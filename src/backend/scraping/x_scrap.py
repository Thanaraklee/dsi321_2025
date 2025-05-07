from playwright.sync_api import sync_playwright
import time
from pprint import pprint
import json
import os
from datetime import datetime  # <-- NEW IMPORT
from pathlib import Path
import pandas as pd
import re
import urllib.parse
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
# Import modern logging configuration
from config.logging.modern_log import LoggingConfig
# Import path configuration
from config.path_config import AUTH_TWITTER
# Import LakeFS loader
from src.backend.load.lakefs_loader import LakeFSLoader
# Import validation configuration
from src.backend.validation.validate import ValidationPydantic, TweetData

logger = LoggingConfig(level="DEBUG", level_console="INFO").get_logger()
console = Console()

def scrape_all_tweet_texts(url: str, max_scrolls: int = 5):
    """
    Scrapes all tweet texts from a given Twitter URL by scrolling down.

    Args:
        url: The Twitter URL to scrape (e.g., a user profile or search results).
        max_scrolls: The maximum number of times to scroll down the page.

    Returns:
        A list of dicts with keys: username, tweetText, scrapeTime.
    """
    all_tweet_entries = []  
    seen_pairs = set()  # To keep track of unique (username, tweetText)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=AUTH_TWITTER, viewport={"width": 1280, "height": 1024})
        page = context.new_page()

        try:
            # print(f"Navigating to {url}...")
            page.goto(url)
            logger.debug("Page loaded. Waiting for initial tweets...")

            try:
                page.wait_for_selector("article", timeout=30000)
                logger.debug("Initial tweets found.")
            except Exception as e:
                logger.error("Could not find initial tweets", exc_info=True)
                try:
                    page.wait_for_selector("[data-testid='tweetText']", timeout=10000)
                    logger.error("Initial tweet text found.")
                except Exception as e2:
                    logger.error("Could not find initial tweet text either", exc_info=True)
                    page.screenshot(path="tmp/debug_screenshot_no_tweets.png")
                    return all_tweet_entries

            logger.debug(f"Scrolling down {max_scrolls} times...")
            last_height = page.evaluate("document.body.scrollHeight")

            for i in range(max_scrolls):
                if i > 0:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                logger.debug(f"Scroll attempt {i+1}/{max_scrolls}")
                
                time.sleep(3)
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    logger.debug("Reached bottom of page or no new content loaded.")
                    break
                last_height = new_height


                articles = page.query_selector_all("article")
                if articles:
                    for article in articles:
                        displayName = article.query_selector("[data-testid='User-Name']")
                        if displayName:
                            spans = displayName.query_selector_all("span")
                            time_tag = displayName.query_selector("time")
                            tweetText_tag = article.query_selector("[data-testid='tweetText']")

                            if len(spans) > 3 and time_tag and tweetText_tag:
                                userName = spans[3].text_content().strip()
                                dateTime = time_tag.get_attribute("datetime")
                                tweetText = tweetText_tag.text_content().strip()

                                if userName and tweetText and dateTime:
                                    try:
                                        dt_naive = datetime.strptime(dateTime, "%Y-%m-%dT%H:%M:%S.%fZ")
                                        now = datetime.now()
                                        key = (userName, tweetText)
                                        if key not in seen_pairs:
                                            seen_pairs.add(key)
                                            all_tweet_entries.append({
                                                "username": userName,
                                                "tweetText": tweetText,
                                                "postTimeRaw": dt_naive,
                                                "scrapeTime": now.isoformat()
                                            })
                                    except ValueError as e:
                                        logger.error(f"Invalid datetime format: {dateTime} | Error: {e}", exc_info=True)

                # tweet_elements = page.query_selector_all("[data-testid='tweetText']")
                # user_names = page.query_selector_all("[data-testid='User-Name']")
                # now = datetime.now()

                # for user, text in zip(user_names, tweet_elements):
                #     username = user.text_content()
                #     tweet_text = text.text_content()
                    # if username and tweet_text:
                    #     key = (username, tweet_text)
                    #     if key not in seen_pairs:
                    #         seen_pairs.add(key)
                    #         all_tweet_entries.append({
                    #             "username": username,
                    #             "tweetText": tweet_text,
                    #             "scrapeTime": now.isoformat()
                    #         })

                logger.info(f"Total tweets collected so far: {len(all_tweet_entries)}")

        except Exception as e:
            logger.error("An error occurred during scraping", exc_info=True)
        finally:
            logger.debug("Closing browser.")
            browser.close()
    return all_tweet_entries

def transform_post_time(post_time, scrape_time):
    year_diff = scrape_time.year - post_time.year
    try:
        adjusted_time = post_time.replace(year=scrape_time.year)
    except ValueError:
        adjusted_time = post_time.replace(year=scrape_time.year, day=28)

    if adjusted_time > scrape_time:
        try:
            adjusted_time = post_time.replace(year=scrape_time.year - 1)
        except ValueError:
            adjusted_time = post_time.replace(year=scrape_time.year - 1, day=28)

    return adjusted_time

def scrape_tags(tags: list[str], max_scrolls: int = 2) -> pd.DataFrame:
    all_dfs = []

    for tag in tags:
        encoded = urllib.parse.quote(tag, safe='')
        target_url = f"https://x.com/search?q={encoded}&src=typeahead_click&f=live"
        
        tweet_data = scrape_all_tweet_texts(target_url, max_scrolls=max_scrolls)

        if tweet_data:
            logger.info(f"Total unique tweet entries scraped for tag '{tag}': {len(tweet_data)}")
        else:
            logger.info(f"No tweet texts were scraped for tag '{tag}'.")
            continue 
        
        try:
            tweet_df = pd.DataFrame(tweet_data)
            tweet_df['scrapeTime'] = datetime.now()

            clean_tag = lambda x: re.sub(r'[^a-zA-Z0-9ก-๙]', '', x)
            tweet_df['tag'] = clean_tag(tag)

            tweet_df['postTime'] = tweet_df.apply(
                lambda row: transform_post_time(row['postTimeRaw'], row['scrapeTime']),
                axis=1
            )

            tweet_df['username'] = tweet_df['username'].astype('string')
            tweet_df['tweetText'] = tweet_df['tweetText'].astype('string')
            tweet_df['tag'] = tweet_df['tag'].astype('string')
            tweet_df['postTimeRaw'] = pd.to_datetime(tweet_df['postTimeRaw'])

            tweet_df['year'] = tweet_df['postTime'].dt.year
            tweet_df['month'] = tweet_df['postTime'].dt.month
            tweet_df['day'] = tweet_df['postTime'].dt.day

            all_dfs.append(tweet_df)

        except Exception as e:
            logger.error(f"Error creating DataFrame for tag: {tag}", exc_info=True)
            continue

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"Combined DataFrame created with {len(final_df)} records from {len(tags)} tags.")
        return final_df
    else:
        logger.warning("No data was scraped for any tags.")
        return pd.DataFrame()

def save_to_parquet(data: pd.DataFrame):
    LakeFSLoader().load(data)

if __name__ == "__main__":
    tags = [
        "#ธรรมศาสตร์ช้างเผือก",
    ]
    data = scrape_tags(tags=tags, max_scrolls=1)
    
    if data is not None:
        # Validate the data using Pydantic
        validator = ValidationPydantic(TweetData)
        is_valid = validator.validate(data)

        save_csv = Prompt.ask('Do you want to save the data to CSV? (Y = Yes, N = No)', choices=['Y', 'N'])
        if save_csv == 'Y':
            data.to_csv('data/tweet_data.csv', index=False)
            logger.info("CSV file saved.")

        save_parquet = Prompt.ask('Do you want to save the data to Parquet? (Y = Yes, N = No)', choices=['Y', 'N'])
        if save_parquet == 'Y':
            save_to_parquet(data)
            logger.info("Parquet file saved.")
        else:
            logger.info("Data not saved to Parquet.")

    else:
        logger.error("No data to save.")
    
