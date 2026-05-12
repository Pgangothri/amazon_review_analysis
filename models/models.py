from pydantic import BaseModel
from typing import Optional


class ReviewInput(BaseModel):
    review_title: Optional[str]
    review_text: str
    rating: float
    storage_variant: Optional[str]
    color: Optional[str]
    verified_purchase: bool = False


class SentimentResponse(BaseModel):
    sentiment: str
    score: float


class ReviewFilter(BaseModel):
    color: Optional[str] = None
    storage_variant: Optional[str] = None
    min_rating: Optional[float] = None
    page: int = 1
    limit: int = 10
