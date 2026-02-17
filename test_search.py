#!/usr/bin/env python3
"""Test script to verify search returns only sellable products with slugs"""

from opensearchpy import OpenSearch
import json

# Connect to OpenSearch
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False,
)

print("Testing: Search for '24 pin cable' with sellable filter")
print("=" * 80)

try:
    response = client.search(
        index="products-index",
        body={
            "query": {
                "bool": {
                    "should": [
                        {"match": {"title": {"query": "24 pin cable", "boost": 2}}},
                        {"match": {"vendor": {"query": "24 pin cable"}}},
                    ],
                    "must": [{"term": {"sellable": True}}]
                }
            },
            "size": 15,
        }
    )
    
    hits = response["hits"]["hits"]
    print(f"\nTotal hits: {len(hits)}")
    print(f"Total available: {response['hits']['total']['value']}")
    print("\nProducts returned:")
    print("-" * 80)
    
    sellable_count = 0
    non_sellable_count = 0
    missing_slug_count = 0
    
    for i, hit in enumerate(hits, 1):
        src = hit["_source"]
        sellable = src.get("sellable", False)
        slug = src.get("slug")
        
        if sellable:
            sellable_count += 1
        else:
            non_sellable_count += 1
            
        if not slug:
            missing_slug_count += 1
        
        print(f"\n{i}. {src.get('title')}")
        print(f"   ID: {src.get('id')}")
        print(f"   Price: ${src.get('price')}")
        print(f"   Vendor: {src.get('vendor')}")
        print(f"   Sellable: {sellable} {'OK' if sellable else 'PROBLEM!'}")
        print(f"   Slug: {slug if slug else 'MISSING!'}")
    
    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Sellable products: {sellable_count}")
    print(f"  Non-sellable products: {non_sellable_count}")
    print(f"  Missing slugs: {missing_slug_count}")
    
    if non_sellable_count > 0:
        print(f"\nWARNING: {non_sellable_count} non-sellable products found!")
    if missing_slug_count > 0:
        print(f"\nWARNING: {missing_slug_count} products missing slug!")
    
    if non_sellable_count == 0 and missing_slug_count == 0:
        print("\nSUCCESS: All tests passed! Only sellable products with slugs returned.")
    
except Exception as e:
    print(f"Error: {e}")
