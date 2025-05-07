from playwright.sync_api import sync_playwright
from rich.prompt import Prompt
from rich.text import Text
from pathlib import Path
import json
import requests
import os
# Import modern logging configuration
from config.logging.modern_log import LoggingConfig
# Import path configuration
from config.path_config import AUTH_TWITTER


logger = LoggingConfig(level="DEBUG").get_logger()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headless=False so you can log in manually
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://x.com/login")

    logger.info("Page loaded. Waiting for login...")
    Prompt.ask(Text("Log in to Twitter manually, then press Enter here...", style="bold green"))

    # Create the directory if it doesn't exist
    Path(AUTH_TWITTER).parent.mkdir(parents=True, exist_ok=True)

    context.storage_state(path=AUTH_TWITTER)  # Save cookies/session
    browser.close()

    # Validate the saved session
    logger.info("Session saved. Validating...")
    data = json.load(open(AUTH_TWITTER, "r"))

    # Validate the session using the cookies from the saved state

    # if len(data['cookies']) > (13*2) and len(data['cookies'][0]['value']) > 500:
    #     logger.info("Session is valid ✅")
    # else:
    #     logger.error("Session is invalid ❌. Removing file...")
    #     os.remove(AUTH_TWITTER)
