import urllib.parse
import asyncio
from playwright.async_api import async_playwright
import time
from datetime import datetime
import random
import pandas as pd
import os

# Import modern logging configuration
from config.logging.modern_log import LoggingConfig
# Import path configuration
from config.path_config import AUTH_TWITTER
# Import validation configuration
from src.backend.validation.validate import ValidationPydantic, TweetData
# Import LakeFS loader
from src.backend.load.lakefs_loader import LakeFSLoader

logger = LoggingConfig(level="DEBUG", level_console="DEBUG").get_logger()

class XScraping:
    def __init__(self):
        pass

    def encode_tag_to_url(self, tags: list[str]) -> dict[str, str]:
        """
        Encode a list of tags to their respective URL format.
        """
        encoded_tags = {}
        for i, tag in enumerate(tags):
            text_encoded = urllib.parse.quote(tag, safe="")
            target_url = f"https://x.com/search?q={text_encoded}&src=typed_query&f=live"
            logger.debug(f"Encoded tag {i+1}/{len(tags)}: {tag}")
            encoded_tags[tag] = target_url
        logger.info(f"Encoded {len(tags)} tags to URL format")
        return encoded_tags
    
    async def wait_for_articles_with_retry(self, page, max_retries=2) -> bool:
        for retry in range(max_retries):
            if await self.is_article_present(page):
                return True
            logger.warning(f"Retry {retry+1}/{max_retries} - Waiting before next try...")
            await asyncio.sleep(random.uniform(2.0, 4.0))
        return False

    async def is_article_present(self, page) -> bool:
        try:
            await page.wait_for_selector("article", timeout=5000)
            logger.debug("Found article on the page")
            return True
        except Exception as e:
            logger.error(f"Article not found on the page", exc_info=True)
            await page.screenshot(path="tmp/debug_screenshot_no_tweets.png")
            return False

    async def extract_articles(self, tag: str, count_tweets: int, articles: list, seen_pairs: set, all_tweet_entries: list) -> None:
        for i, article in enumerate(articles):
            displayName = await article.query_selector("[data-testid='User-Name']")
            if displayName:
                spans = await displayName.query_selector_all("span")
                time_tag = await displayName.query_selector("time")
                tweetText_tag = await article.query_selector("[data-testid='tweetText']")
                if len(spans) > 3 and time_tag and tweetText_tag:
                    userName = await spans[3].text_content()
                    userName = userName.strip()
                    dateTime = await time_tag.get_attribute("datetime")
                    tweetText = await tweetText_tag.text_content()
                    tweetText = tweetText.strip()

                    if userName and tweetText and dateTime:
                        try:
                            dt_naive = datetime.strptime(dateTime, "%Y-%m-%dT%H:%M:%S.%fZ")
                            now = datetime.now()
                            key = (userName, tweetText)
                            if key not in seen_pairs:
                                seen_pairs.add(key)
                                all_tweet_entries.append({
                                    "tag": tag,
                                    "username": userName,
                                    "tweetText": tweetText,
                                    "postTimeRaw": dt_naive,
                                    "scrapeTime": now.strftime("%Y-%m-%dT%H:%M:%S")
                                })
                                count_tweets += 1
                                logger.debug(f"Scraped tweet {count_tweets} - {tag}")
                        except ValueError as e:
                            logger.error(f"Invalid datetime format: {dateTime} | Error: {e}", exc_info=True)
                        
                else:
                    logger.debug("Tweet does not have the expected structure.")
            else:
                logger.debug("No display name found for the article.")


    async def scrape_all_tweet_texts(self, tag: str, tag_url: str, max_scrolls: int = 2, view_browser: bool = True) -> list[dict]:
        logger.debug(f"Starting scraping: {tag}")
        all_tweet_entries = []
        seen_pairs = set() 
        count_tweets = 0
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=view_browser)
            context = await browser.new_context(
                storage_state=AUTH_TWITTER,
                viewport={"width": 1280, "height": 1024}
            )
            page = await context.new_page()
            await page.goto(tag_url)
            await asyncio.sleep(random.uniform(2.5, 5.0))

            # Check if the page has loaded tweets
            if not await self.wait_for_articles_with_retry(page):
                logger.error(f"No articles found for tag: {tag} (Initial load)")
                await browser.close()
                return all_tweet_entries

            now_height = 0
            for i in range(max_scrolls):
                if i > 0:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(random.uniform(2.5, 5.0))

                    # Check if the page has loaded tweets
                    if not await self.wait_for_articles_with_retry(page):
                        logger.warning(f"No articles found on scroll {i+1}")
                        break
                
                logger.debug(f"Scroll attempt {i+1}/{max_scrolls}")
                new_height = await page.evaluate("document.body.scrollHeight")
                await asyncio.sleep(random.uniform(2.5, 5.0))
                logger.debug(f"Now height: {now_height} - New height after scroll: {new_height}")
                
                if new_height == now_height:
                    logger.debug("Reached bottom of page or no new content loaded.")
                    break
                now_height = new_height

                articles = await page.query_selector_all("article")
                if articles:
                    await self.extract_articles(tag, count_tweets, articles, seen_pairs, all_tweet_entries)
                else:
                    logger.debug("No articles found on the page.")
                    break
            
            await browser.close()
            logger.info(f"Finished scraping tag: {tag} | Total tweets: {len(all_tweet_entries)}")

        return all_tweet_entries

    @staticmethod
    def to_dataframe(all_tweet: list[dict]) -> pd.DataFrame:
        logger.info(f"Converting to dataframe...")
        all_tweet = pd.DataFrame(all_tweet)
        all_tweet['username'] = all_tweet['username'].astype('string')
        all_tweet['tweetText'] = all_tweet['tweetText'].astype('string')
        all_tweet['tag'] = all_tweet['tag'].astype('string')

        all_tweet['year'] = all_tweet['postTimeRaw'].dt.year
        all_tweet['month'] = all_tweet['postTimeRaw'].dt.month
        all_tweet['day'] = all_tweet['postTimeRaw'].dt.day

        all_tweet['postTimeRaw'] = pd.to_datetime(all_tweet['postTimeRaw'])
        all_tweet['scrapeTime'] = pd.to_datetime(all_tweet['scrapeTime'])
        logger.info("Finished converting to dataframe.")
        return all_tweet

    @staticmethod
    def load_to_lakefs(data: pd.DataFrame):
        LakeFSLoader().load(data)

async def main():
    tags = ["#ธรรมศาสตร์ช้างเผือก", "#TCAS", "#รับตรง"]
    x_scraping = XScraping()
    tag_urls = x_scraping.encode_tag_to_url(tags)

    tasks = [x_scraping.scrape_all_tweet_texts(tag=tag, tag_url=tag_urls[tag]) for tag in tag_urls.keys()]
    results = await asyncio.gather(*tasks)

    all_tweet_entries = [entry for result in results for entry in result]
    data = x_scraping.to_dataframe(all_tweet_entries)
    logger.info(f"Total tweets scraped from all tags: {len(data)}")

    validator = ValidationPydantic(TweetData)
    is_valid = validator.validate(data)
    is_valid = True
    if is_valid:
        os.makedirs('data', exist_ok=True)
        data.to_csv('data/tweet_data.csv', index=False)
        logger.info("CSV file saved.")
        x_scraping.load_to_lakefs(data)


if __name__ == "__main__":
    asyncio.run(main())
