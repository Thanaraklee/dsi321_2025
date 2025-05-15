from prefect import flow, task
import pandas as pd
import os
import asyncio

# Import XScraping for scraping
from src.backend.scraping.x_scraping import XScraping
# Import LakeFS loader
from src.backend.load.lakefs_loader import LakeFSLoader
# Import validation configuration
from src.backend.validation.validate import ValidationPydantic, TweetData
# Import modern logging configuration
from config.logging.modern_log import LoggingConfig
# Import path configuration
from config.path_config import tags, lakefs_s3_path_ml, repo_name_ml
# Import wordcloud 
from src.backend.ml.wordcloud import WordCloud

logger = LoggingConfig(level="DEBUG", level_console="DEBUG").get_logger()

@task(name="generate word cloud")
def generate_wordcloud(df: pd.DataFrame) -> pd.DataFrame:
    return WordCloud().classify(df=df)

@task(name="load word cloud to lakefs")
def load_wordcloud_to_lakefs(faqs_df: pd.DataFrame, lakefs_endpoint: str, lakefs_s3_path: str) -> None:
    return LakeFSLoader(host=lakefs_endpoint).load(faqs_df, lakefs_endpoint=lakefs_endpoint, repo_name=repo_name_ml,lakefs_s3_path=lakefs_s3_path)

@task(name="encode tags")
def encode_tags(tags: dict[str, list[str]]) -> dict[str, dict[str, str]]:
    return XScraping().encode_tag_to_url(tags)

@task(name="flatten results")
def flatten_results(nested_results: list[list[dict]]) -> list[dict]:
    return [entry for result in nested_results for entry in result]

@task(name="data to dataframe")
def to_dataframe(tweets: list[dict]) -> pd.DataFrame:
    return XScraping.to_dataframe(tweets)

@task(name="validate dataframe")
def validate_dataframe(data: pd.DataFrame) -> bool:
    validator = ValidationPydantic(TweetData)
    return validator.validate(data)

@task(name="save to csv")
def save_to_csv(data: pd.DataFrame, path: str = "/root/flows/data/from_prefect/tweet_data.csv") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data.to_csv(path, index=False)
    logger.info(f"CSV file saved to {path}")

@task(name="load to lakefs")
def load_to_lakefs(data: pd.DataFrame, lakefs_endpoint: str = None) -> None:
    LakeFSLoader(host=lakefs_endpoint).load(data=data, lakefs_endpoint=lakefs_endpoint)

@task(name="scrape tag")
async def scrape_tag(category: str, tag: str, tag_url: str) -> list[dict]:
    try:
        return await XScraping().scrape_all_tweet_texts(category=category, tag=tag, tag_url=tag_url, max_scrolls=2)
    except Exception as e:
        logger.error(f"[ERROR] Tag '{tag}' failed: {str(e)}")
        raise

@task(name="upload hash")
def unload_hash(df: pd.DataFrame, lakefs_endpoint: str) -> bool:
    return LakeFSLoader(host=lakefs_endpoint).load_hash(df=df, lakefs_endpoint=lakefs_endpoint)


@flow(name="Initial Scrape Flow")
async def scrape_flow():
    tag_urls = encode_tags(tags)
    semaphore = asyncio.Semaphore(3)
    delay_seconds = 30
    lakefs_endpoint = "http://lakefsdb:8000"

    async def scrape_with_limit(category: str, tag: str, url: str):
        async with semaphore:
            return await scrape_tag(category=category, tag=tag, tag_url=url)
        
    task_list = [
        (category, tag, url)
        for category, tag_url_dict in tag_urls.items()
        for tag, url in tag_url_dict.items()
    ]

    all_results = []

    for i in range(0, len(task_list), 3):
        batch = task_list[i:i+3]
        futures = [
            scrape_with_limit(category, tag, url)
            for category, tag, url in batch
        ]
        results = await asyncio.gather(*futures)
        all_results.extend(results)

        if i + 3 < len(task_list):
            logger.info(f"Completed batch {i//3 + 1}. Sleeping for {delay_seconds} seconds...")
            await asyncio.sleep(delay_seconds)

    all_tweets = flatten_results(all_results)
    data = to_dataframe(all_tweets)
    logger.info(f"Total tweets scraped: {len(data)}")

    is_valid = validate_dataframe(data=data)
    is_valid = True
    if is_valid:
        faqs_df = generate_wordcloud(df=data)
        # save_to_csv(data)
        # load_to_lakefs(data=data, lakefs_endpoint=lakefs_endpoint)
        save_to_csv(data)
        unload_hash(df=data, lakefs_endpoint=lakefs_endpoint)
        load_to_lakefs(data=data, lakefs_endpoint=lakefs_endpoint)
        load_wordcloud_to_lakefs(faqs_df=faqs_df, lakefs_endpoint=lakefs_endpoint, lakefs_s3_path=lakefs_s3_path_ml)
    else:
        logger.warning("Validation failed, data not saved.")

    

if __name__ == "__main__":
    asyncio.run(scrape_flow())