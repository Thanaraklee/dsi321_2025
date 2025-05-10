from dotenv import load_dotenv
import os

load_dotenv()

DATA = "data"
AUTH = "config/auth"

AUTH_TWITTER = AUTH + "/twitter_auth.json"

repo_name = "tweets-repo"
branch_name = "main"
path = "tweets.parquet"

lakefs_s3_path = f"s3://{repo_name}/{branch_name}/{path}"