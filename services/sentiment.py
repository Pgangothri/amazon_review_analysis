# sentiment.py

import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from logger import get_logger

load_dotenv()
logger = get_logger(__name__)

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN is not set")

client = InferenceClient(
    provider="hf-inference",
    api_key=HF_TOKEN,
)


def map_label(label: str) -> str:
    label = label.upper()
    if "NEG" in label or label == "LABEL_0":
        return "negative"
    elif "NEU" in label or label == "LABEL_1":
        return "neutral"
    else:
        return "positive"


def analyze_sentiment(text: str):
    if not text:
        logger.warning("Empty text")
        return "neutral", 0.0

    try:
        text = text[:512]
        outputs = client.text_classification(
            text,
            model="cardiffnlp/twitter-roberta-base-sentiment",
        )
        best = max(outputs, key=lambda x: x["score"])
        sentiment = map_label(best["label"])
        score = float(best["score"])
        logger.debug(f"{sentiment} ({score})")
        return sentiment, score
    except Exception:
        logger.error("Sentiment failed", exc_info=True)
        return "neutral", 0.0
