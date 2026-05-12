from db.database import reviews_collection
from logger import get_logger

logger = get_logger(__name__)


def fetch_reviews(query: dict, skip: int, limit: int):
    """
    Fetch paginated reviews from MongoDB with error handling
    """

    try:
        logger.info(f"MongoDB query executed: {query}")
        logger.info(f"skip={skip}, limit={limit}")

        cursor = reviews_collection.find(query, {"_id": 0}).skip(skip).limit(limit)
        results = list(cursor)

        logger.info(f"Fetched {len(results)} reviews from MongoDB")

        return results

    except Exception as e:
        logger.error(f"MongoDB fetch_reviews failed: {str(e)}", exc_info=True)
        return []


def count_reviews(query: dict):
    """
    Count total matching documents
    """
    try:
        logger.info(f"Counting reviews with query: {query}")
        total = reviews_collection.count_documents(query)
        logger.info(f"Total matching reviews: {total}")
        return total
    except Exception as e:
        logger.error(f"MongoDB count_reviews failed: {str(e)}", exc_info=True)
        return 0


def insert_review(review: dict, collection=reviews_collection):
    """
    Insert a review document into MongoDB
    """
    try:
        result = collection.insert_one(review)
        logger.info(f"Inserted review with id: {result.inserted_id}")
        return result
    except Exception as e:
        logger.error(f"MongoDB insert_review failed: {str(e)}", exc_info=True)
        return None
