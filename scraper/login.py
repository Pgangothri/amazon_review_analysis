from playwright.sync_api import sync_playwright
from logger import get_logger

logger = get_logger(__name__)

SESSION_FILE = "amazon_session.json"


def save_login_session():
    logger.info("Starting Amazon login session capture using Playwright")

    try:
        with sync_playwright() as p:
            logger.info("Launching Chromium browser")
            browser = p.chromium.launch(headless=False)

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            )

            page = context.new_page()

            logger.info("Opening Amazon homepage")
            page.goto("https://www.amazon.in", timeout=60000)

            page.wait_for_timeout(3000)
            logger.info("Amazon homepage loaded successfully")

            # Click Sign In
            try:
                logger.info("Trying to click Sign In button")
                page.locator("#nav-link-accountList").click()
                logger.info("Clicked Sign In button successfully")
            except Exception as e:
                logger.warning(
                    "Could not click Sign In button automatically. Manual navigation required."
                )
                logger.error(f"Sign In click error: {str(e)}")

            print("\n⚠️ LOGIN MANUALLY in the browser")
            print("After login completes (you see your name on top), press ENTER...\n")

            logger.info("Waiting for user to complete manual login")
            input()

            # Save session
            context.storage_state(path=SESSION_FILE)
            logger.info(f"Session saved successfully to {SESSION_FILE}")

            print(f"✅ Session saved to {SESSION_FILE}")

            browser.close()
            logger.info("Browser closed successfully")

    except Exception as e:
        logger.error(f"Unexpected error in save_login_session: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    save_login_session()
