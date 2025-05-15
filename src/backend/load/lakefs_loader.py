from lakefs.client import Client
import lakefs
from lakefs import repositories
import subprocess
import pandas as pd
from dotenv import load_dotenv
import os
import shutil
import hashlib
import fsspec

# Import modern log configuration
from config.logging.modern_log import LoggingConfig
# Import path configuration
from config.path_config import lakefs_s3_path, repo_name, branch_name, lakefs_s3_path_hash, repo_name_hash

logger = LoggingConfig(level="DEBUG", level_console="INFO").get_logger(__name__)

load_dotenv()

import time  # <-- เพิ่มสำหรับ sleep

class LakeFSLoader:
    def __init__(self, host: str = "http://localhost:8001"):
        self.restart_container()
        self.client = Client(
            host=host,
            username=os.getenv("ACCESS_KEY"),  
            password=os.getenv("SECRET_KEY"),
            verify_ssl=False,
        )
        logger.debug(f"Connected to lakeFS version: {self.client.version}")

    def load_hash(self, df: pd.DataFrame, lakefs_endpoint: str, repo_name: str = repo_name_hash):
        logger.info(f"Creating or replacing repository hash: {repo_name}")
        lakefs.repository(repo_name, client=self.client).create(storage_namespace=f"local://{repo_name}")
        logger.info(f"Repository {repo_name} hash created or already exists.")

        storage_options = {
            "key": os.getenv("ACCESS_KEY"),
            "secret": os.getenv("SECRET_KEY"),
            "client_kwargs": {
                "endpoint_url": lakefs_endpoint
            }
        }
        columns = ["postTimeRaw", "username", "tweetText"]
        data_str = df[columns].astype(str).apply(lambda row: "_".join(row), axis=1).str.cat()
        hash_text = hashlib.md5(data_str.encode()).hexdigest()
        fs = fsspec.filesystem("s3", **storage_options)
        with fs.open(lakefs_s3_path_hash, "w") as f:
            f.write(hash_text)   
        logger.info(f"Uploaded hash: {hash_text} to {lakefs_s3_path_hash}")

    def check_hash(self, df: pd.DataFrame, lakefs_endpoint: str) -> bool:
        storage_options = {
            "key": os.getenv("ACCESS_KEY"),
            "secret": os.getenv("SECRET_KEY"),
            "client_kwargs": {
                "endpoint_url": lakefs_endpoint
            }
        }
        columns = ["postTimeRaw", "username", "tweetText"]
        data_str = df[columns].astype(str).apply(lambda row: "_".join(row), axis=1).str.cat()
        new_hash = hashlib.md5(data_str.encode()).hexdigest()

        fs = fsspec.filesystem("s3", **storage_options)

        if fs.exists(lakefs_s3_path_hash):
            with fs.open(lakefs_s3_path_hash, "r") as f:
                existing_hash = f.read().strip()
            if new_hash == existing_hash:
                logger.info("No changes detected. Hash matched.")
                return False 

        with fs.open(lakefs_s3_path_hash, "w") as f:
            f.write(new_hash)
        logger.info(f"Uploaded new hash: {new_hash} to {lakefs_s3_path_hash}")
        return True  
    
    def restart_container(self, container_name="lakefs_db"):
        try:
            stop_command = ["docker", "compose", "down", container_name]
            logger.info(f"Stopping container: {' '.join(stop_command)}")
            stop_result = subprocess.run(stop_command, capture_output=True, text=True)

            if stop_result.returncode == 0:
                logger.info(f"Container {container_name} stopped successfully.")
            else:
                logger.error(f"Failed to stop container {container_name}. Error: {stop_result.stderr.strip()}")

            start_command = ["docker", "compose", "up", "-d", container_name]
            logger.info(f"Starting container: {' '.join(start_command)}")
            start_result = subprocess.run(start_command, capture_output=True, text=True)

            if start_result.returncode == 0:
                logger.info(f"Container {container_name} started successfully.")
                logger.info("Waiting for container to be ready...")
                time.sleep(10)  
            else:
                logger.error(f"Failed to start container {container_name}. Error: {start_result.stderr.strip()}")

        except Exception as e:
            logger.error(f"Exception occurred while restarting container {container_name}: {str(e)}")

    def connect(self):
        try:
            logger.debug("Listing repositories in lakeFS...")
            for repo in lakefs.repositories(self.client):
                print(repo)
            logger.debug("Successfully connected to lakeFS")
        except Exception as e:
            logger.error("Error connecting to lakeFS", exc_info=True)

    def load(self, data: pd.DataFrame, lakefs_endpoint: str, repo_name: str = repo_name, lakefs_s3_path: str = lakefs_s3_path) -> None:
        logger.info(f"Creating or replacing repository: {repo_name}")
        lakefs.repository(repo_name, client=self.client).create(storage_namespace=f"local://{repo_name}")
        logger.info(f"Repository {repo_name} created or already exists.")

        logger.debug(f"Uploading data to lakeFS repository: {repo_name} on branch: {branch_name}")

        storage_options = {
            "key": os.getenv("ACCESS_KEY"),
            "secret": os.getenv("SECRET_KEY"),
            "client_kwargs": {
                "endpoint_url": lakefs_endpoint
            }
        }
        
        data.to_parquet(
            lakefs_s3_path,
            storage_options=storage_options,
            partition_cols=['year', 'month', 'day'],
            engine='pyarrow',
        )

        valid_data = pd.read_parquet(
            lakefs_s3_path,
            storage_options=storage_options,
            engine='pyarrow',
        )
        logger.info(f"Data uploaded successfully to {lakefs_s3_path} with {len(valid_data)} records.")

    def incremental_load(self, data: pd.DataFrame, lakefs_endpoint: str, lakefs_s3_path: str = lakefs_s3_path, is_wordcloud: bool=False) -> None:
        storage_options = {
            "key": os.getenv("ACCESS_KEY"),
            "secret": os.getenv("SECRET_KEY"),
            "client_kwargs": {
                "endpoint_url": lakefs_endpoint
            }
        }
        data_in_lakefs = pd.read_parquet(
            lakefs_s3_path,
            storage_options=storage_options,
            engine='pyarrow',
        )
        if is_wordcloud:
            new_unique_data = data.merge(
                data_in_lakefs,
                on=["postTimeRaw", "tweetText"],    
                how="left",
                indicator=True
            ).query('_merge == "left_only"').drop(columns=['_merge'])
        else:
            new_unique_data = data.merge(
                data_in_lakefs,
                on=["postTimeRaw", "username", "tweetText"],    
                how="left",
                indicator=True
            ).query('_merge == "left_only"').drop(columns=['_merge'])

        cols = [col for col in new_unique_data.columns if not col.endswith('_y')]
        new_cleaned_df = new_unique_data[cols].copy()
        new_cleaned_df.columns = [col.replace('_x', '') for col in new_cleaned_df.columns]

        if len(new_cleaned_df) > 0:
            logger.info(new_cleaned_df)
            logger.info(f"Number of new records: {len(new_cleaned_df)}")
            new_cleaned_df.to_parquet(
                lakefs_s3_path,
                storage_options=storage_options,
                partition_cols=['year', 'month', 'day'],
                engine='pyarrow',
            )

            logger.info(f"Data uploaded successfully to {lakefs_s3_path} with {len(new_cleaned_df)} records.")
        else:
            logger.info("No new records found.")

if __name__ == "__main__":
    loader = LakeFSLoader(host="http://lakefs_db:8000")
    loader.connect()
