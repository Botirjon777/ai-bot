#!/usr/bin/env python3
"""Quick script to check OpenSearch index structure and sample data"""

from opensearchpy import OpenSearch
import json

# Connect to OpenSearch
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "Str0ngP@ssw0rd1245!"),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False,
)

# Get a sample document
try:
    response = client.search(
        index="products-index",
        body={
            "query": {"match": {"title": "24 pin"}},
            "size": 3
        }
    )
    
    print("Sample products from OpenSearch:")
    print("=" * 80)
    
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        print(f"\nProduct ID: {source.get('id')}")
        print(f"Title: {source.get('title')}")
        print(f"Price: ${source.get('price')}")
        print(f"Vendor: {source.get('vendor')}")
        print(f"Sellable: {source.get('sellable')}")
        print(f"Slug: {source.get('slug', 'NOT FOUND')}")
        print(f"Available fields: {list(source.keys())}")
        print("-" * 80)
        
except Exception as e:
    print(f"Error: {e}")
