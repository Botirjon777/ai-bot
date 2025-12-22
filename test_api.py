#!/usr/bin/env python3
"""Test the complete chat API endpoint"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing Complete Chat API Flow")
print("=" * 80)

# Step 1: Initialize session
print("\n1. Initializing session...")
session_response = requests.get(f"{BASE_URL}/api/session")
if session_response.status_code == 200:
    session_data = session_response.json()
    session_id = session_data.get("session_id")
    cookies = session_response.cookies
    print(f"   Session ID: {session_id}")
    print(f"   Cookies: {dict(cookies)}")
else:
    print(f"   ERROR: {session_response.status_code}")
    exit(1)

# Step 2: Send chat message
print("\n2. Sending chat message: 'i need 24 pin cable'")
chat_response = requests.post(
    f"{BASE_URL}/api/chat",
    json={"message": "i need 24 pin cable"},
    cookies=cookies
)

if chat_response.status_code == 200:
    chat_data = chat_response.json()
    print(f"   Status: SUCCESS")
    print(f"\n   AI Response:")
    print(f"   {chat_data.get('response', 'No response')[:200]}...")
    
    products = chat_data.get("suggested_products", [])
    print(f"\n   Suggested Products: {len(products)}")
    
    if products:
        print("\n" + "-" * 80)
        for i, product in enumerate(products, 1):
            print(f"\n   Product {i}:")
            print(f"      ID: {product.get('id')}")
            print(f"      Title: {product.get('title')}")
            print(f"      Price: ${product.get('price')}")
            print(f"      Vendor: {product.get('vendor')}")
            print(f"      Slug: {product.get('slug', 'MISSING!')}")
            
            if not product.get('slug'):
                print(f"      ERROR: Slug is missing!")
        
        print("\n" + "=" * 80)
        print(f"Summary:")
        
        missing_slugs = sum(1 for p in products if not p.get('slug'))
        print(f"  Total products returned: {len(products)}")
        print(f"  Products with slugs: {len(products) - missing_slugs}")
        print(f"  Products missing slugs: {missing_slugs}")
        
        if missing_slugs == 0:
            print("\n  SUCCESS: All products have slugs!")
        else:
            print(f"\n  ERROR: {missing_slugs} products are missing slugs!")
    else:
        print("\n   WARNING: No products returned!")
else:
    print(f"   ERROR: {chat_response.status_code}")
    print(f"   Response: {chat_response.text}")
