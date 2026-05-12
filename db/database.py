# db/database.py
from pymongo import MongoClient
from logger import get_logger
from dotenv import load_dotenv
import os

load_dotenv()

logger = get_logger(__name__)

MONGO_URI = os.getenv("MONGO_URI")


client = MongoClient(MONGO_URI)
db = client["enterprise_bot"]
reviews_collection = db["reviews"]
review_analysis = db["review_analysis"]
summary_collection = db["summary"]


try:
    client.admin.command("ping")
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}", exc_info=True)
