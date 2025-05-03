from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headless=False so you can log in manually
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://x.com/login")

    input("Log in to Twitter manually, then press Enter here...")

    context.storage_state(path="twitter_auth.json")  # Save cookies/session
    browser.close()