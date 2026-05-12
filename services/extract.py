from pymongo.errors import DuplicateKeyError

from .sentiment import analyze_sentiment
from .keywords import get_keywords
from db.database import reviews_collection, review_analysis, summary_collection
from utils.helpers import clean_text
from logger import get_logger


logger = get_logger(__name__)


def process_reviews():
    positive_reviews = []
    negative_reviews = []

    logger.info("Processing reviews...")

    for doc in reviews_collection.find():
        review_id = doc["_id"]
        text = doc.get("review_body", "")

        if not text:
            continue

        text_clean = clean_text(text)

        if not text_clean or len(text_clean.split()) < 3:
            continue

        try:
            sentiment, score = analyze_sentiment(text_clean)
        except Exception as e:
            logger.error(f"Sentiment failed for {review_id}: {e}")
            continue

        if sentiment == "positive":
            positive_reviews.append(text_clean)

        elif sentiment == "negative":
            negative_reviews.append(text_clean)

        analysis_doc = {"_id": review_id, "sentiment": sentiment, "score": score}

        try:
            review_analysis.insert_one(analysis_doc)
        except DuplicateKeyError:
            logger.warning(f"Review {review_id} already processed")

    logger.info("Sentiment analysis completed")
    logger.info("Extracting global keywords...")

    top_positive_keywords = get_keywords(positive_reviews, top_n=20)
    top_negative_keywords = get_keywords(negative_reviews, top_n=20)

    logger.info(f"Top Positive Keywords: {top_positive_keywords}")
    logger.info(f"Top Negative Keywords: {top_negative_keywords}")

    summary_doc = {
        "type": "global_summary",
        "total_reviews": len(positive_reviews) + len(negative_reviews),
        "positive_count": len(positive_reviews),
        "negative_count": len(negative_reviews),
        "top_positive_keywords": top_positive_keywords,
        "top_negative_keywords": top_negative_keywords,
    }

    try:
        summary_collection.insert_one(summary_doc)
        logger.info("Summary saved to DB")
    except Exception as e:
        logger.error(f"Failed to save summary: {e}")


if __name__ == "__main__":
    process_reviews()
