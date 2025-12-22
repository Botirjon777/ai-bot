from opensearchpy import OpenSearch
from typing import List, Dict

from ..config import get_config
from ..utils.logging import get_logger

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

# ------------------------------------------------------------------ #
# GPU filter
# ------------------------------------------------------------------ #
GPU_KEYWORDS = {
    "gpu", "rtx", "gtx", "radeon", "nvidia", "amd",
    "4090", "4080", "3080", "rx", "graphics card", "video card"
}

def contains_gpu(text: str) -> bool:
    return any(kw in text.lower() for kw in GPU_KEYWORDS)


# ------------------------------------------------------------------ #
# Search
# ------------------------------------------------------------------ #
def search_products(query: str, limit: int = 5) -> List[Dict]:
    if contains_gpu(query):
        return []

    try:
        resp = opensearch_client.search(
            index=config.opensearch.index_name,
            body={
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"title": {"query": query, "boost": 2}}},
                            {"match": {"vendor": {"query": query}}},
                        ],
                        "must": [{"term": {"sellable": True}}]
                    }
                },
                "size": limit * 3,
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
                products.append({
                    "id": src.get("id"),
                    "title": title,
                    "price": src.get("price"),
                    "vendor": vendor,
                    "sellable": sellable,
                    "slug": src.get("slug"),
                })
        return products[:limit]
    except Exception as e:
        logger.error(f"OpenSearch error: {e}")
        return []