#!/usr/bin/env python3
"""Quick test to verify OpenSearch connection"""

from opensearchpy import OpenSearch

# Test different connection configurations
print("Testing OpenSearch connection...")
print("=" * 80)

# Configuration 1: HTTP without auth
try:
    print("\n1. Testing HTTP without auth (http://localhost:9200)...")
    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9200, "scheme": "http"}],
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
    )
    info = client.info()
    print(f"   SUCCESS! Connected to: {info['cluster_name']}")
    print(f"   Version: {info['version']['number']}")
except Exception as e:
    print(f"   FAILED: {e}")

# Configuration 2: Without scheme specified
try:
    print("\n2. Testing without scheme specified...")
    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
    )
    info = client.info()
    print(f"   SUCCESS! Connected to: {info['cluster_name']}")
except Exception as e:
    print(f"   FAILED: {e}")

# Configuration 3: Using URL format
try:
    print("\n3. Testing with URL format...")
    client = OpenSearch(
        hosts=["http://localhost:9200"],
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
    )
    info = client.info()
    print(f"   SUCCESS! Connected to: {info['cluster_name']}")
except Exception as e:
    print(f"   FAILED: {e}")

print("\n" + "=" * 80)
