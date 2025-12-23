# app/services/enhanced_search.py
from opensearchpy import OpenSearch
from typing import List, Dict, Optional
from datetime import datetime
from ..config import get_config
from ..utils.logging import get_logger
import json

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
config = get_config()
logger = get_logger(__name__)

# ------------------------------------------------------------------ #
# OpenSearch client
# ------------------------------------------------------------------ #
opensearch_client = OpenSearch(
    hosts=[{"host": config.opensearch.host, "port": config.opensearch.port}],
    http_auth=(config.opensearch.user, config.opensearch.password),
    use_ssl=config.opensearch.use_ssl,
    verify_certs=config.opensearch.verify_certs,
    ssl_show_warn=False,
)

GPU_KEYWORDS = {
    "gpu", "rtx", "gtx", "radeon", "nvidia", "amd",
    "4090", "4080", "3080", "rx", "graphics card", "video card"
}

def contains_gpu(text: str) -> bool:
    return any(kw in text.lower() for kw in GPU_KEYWORDS)


# ------------------------------------------------------------------ #
# Promotion Management (DISABLED - requires Redis)
# ------------------------------------------------------------------ #
class PromotionManager:
    """Manages active promotions and discounts (DISABLED without Redis)"""
    
    @staticmethod
    def get_active_promotions() -> List[Dict]:
        """Retrieve all active promotions (disabled without Redis)"""
        return []
    
    @staticmethod
    def add_promotion(product_id: str, title: str, discount: int, end_date: str):
        """Add a new promotion (disabled without Redis)"""
        logger.warning("Promotions disabled: Redis not available")
        return None
    
    @staticmethod
    def is_on_promotion(product_id: str) -> Optional[Dict]:
        """Check if a specific product is on promotion (disabled without Redis)"""
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
    Enhanced search with specification filtering
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
        
        for hit in hits:
            src = hit["_source"]
            title = src.get("title", "")
            vendor = src.get("vendor", "")
            sellable = src.get("sellable", False)
            
            # Only include sellable products and exclude GPU-related items
            if sellable and not contains_gpu(f"{title} {vendor}"):
                product = {
                    "id": src.get("id"),
                    "title": title,
                    "price": src.get("price"),
                    "vendor": vendor,
                    "sellable": sellable,
                    "slug": src.get("slug"),
                    "score": hit["_score"]
                }
                products.append(product)
        
        # Return products (promotions disabled)
        return products[:limit], []
    
    except Exception as e:
        logger.error(f"OpenSearch error: {e}")
        return [], []


# ------------------------------------------------------------------ #
# Product Feedback for Learning (DISABLED - requires Redis)
# ------------------------------------------------------------------ #
class ProductFeedback:
    """Track product selections for learning (DISABLED without Redis)"""
    
    @staticmethod
    def log_product_view(session_id: str, product_id: str, query: str):
        """Log when a user views a product (disabled without Redis)"""
        pass
    
    @staticmethod
    def log_product_click(session_id: str, product_id: str, query: str):
        """Log when a user clicks/selects a product (disabled without Redis)"""
        pass
    
    @staticmethod
    def get_popular_products(cable_type: Optional[str] = None, limit: int = 5) -> List[str]:
        """Get most popular product IDs (disabled without Redis)"""
        return []


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
    Orchestrate smart search
    """
    
    # Perform enhanced search
    products, promotions = enhanced_search_products(query, specs, limit=10)
    
    return {
        "products": products,
        "promotions": promotions,
        "has_promotions": False,
        "total_results": len(products)
    }