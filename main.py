from fastapi import FastAPI, HTTPException
from models.models import ReviewInput, SentimentResponse, ReviewFilter
from services.sentiment import analyze_sentiment
from logger import get_logger
from redis_cache import redis_client
from db.mongo import fetch_reviews, count_reviews, insert_review
from db.database import review_analysis, reviews_collection
import json

logger = get_logger(__name__)

app = FastAPI(title="Amazon Review Analysis API", version="1.0")


@app.get("/")
def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to the Amazon Review Analysis API!"}


@app.post("/sentiment", response_model=SentimentResponse)
async def get_sentiment(review: ReviewInput):
    logger.info("Sentiment analysis request received")

    try:
        sentiment, score = analyze_sentiment(review.review_text)
        document = {
            "review_title": review.review_title,
            "review_body": review.review_text,
            "rating": review.rating,
            "storage_variant": review.storage_variant,
            "verified_purchase": review.verified_purchase,
            "product_colour": review.color,
        }
        inserted=insert_review(document, collection=reviews_collection)
        review_id = inserted.inserted_id
        analysis_document = {
            "_id": review_id,
            "sentiment": sentiment,
            "score": score,
        }
        insert_review(analysis_document, collection=review_analysis)

        logger.info(f"Sentiment result: {sentiment}, score: {score}")

        return SentimentResponse(sentiment=sentiment, score=score)

    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/reviews")
async def get_reviews(filters: ReviewFilter):
    logger.info(f"Review filter request received: {filters.dict()}")

    try:
        query = {}

        if filters.color:
            query["product_colour"] = {"$regex": filters.color, "$options": "i"}

        if filters.storage_variant:
            query["storage_variant"] = filters.storage_variant

        if filters.min_rating is not None:
            query["rating"] = {"$gte": filters.min_rating}

        page = max(filters.page, 1)
        limit = max(filters.limit, 1)
        skip = (page - 1) * limit

        cache_key = f"reviews:p{page}:l{limit}:c{filters.color or 'all'}:s{filters.storage_variant or 'all'}:r{filters.min_rating or 'all'}"

        cached_data = redis_client.get(cache_key)

        if cached_data:
            logger.info("Cache HIT - returning Redis data")
            return json.loads(cached_data)

        logger.info("Cache MISS - calling MongoDB service layer")

        results = fetch_reviews(query, skip, limit)
        total_count = count_reviews(query)

        response = {
            "page": page,
            "limit": limit,
            "total": total_count,
            "pages": (total_count + limit - 1) // limit,
            "count": len(results),
            "reviews": results,
        }

        redis_client.setex(cache_key, 600, json.dumps(response))

        logger.info("Response cached in Redis")

        return response

    except Exception as e:
        logger.error(f"Error fetching reviews: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
