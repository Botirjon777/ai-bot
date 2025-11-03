from opensearchpy import OpenSearch
from typing import List, Dict
import os

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
            index="products-index",
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
            if not contains_gpu(f"{title} {vendor}"):
                products.append({
                    "id": src.get("id"),
                    "title": title,
                    "price": src.get("price"),
                    "vendor": vendor,
                    "sellable": src.get("sellable"),
                })
        return products[:limit]
    except Exception as e:
        print(f"OpenSearch error: {e}")
        return []