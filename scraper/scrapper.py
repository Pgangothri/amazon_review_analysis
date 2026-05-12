import asyncio
import random
import re
from playwright.async_api import async_playwright
from db.database import reviews_collection
from logger import get_logger

logger = get_logger(__name__)

SESSION_FILE = "amazon_session.json"


async def extract_review_title(review_element):
    try:
        logger.debug("Extracting review title")

        title = await review_element.evaluate(
            """(el) => {
                const link = el.querySelector('[data-hook="review-title"]');
                if (!link) return '';
                const spans = link.querySelectorAll('span');
                if (spans.length > 0) {
                    return spans[spans.length - 1].innerText.trim();
                }
                return (link.innerText || '').trim();
            }"""
        )

        title = title.replace("\\n", "").strip()

        if not title:
            title = "not available"

        logger.debug(f"Extracted title: {title}")
        return title

    except Exception as e:
        logger.error(f"Error extracting title: {str(e)}", exc_info=True)
        return "not available"


async def extract_product_colour(review_element):
    try:
        logger.debug("Extracting product colour")

        colour = await review_element.evaluate(
            """(el) => {
                const n = el.querySelector('[data-hook="format-strip"]');
                return n ? n.innerText : '';
            }"""
        )

        colour = colour.replace("Colour:", "").strip()

        if not colour:
            colour = "not available"

        return colour

    except Exception as e:
        logger.error(f"Error extracting colour: {str(e)}", exc_info=True)
        return "not available"


def infer_colour_from_text(text: str):
    colors = ["Black", "White", "Blue", "Red", "Green", "Purple", "Silver", "Gold"]
    for c in colors:
        if re.search(rf"\b{c}\b", text, re.IGNORECASE):
            return c
    return "not available"


async def extract_review_body(review_element):
    try:
        logger.debug("Extracting review body")

        body = await review_element.evaluate(
            """(el) => {
                const full = el.querySelector('div.cr-full-content [data-hook="review-body"]');
                const short = el.querySelector('[data-hook="review-body"]');
                const node = full || short;
                return node ? node.innerText : '';
            }"""
        )

        body = body.replace("\n", " ").strip()

        if not body:
            body = "not available"

        return body

    except Exception as e:
        logger.error(f"Error extracting body: {str(e)}", exc_info=True)
        return "not available"


async def extract_rating(review_element):
    try:
        logger.debug("Extracting rating")

        ratings = await review_element.evaluate(
            """(el) => {
                const n = el.querySelector('[data-hook="review-star-rating"]');
                return n ? n.innerText : '';
            }"""
        )

        rating = ratings.split()[0] if ratings else "not available"
        return rating

    except Exception as e:
        logger.error(f"Error extracting rating: {str(e)}", exc_info=True)
        return "not available"


async def extract_verified(review_element):
    try:
        logger.debug("Checking verified purchase")

        is_verified = await review_element.evaluate(
            """(el) => !!(
                el.querySelector('[data-hook="avp-badge"]')
                || el.querySelector('[data-hook="msrp-avp-badge-linkless"]')
            )"""
        )

        return bool(is_verified)

    except Exception as e:
        logger.error(f"Error extracting verified flag: {str(e)}", exc_info=True)
        return False


def extract_storage_variant(text: str):
    try:
        m = re.search(r"(\d+\s?GB)", text, re.IGNORECASE)
        if m:
            return m.group(1).upper().replace(" ", "")
    except Exception:
        pass
    return "not available"


async def perform_request_with_retry(page, link):
    MAX_RETRIES = 5
    retry_count = 0

    logger.info(f"Navigating to URL with retry: {link}")

    while retry_count < MAX_RETRIES:
        try:
            await page.goto(link, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            logger.info("Page loaded successfully")
            return

        except Exception as e:
            retry_count += 1
            logger.warning(f"Retry {retry_count}/{MAX_RETRIES} failed: {str(e)}")

            if retry_count == MAX_RETRIES:
                logger.error("Max retries reached. Request failed.")
                raise Exception("Request timed out")

            await asyncio.sleep(random.uniform(1, 5))


def save_reviews_to_mongodb(reviews):
    if not reviews:
        logger.warning("No reviews found to insert into MongoDB")
        return

    result = reviews_collection.insert_many(reviews)
    logger.info(f"Inserted {len(result.inserted_ids)} reviews into MongoDB")


async def extract_reviews(page, max_pages=None):
    reviews = []
    seen = set()
    page_count = 0

    logger.info("Starting review extraction")

    while True:
        await page.wait_for_selector("[data-hook='review']")
        logger.info(f"Scraping page {page_count + 1}")

        # show more reviews
        show_more = page.locator("a[data-hook='show-more-button']")
        if await show_more.count() > 0:
            try:
                logger.info("Clicking 'Show more reviews'")
                await show_more.first.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Show more click failed: {str(e)}")

        review_elements = await page.query_selector_all("[data-hook='review']")
        logger.info(f"Found {len(review_elements)} reviews")

        for review_element in review_elements:
            title = await extract_review_title(review_element)
            body = await extract_review_body(review_element)
            rating = await extract_rating(review_element)
            verified = await extract_verified(review_element)
            product_colour = await extract_product_colour(review_element)

            if product_colour == "not available":
                product_colour = infer_colour_from_text(title + " " + body)

            storage_variant = extract_storage_variant(title + " " + body)

            key = (title, body, rating, storage_variant, verified, product_colour)
            if key in seen:
                continue
            seen.add(key)

            reviews.append(
                {
                    "review_title": title,
                    "review_body": body,
                    "rating": rating,
                    "storage_variant": storage_variant,
                    "verified_purchase": verified,
                    "product_colour": product_colour,
                }
            )

        page_count += 1

        if max_pages and page_count >= max_pages:
            logger.info("Max page limit reached")
            break

        next_page = await page.query_selector("li.a-last:not(.a-disabled) a")
        if next_page:
            try:
                logger.info("Navigating to next page")
                async with page.expect_navigation(wait_until="networkidle"):
                    await next_page.click()
                await asyncio.sleep(1)
                continue
            except Exception as e:
                logger.error(f"Next page navigation failed: {str(e)}")
                break

        logger.info("No more pages left")
        break

    return reviews


async def main():
    logger.info("Starting Amazon scraper")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state=SESSION_FILE)
        page = await context.new_page()

        product_url = "https://www.amazon.in/Apple-New-iPhone-12-128GB/dp/B08L5TNJHG/"
        asin_match = re.search(r"/dp/([A-Z0-9]{10})", product_url)

        if not asin_match:
            logger.error("Invalid product URL")
            raise ValueError("Invalid product URL")

        asin = asin_match.group(1)

        reviews_url = (
            f"https://www.amazon.in/product-reviews/{asin}/"
            f"?ie=UTF8&reviewerType=all_reviews&sortBy=recent&formatType=current_format"
        )

        logger.info(f"Opening reviews URL: {reviews_url}")

        await perform_request_with_retry(page, reviews_url)

        reviews = await extract_reviews(page, max_pages=10)

        save_reviews_to_mongodb(reviews)

        logger.info(f"Scraping completed. Total reviews: {len(reviews)}")

        await browser.close()
        logger.info("Browser closed")


if __name__ == "__main__":
    asyncio.run(main())
