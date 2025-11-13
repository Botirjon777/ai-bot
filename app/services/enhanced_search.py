# app/services/enhanced_search.py
from opensearchpy import OpenSearch
from typing import List, Dict, Optional
import os
from datetime import datetime
from ..services.session import r as redis_client
import json

# ------------------------------------------------------------------ #
# OpenSearch client
# ------------------------------------------------------------------ #
opensearch_client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "Str0ngP@ssw0rd1245!"),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False,
)

GPU_KEYWORDS = {
    "gpu", "rtx", "gtx", "radeon", "nvidia", "amd",
    "4090", "4080", "3080", "rx", "graphics card", "video card"
}

def contains_gpu(text: str) -> bool:
    return any(kw in text.lower() for kw in GPU_KEYWORDS)


# ------------------------------------------------------------------ #
# Promotion Management
# ------------------------------------------------------------------ #
class PromotionManager:
    """Manages active promotions and discounts"""
    
    @staticmethod
    def get_active_promotions() -> List[Dict]:
        """Retrieve all active promotions from Redis"""
        key = "promotions:active"
        promos = redis_client.lrange(key, 0, -1)
        active = []
        
        for promo in promos:
            try:
                data = json.loads(promo)
                # Check if promotion is still valid
                end_date = datetime.fromisoformat(data["end_date"])
                if end_date > datetime.now():
                    active.append(data)
            except Exception as e:
                print(f"Promotion parse error: {e}")
                continue
        
        return active
    
    @staticmethod
    def add_promotion(product_id: str, title: str, discount: int, end_date: str):
        """Add a new promotion (admin function)"""
        promo = {
            "product_id": product_id,
            "title": title,
            "discount": discount,
            "end_date": end_date,
            "created_at": datetime.now().isoformat()
        }
        
        key = "promotions:active"
        redis_client.lpush(key, json.dumps(promo))
        redis_client.expire(key, 7776000)  # 90 days
        return promo
    
    @staticmethod
    def is_on_promotion(product_id: str) -> Optional[Dict]:
        """Check if a specific product is on promotion"""
        promotions = PromotionManager.get_active_promotions()
        for promo in promotions:
            if promo["product_id"] == product_id:
                return promo
        return None


# ------------------------------------------------------------------ #
# Enhanced Search with Smart Filtering
# ------------------------------------------------------------------ #
def enhanced_search_products(
    query: str,
    specs: Dict,
    limit: int = 10
) -> tuple[List[Dict], List[Dict]]:
    """
    Enhanced search with specification filtering and promotion detection
    Returns: (products, promotions)
    """
    
    if contains_gpu(query):
        return [], []
    
    # Build OpenSearch query
    must_clauses = [{"term": {"sellable": True}}]
    should_clauses = [
        {"match": {"title": {"query": query, "boost": 3}}},
        {"match": {"vendor": {"query": query, "boost": 1}}},
    ]
    
    # Add specification filters
    if specs.get("cable_type"):
        cable_type = specs["cable_type"]
        should_clauses.append(
            {"match": {"title": {"query": cable_type, "boost": 2}}}
        )
    
    if specs.get("color"):
        should_clauses.append(
            {"match": {"title": {"query": specs["color"], "boost": 1.5}}}
        )
    
    # Length filter (search in title for length mentions)
    if specs.get("length_m"):
        length_m = specs["length_m"]
        should_clauses.append(
            {"match": {"title": {"query": f"{length_m}m", "boost": 1.5}}}
        )
    
    # Price range filter
    if specs.get("price_min") or specs.get("price_max"):
        price_filter = {"range": {"price": {}}}
        if specs.get("price_min"):
            price_filter["range"]["price"]["gte"] = specs["price_min"]
        if specs.get("price_max"):
            price_filter["range"]["price"]["lte"] = specs["price_max"]
        must_clauses.append(price_filter)
    
    try:
        resp = opensearch_client.search(
            index="products-index",
            body={
                "query": {
                    "bool": {
                        "should": should_clauses,
                        "must": must_clauses,
                        "minimum_should_match": 1
                    }
                },
                "size": limit * 2,
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"price": {"order": "asc"}}
                ]
            },
        )
        
        hits = resp["hits"]["hits"]
        products = []
        promoted_products = []
        
        promotions = PromotionManager.get_active_promotions()
        
        for hit in hits:
            src = hit["_source"]
            title = src.get("title", "")
            vendor = src.get("vendor", "")
            
            if not contains_gpu(f"{title} {vendor}"):
                product = {
                    "id": src.get("id"),
                    "title": title,
                    "price": src.get("price"),
                    "vendor": vendor,
                    "sellable": src.get("sellable"),
                    "score": hit["_score"]
                }
                
                # Check if on promotion
                promo = PromotionManager.is_on_promotion(product["id"])
                if promo:
                    product["promotion"] = promo
                    product["discounted_price"] = product["price"] * (1 - promo["discount"] / 100)
                    promoted_products.append(product)
                else:
                    products.append(product)
        
        # Prioritize promoted products
        final_products = (promoted_products + products)[:limit]
        
        return final_products, promotions
    
    except Exception as e:
        print(f"OpenSearch error: {e}")
        return [], []


# ------------------------------------------------------------------ #
# Product Feedback for Learning
# ------------------------------------------------------------------ #
class ProductFeedback:
    """Track product selections for learning"""
    
    @staticmethod
    def log_product_view(session_id: str, product_id: str, query: str):
        """Log when a user views a product"""
        key = f"feedback:view:{product_id}"
        data = {
            "session_id": session_id,
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        redis_client.lpush(key, json.dumps(data))
        redis_client.ltrim(key, 0, 99)
        redis_client.expire(key, 2592000)  # 30 days
    
    @staticmethod
    def log_product_click(session_id: str, product_id: str, query: str):
        """Log when a user clicks/selects a product"""
        key = f"feedback:click:{product_id}"
        data = {
            "session_id": session_id,
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        redis_client.lpush(key, json.dumps(data))
        redis_client.ltrim(key, 0, 99)
        redis_client.expire(key, 2592000)
        
        # Update product popularity score
        popularity_key = f"product:popularity:{product_id}"
        redis_client.incr(popularity_key)
        redis_client.expire(popularity_key, 2592000)
    
    @staticmethod
    def get_popular_products(cable_type: Optional[str] = None, limit: int = 5) -> List[str]:
        """Get most popular product IDs"""
        pattern = "product:popularity:*"
        keys = redis_client.keys(pattern)
        
        products_with_scores = []
        for key in keys:
            product_id = key.decode().split(":")[-1]
            score = int(redis_client.get(key) or 0)
            products_with_scores.append((product_id, score))
        
        # Sort by score
        products_with_scores.sort(key=lambda x: x[1], reverse=True)
        return [pid for pid, _ in products_with_scores[:limit]]


# ------------------------------------------------------------------ #
# Smart Search Orchestrator
# ------------------------------------------------------------------ #
def smart_search(
    query: str,
    specs: Dict,
    session_id: str,
    include_popular: bool = True
) -> Dict:
    """
    Orchestrate smart search with learning and recommendations
    """
    
    # Perform enhanced search
    products, promotions = enhanced_search_products(query, specs, limit=10)
    
    # Get popular products if results are limited
    if len(products) < 5 and include_popular:
        cable_type = specs.get("cable_type")
        popular_ids = ProductFeedback.get_popular_products(cable_type, limit=3)
        # You'd fetch these products from OpenSearch by ID
        # For now, we'll just note that we should show popular items
    
    # Log views for learning
    for product in products[:5]:
        ProductFeedback.log_product_view(session_id, product["id"], query)
    
    return {
        "products": products,
        "promotions": promotions,
        "has_promotions": len([p for p in products if "promotion" in p]) > 0,
        "total_results": len(products)
    }