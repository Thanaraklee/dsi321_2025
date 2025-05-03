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

file_dir = Path(__file__).resolve().parent
data_dir = file_dir/ ".." / "data"

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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state="twitter_auth.json", viewport={"width": 1280, "height": 1024})
        page = context.new_page()

        try:
            # print(f"Navigating to {url}...")
            page.goto(url, wait_until='networkidle', timeout=60000)
            print("Page loaded. Waiting for initial tweets...")

            try:
                page.wait_for_selector("[data-testid='tweet']", timeout=30000)
                print("Initial tweets found.")
            except Exception as e:
                print(f"Could not find initial tweets: {e}")
                try:
                    page.wait_for_selector("[data-testid='tweetText']", timeout=10000)
                    print("Initial tweet text found.")
                except Exception as e2:
                    print(f"Could not find initial tweet text either: {e2}")
                    page.screenshot(path="debug_screenshot_no_tweets.png")
                    return all_tweet_entries

            print(f"Scrolling down {max_scrolls} times...")
            last_height = page.evaluate("document.body.scrollHeight")

            for i in range(max_scrolls):
                print(f"Scroll attempt {i+1}/{max_scrolls}")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    print("Reached bottom of page or no new content loaded.")
                    break
                last_height = new_height

                tweet_elements = page.query_selector_all("[data-testid='tweetText']")
                user_names = page.query_selector_all("[data-testid='User-Name']")
                now = datetime.now()

                for user, text in zip(user_names, tweet_elements):
                    username = user.text_content()
                    tweet_text = text.text_content()
                    if username and tweet_text:
                        key = (username, tweet_text)
                        if key not in seen_pairs:
                            seen_pairs.add(key)
                            all_tweet_entries.append({
                                "username": username,
                                "tweetText": tweet_text,
                                "scrapeTime": now.isoformat()
                            })

                print(f"Total tweets collected so far: {len(all_tweet_entries)}")

        except Exception as e:
            print(f"An error occurred during scraping: {e}")
        finally:
            print("Closing browser.")
            browser.close()

    return all_tweet_entries

def transform_post_time(post_time, scrape_time):
    # hour
    if 'h' in post_time:
        hour = int(post_time[:-1])
        return scrape_time - pd.Timedelta(hours=hour)
    if 'm' in post_time:
        minute = int(post_time[:-1])
        return scrape_time - pd.Timedelta(minutes=minute)
    if 's' in post_time:
        second = int(post_time[:-1])
        return scrape_time - pd.Timedelta(seconds=second)
    
    try:
        current_year = scrape_time.year
        post_time = f"{current_year} {post_time}"
        return pd.to_datetime(post_time, format='%Y %b %d')
    except ValueError:
        print("error",post_time)
        return pd.NaT
    
def scrape_tag(tag:str) -> pd.DataFrame:
    encoded = urllib.parse.quote(tag, safe='')
    target_url = f"https://x.com/search?q={encoded}&src=typeahead_click&f=live"
    
    # print(f"Starting scrape for URL: {target_url}")
    tweet_data = scrape_all_tweet_texts(target_url, max_scrolls=1)


    print("\n--- Scraped Tweet Data ---")
    if tweet_data:
        pprint(tweet_data)
        print(f"\nTotal unique tweet entries scraped: {len(tweet_data)}")
    else:
        print("No tweet texts were scraped.")
        
    tweet_df = pd.DataFrame(tweet_data)
    tweet_df['scrapeTime'] = datetime.now()
    
    clean_tag = lambda x: re.sub(r'[^a-zA-Z0-9ก-๙]', '', x)
    tweet_df['tag'] = tag
    tweet_df['tag'] = tweet_df['tag'].apply(clean_tag)
    
    tweet_df['postTimeRaw'] = tweet_df['username'].str.split("·").str[-1]
    tweet_df['postTime'] = tweet_df.apply(lambda x: transform_post_time(x['postTimeRaw'], x['scrapeTime']), axis=1)
    scrape_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
    # tweet_df['scrapeTime'] = pd.to_datetime(tweet_df['scrapeTime']).dt.strftime('%Y-%m-%d_%H-%M')
    for (tag_val, scrape_time_val), group in tweet_df.groupby(['tag', 'scrapeTime']):
        # Make human-readable folder name
        subdir = os.path.join(data_dir, f"tag={tag_val}", f"scrapeTime={scrape_time}")
        os.makedirs(subdir, exist_ok=True)
        
        # Save each group (e.g., part-1.parquet)
        group.to_parquet(os.path.join(subdir, 'part.parquet'), index=False, engine='pyarrow')

    return tweet_df


if __name__ == "__main__":
    tag = "#ธรรมศาสตร์ช้างเผือก"
    scrape_tag(tag)
    
