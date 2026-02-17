#!/usr/bin/env python3
"""Test OpenSearch with requests library"""

import requests
import json

print("Testing OpenSearch with requests library...")
print("=" * 80)

try:
    # Test basic connection
    print("\n1. Testing basic connection...")
    response = requests.get("http://localhost:9200")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    # Test search
    print("\n2. Testing search query...")
    search_body = {
        "query": {
            "bool": {
                "should": [
                    {"match": {"title": {"query": "24 pin", "boost": 2}}},
                ],
                "must": [{"term": {"sellable": True}}]
            }
        },
        "size": 5
    }
    
    response = requests.post(
        "http://localhost:9200/products-index/_search",
        json=search_body,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total hits: {data['hits']['total']['value']}")
        print(f"   Products returned: {len(data['hits']['hits'])}")
        for hit in data['hits']['hits'][:3]:
            src = hit['_source']
            print(f"      - {src.get('title')} (${src.get('price')})")
    else:
        print(f"   Error: {response.text}")
        
except Exception as e:
    print(f"   FAILED: {e}")

print("\n" + "=" * 80)
