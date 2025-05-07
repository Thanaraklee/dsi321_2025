from playwright.sync_api import sync_playwright
from rich.prompt import Prompt
from rich.text import Text
from pathlib import Path
import json
import os
import urllib.parse
# Import modern logging configuration
from config.logging.modern_log import LoggingConfig
# Import path configuration
from config.path_config import AUTH_TWITTER


logger = LoggingConfig(level="DEBUG").get_logger()

def validate_session(playwright):
    encoded = urllib.parse.quote("#ธรรมศาสตร์ช้างเผือก", safe='')
    url = f"https://x.com/search?q={encoded}&src=typeahead_click&f=live"

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(storage_state=AUTH_TWITTER, viewport={"width": 1280, "height": 1024})
    page = context.new_page()

    try:
        page.goto(url)
        logger.debug("Page loaded. Waiting for initial tweets...")
        page.wait_for_selector("article", timeout=30000)
        logger.info("Valid session detected.")
        return True
    except Exception as e:
        logger.error(f"Session invalid or timed out: {e}")
        if os.path.exists(AUTH_TWITTER):
            os.remove(AUTH_TWITTER)
            logger.info("Removed invalid session file")
        return False
    finally:
        browser.close()

def login_and_save_session(playwright):
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://x.com/login")
    logger.info("Waiting for manual login...")

    Prompt.ask(Text("Log in to Twitter manually, then press Enter here...", style="bold green"))

    # Save session
    Path(AUTH_TWITTER).parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=AUTH_TWITTER)
    browser.close()
    logger.info("Session saved")

if __name__ == "__main__":
    with sync_playwright() as p:
        if not os.path.exists(AUTH_TWITTER) or not validate_session(p):
            login_and_save_session(p)
            validate_session(p)