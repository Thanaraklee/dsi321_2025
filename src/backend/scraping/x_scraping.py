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

    def encode_tag_to_url(self, tags: dict[str, list[str]]) -> dict[str, dict[str, str]]:
        encoded_tags_by_category = {}

        for category, tag_list in tags.items():
            encoded_tags = {}
            for i, tag in enumerate(tag_list):
                text_encoded = urllib.parse.quote(tag, safe="")
                target_url = f"https://x.com/search?q={text_encoded}&src=typed_query&f=live"
                logger.debug(f"Encoded tag {i+1}/{len(tag_list)} in '{category}': {tag}")
                encoded_tags[tag] = target_url
            encoded_tags_by_category[category] = encoded_tags

        logger.info(f"Encoded tags for {len(tags)} categories to URL format")
        return encoded_tags_by_category

    async def wait_for_articles_with_retry(self, page, max_retries: int =2) -> bool:
        for retry in range(max_retries):
            if await self.is_article_present(page):
                return True
            logger.warning(f"Retry {retry+1}/{max_retries} - Waiting before next try...")
            await asyncio.sleep(random.uniform(6.0, 12.0))
        return False

    async def is_article_present(self, page) -> bool:
        try:
            await page.wait_for_selector("article", timeout=5000)
            logger.debug("Found article on the page")
            return True
        except TimeoutError as t:
            logger.error(f"X Blocked us Please try again later 😢")
            await page.screenshot(path="tmp/debug_screenshot_no_tweets.png")
            return False

    async def extract_articles(self, category: str, tag: str, count_tweets: int, articles: list, seen_pairs: set, all_tweet_entries: list) -> None:
        for i, article in enumerate(articles):
            displayName = await article.query_selector("[data-testid='User-Name']")
            if displayName:
                spans = await displayName.query_selector_all("span")
                time_tag = await displayName.query_selector("time")
                asyncio.sleep(random.uniform(1.0, 7.5))
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
                                    "category": category,
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

    async def scrape_all_tweet_texts(self, category: str, tag: str, tag_url: str, max_scrolls: int = 10, view_browser: bool = True) -> list[dict]:
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
            await asyncio.sleep(random.uniform(2, 20.0))

            # Check if the page has loaded tweets
            if not await self.wait_for_articles_with_retry(page):
                logger.error(f"No articles found for tag: {tag} (Initial load)")
                await browser.close()
                return all_tweet_entries

            now_height = 0
            for i in range(max_scrolls):
                if i > 0:
                    scroll_distance = random.randint(300, 800)
                    await page.evaluate(f"window.scrollBy(0, {scroll_distance});")
                    logger.debug(f"Scroll attempt {i+1}/{max_scrolls} - Scrolling by {scroll_distance}px")
                    await asyncio.sleep(random.uniform(5, 17))
                    # Check if the page has loaded tweets
                    if not await self.wait_for_articles_with_retry(page):
                        logger.warning(f"No articles found on scroll {i+1}")
                        break
                
                logger.debug(f"Scroll attempt {i+1}/{max_scrolls} - {tag}")
                new_height = await page.evaluate("document.body.scrollHeight")
                await asyncio.sleep(random.uniform(1, 14))
                logger.debug(f"Now height: {now_height} - New height after scroll: {new_height}")
                
                if new_height == now_height:
                    logger.debug("Reached bottom of page or no new content loaded.")
                    break
                now_height = new_height

                articles = await page.query_selector_all("article")
                if articles:
                    await self.extract_articles(category, tag, count_tweets, articles, seen_pairs, all_tweet_entries)
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
    def load_to_lakefs(data: pd.DataFrame, lakefs_endpoint: str):
        LakeFSLoader(host=lakefs_endpoint).load(data=data, lakefs_endpoint=lakefs_endpoint)

async def main():
    tags = {
        "ธรรมศาสตร์": [
            "#ธรรมศาสตร์ช้างเผือก",
            "#TCAS",
            "#รับตรง",
            "#ทีมมธ",
            "#มธ", 
            "#dek70", 
            "#มอท่อ",
            "#TU89",
        ],
        "คณะนิติศาสตร์":[
            # "#นิติศาสตร์",
            # "#LawTU",
            # "#TUlaw",
            "#นิติมธ",
        ],
        "คณะพาณิชยศาสตร์และการบัญชี":[
            "#บัญชีมธ",
            "##บริหารมธ",
            "#BBATU",
        ],
        "คณะรัฐศาสตร์":[
            "#รัฐศาสตร์มธ",
            "#LLBTU",
            "#BIRTU",
            "#singhadang",
            "#สิงห์แดง",
        ],
        "คณะเศรษฐศาสตร์":[
            "#เสดสาดมธ",
            # "#EconTU",
            # "#TUeconomics",
        ],
        "คณะสังคมสงเคราะห์ศาสตร์":[
            "#สังคมสงเคราะห์มธ",
            # "#SocialWorkTU",
        ],
        "คณะสังคมวิทยาและมานุษยวิทยา":[
            "#สังวิทมธ",
            # "#AnthroTU",
        ],
        "คณะศิลปศาสตร์":[
            "#สินสาดมธ",
            "#LartsTU",
            "#BASTU",
        ],
        "คณะวารสารศาสตร์และสื่อสารมวลชน":[
            "#BJMTU",
            "#JCTU",
            "#วารสารมธ",
        ],
        "คณะวิทยาศาสตร์และเทคโนโลยี":[
            "#วิทยามธ",
            "#วิดยามธ",
        ],
        "คณะวิศวกรรมศาสตร์":[
            "#วิดวะมธ",
            # "#EngTU",
            # "#TUengineering",
        ],
        "คณะสถาปัตยกรรมศาสตร์และการผังเมือง":[
            "#APTU",
            "#สถาปัตมธ",
            "#ถาปัตมธ",
            "#สถาปัตย์มธ",
        ],
        "คณะศิลปกรรมศาสตร์":[
            "#ละคอนมธ",
            "#สินกำมธ",
        ],
        "คณะแพทยศาสตร์":[
            "#แพทย์มธ",
            # "#MedTU",
            # "#TUmedicine",
        ],
        "คณะสหเวชศาสตร์":[
            "#สหเวชมธ",
            "#กายภาพมธ",
            "#เทคนิคมธ",
        ],
        "คณะทันตแพทยศาสตร์":[
            "#ทันตะมธ",
            # "#DentTU",
            # "#TUDentistry",
        ],
        "คณะพยาบาลศาสตร์":[
            "#พยาบาลมธ",
            # "#NurseTU",
            # "#TUnursing",
        ],
        "คณะสาธารณสุขศาสตร์":[
            "#fphtu",
            "#fphthammasat",
        ],
        "คณะเภสัชศาสตร์":[
            "#เภสัชมธ",
            # "#PharmTU",
            # "#TUpharmacy",
        ],
        "คณะวิทยาการเรียนรู้และศึกษาศาสตร์":[
            "#lsedtu",
            "#lsed",
            "#คณะวิทยาการเรียนรู้และศึกษาศาสตร์",
        ],
        "วิทยาลัยพัฒนศาสตร์ ป๋วย อึ๊งภากรณ์":[
            "#psdsTU",
            "#วป๋วย",
            "#วิทยาลัยป๋วย",
            "#วิทยาลัยพัฒนศาสตร์",
        ],
        "วิทยาลัยนวัตกรรม":[
            "#นวัตมธ",
            "#CITU",
            "#CITUSC",
            "#CITUTU",
        ],
        # "วิทยาลัยสหวิทยาการ":[
        #     "#สหวิทยาการธรรมศาสตร์",
        #     "#InterdisciplinaryTU",
        # ],
        # "วิทยาลัยโลกคดีศึกษา":[
        #     "#โลกคดีธรรมศาสตร์",
        #     "#WorldStudiesTU",
        # ],
        # "สถาบันเทคโนโลยีนานาชาติสิรินธร":[
        #     "#SIIT",
        #     "#SIITThammasat",
        # ],
        # "วิทยาลัยนานาชาติ ปรีดี พนมยงค์":[
        #     "#ปรีดีนานาชาติ",
        #     "#PridiTU",
        #     "#TUinternational",
        # ],
        # "วิทยาลัยแพทยศาสตร์นานาชาติจุฬาภรณ์":[
        #     "#แพทย์นานาชาติธรรมศาสตร์",
        #     "#CICM",
        #     "#CICMTU",
        # ],
        # "สถาบันเสริมศึกษาและทรัพยากรมนุษย์":[
        #     "#เสริมศึกษาธรรมศาสตร์",
        #     "#HumanResourcesTU",
        # ],
        # "สถาบันไทยคดีศึกษา":[
        #     "#ไทยคดีธรรมศาสตร์",
        #     "#ThaiStudiesTU",
        # ],
        # "สถาบันเอเชียตะวันออกศึกษา":[
        #     "#เอเชียตะวันออกธรรมศาสตร์",
        #     "#EastAsianStudiesTU",
        # ],
        # "สถาบันภาษา":[
        #     "#สถาบันภาษาธรรมศาสตร์",
        #     "#LanguageInstituteTU",
        # ],
        # "สถาบันอาณาบริเวณศึกษา":[
        #     "#อาณาบริเวณธรรมศาสตร์",
        #     "#AreaStudiesTU",
        # ],
    }

    x_scraping = XScraping()
    tag_urls = x_scraping.encode_tag_to_url(tags)


    semaphore = asyncio.Semaphore(3)
    all_results = []

    async def scrape_with_limit(category: str, tag: str, url: str):
        async with semaphore:
            result = await x_scraping.scrape_all_tweet_texts(category, tag, url)
            return result
        
    tasks = []
    for category, tag_url_dict in tag_urls.items():
        for tag, url in tag_url_dict.items():
            tasks.append(scrape_with_limit(category, tag, url))

    logger.info(f"Starting scraping with {len(tasks)} tasks, max 3 concurrently...")
    # tasks = [x_scraping.scrape_all_tweet_texts(tag=tag, tag_url=tag_urls[tag]) for tag in tag_urls.keys()]
    results = await asyncio.gather(*tasks)

    for result in results:
        all_results.extend(result)

    # all_tweet_entries = [entry for result in results for entry in result]
    data = x_scraping.to_dataframe(all_results)
    logger.info(f"Total tweets scraped from all tags: {len(data)}")

    validator = ValidationPydantic(TweetData)
    is_valid = validator.validate(data)
    is_valid = True
    if is_valid:
        os.makedirs('data', exist_ok=True)
        data.to_csv('data/tweet_data.csv', index=False)
        logger.info("CSV file saved.")
        x_scraping.load_to_lakefs(data=data, lakefs_endpoint="http://localhost:8001")


if __name__ == "__main__":
    asyncio.run(main())
