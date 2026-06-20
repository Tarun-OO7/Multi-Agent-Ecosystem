import pandas as pd
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'customer_feedback.csv')

def process_customer_data(file_path: str = None) -> str:
    path_to_use = file_path if file_path else DATA_PATH
    try:
        if not os.path.exists(path_to_use):
            return json.dumps({"error": "customer_feedback.csv not found"})
            
        df = pd.read_csv(path_to_use)
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(3)
        df['Review_Text'] = df['Review_Text'].astype(str)
        
        avg_rating = df['Rating'].mean()
        avg_rating_by_product = df.groupby('Product_ID')['Rating'].mean().to_dict()
        
        low_ratings = df[df['Rating'] <= 2]
        low_rating_segments = low_ratings[['Date', 'Product_ID', 'Review_Text', 'Rating']].tail(10).to_dict('records')
        
        # Keyword clustering
        keywords = {
            "shipping": ["shipping", "delayed", "arrived", "delivery"],
            "quality": ["broken", "damaged", "working", "latch", "quality"],
            "service": ["service", "support", "rude"]
        }
        
        clusters = {k: 0 for k in keywords.keys()}
        for text in low_ratings['Review_Text']:
            text_lower = text.lower()
            for cluster, words in keywords.items():
                if any(w in text_lower for w in words):
                    clusters[cluster] += 1
                    
        metrics = {
            "overall_average_rating": avg_rating,
            "average_rating_by_product": avg_rating_by_product,
            "complaint_clusters": clusters,
            "recent_low_rating_reviews": low_rating_segments
        }
        
        return json.dumps(metrics)
    except Exception as e:
        logger.error(f"Error processing customer data: {e}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    print(process_customer_data())
