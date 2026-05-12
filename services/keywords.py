from sklearn.feature_extraction.text import TfidfVectorizer
from logger import get_logger
logger= get_logger(__name__)

def get_keywords(text_list, top_n=10):
    if not text_list or all(not t.strip() for t in text_list):
        logger.warning("No valid text provided for keyword extraction.")
        return []

    vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)

    try:
        
        X = vectorizer.fit_transform(text_list)
    except ValueError:
        logger.error("Error occurred while fitting TF-IDF vectorizer.")
        return []  

    feature_names = vectorizer.get_feature_names_out()
    scores = X.toarray().sum(axis=0)

    keywords = [feature_names[i] for i in scores.argsort()[::-1][:top_n]]

    return keywords
