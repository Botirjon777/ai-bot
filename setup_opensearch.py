from opensearchpy import OpenSearch
import json

# OpenSearch Configuration
client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    http_auth=('admin', 'Str0ngP@ssw0rd1245!'),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False
)

def create_products_index():
    """Create products index with proper mapping"""
    
    index_name = 'products'
    
    # Delete index if exists
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)
        print(f"Deleted existing index: {index_name}")
    
    # Create index with mapping
    index_body = {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'analysis': {
                'analyzer': {
                    'product_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': ['lowercase', 'stop', 'snowball']
                    }
                }
            }
        },
        'mappings': {
            'properties': {
                'name': {
                    'type': 'text',
                    'analyzer': 'product_analyzer',
                    'fields': {
                        'keyword': {'type': 'keyword'}
                    }
                },
                'description': {
                    'type': 'text',
                    'analyzer': 'product_analyzer'
                },
                'category': {
                    'type': 'keyword'
                },
                'price': {
                    'type': 'float'
                },
                'stock_quantity': {
                    'type': 'integer'
                },
                'is_active': {
                    'type': 'boolean'
                },
                'tags': {
                    'type': 'keyword'
                },
                'sku': {
                    'type': 'keyword'
                },
                'image_url': {
                    'type': 'keyword'
                },
                'created_at': {
                    'type': 'date'
                },
                'updated_at': {
                    'type': 'date'
                }
            }
        }
    }
    
    client.indices.create(index=index_name, body=index_body)
    print(f"Created index: {index_name}")

def insert_sample_products():
    """Insert sample cable products"""
    
    sample_products = [
        {
            'name': 'USB-C to USB-C Cable 2m',
            'description': 'High-speed USB-C cable supporting 100W power delivery and 10Gbps data transfer. Perfect for charging laptops and transferring large files.',
            'category': 'USB Cables',
            'price': 19.99,
            'stock_quantity': 150,
            'is_active': True,
            'tags': ['usb-c', 'fast-charging', 'data-transfer', 'pd'],
            'sku': 'USBC-2M-001',
            'image_url': '/images/usbc-cable.jpg'
        },
        {
            'name': '24-Pin ATX Power Cable Custom Sleeved',
            'description': 'Custom sleeved 24-pin ATX motherboard power cable. Available in multiple colors with premium cable combs.',
            'category': 'PC Power Cables',
            'price': 34.99,
            'stock_quantity': 0,
            'is_active': True,
            'tags': ['24-pin', 'atx', 'power', 'custom', 'sleeved'],
            'sku': 'ATX24-CUSTOM-001',
            'image_url': '/images/24pin-cable.jpg'
        },
        {
            'name': '8-Pin PCIe Power Cable',
            'description': '8-pin (6+2) PCIe power cable for graphics cards. High quality copper wires for stable power delivery.',
            'category': 'PC Power Cables',
            'price': 12.99,
            'stock_quantity': 200,
            'is_active': True,
            'tags': ['8-pin', 'pcie', 'gpu', 'power'],
            'sku': 'PCIE8-001',
            'image_url': '/images/pcie-cable.jpg'
        },
        {
            'name': 'HDMI 2.1 Cable 3m - 8K Support',
            'description': 'Ultra high-speed HDMI 2.1 cable supporting 8K@60Hz and 4K@120Hz. Perfect for gaming and high-resolution displays.',
            'category': 'Video Cables',
            'price': 29.99,
            'stock_quantity': 85,
            'is_active': True,
            'tags': ['hdmi', '8k', '4k', 'gaming', 'high-speed'],
            'sku': 'HDMI21-3M-001',
            'image_url': '/images/hdmi-cable.jpg'
        },
        {
            'name': 'DisplayPort 1.4 Cable 2m',
            'description': 'DisplayPort 1.4 cable with HBR3 support for 8K displays. Gold-plated connectors for reliable connection.',
            'category': 'Video Cables',
            'price': 24.99,
            'stock_quantity': 120,
            'is_active': True,
            'tags': ['displayport', 'dp', '8k', 'hbr3'],
            'sku': 'DP14-2M-001',
            'image_url': '/images/dp-cable.jpg'
        },
        {
            'name': 'Cat8 Ethernet Cable 5m',
            'description': 'Category 8 ethernet cable supporting 40Gbps speeds. Shielded design for minimal interference.',
            'category': 'Network Cables',
            'price': 22.99,
            'stock_quantity': 95,
            'is_active': True,
            'tags': ['ethernet', 'cat8', 'network', '40gbps', 'shielded'],
            'sku': 'CAT8-5M-001',
            'image_url': '/images/cat8-cable.jpg'
        },
        {
            'name': 'Custom RGB Cable Extension Kit',
            'description': 'Complete cable extension kit with RGB lighting. Includes 24-pin ATX, 8-pin EPS, and 8-pin PCIe cables.',
            'category': 'Cable Kits',
            'price': 89.99,
            'stock_quantity': 45,
            'is_active': True,
            'tags': ['custom', 'rgb', 'extension', 'kit', 'pc-building'],
            'sku': 'RGB-KIT-001',
            'image_url': '/images/rgb-kit.jpg'
        },
        {
            'name': 'USB 3.0 Extension Cable 3m',
            'description': 'USB 3.0 (Type-A) extension cable with gold-plated connectors. Supports 5Gbps data transfer.',
            'category': 'USB Cables',
            'price': 14.99,
            'stock_quantity': 180,
            'is_active': True,
            'tags': ['usb', 'usb3', 'extension', 'type-a'],
            'sku': 'USB3-EXT-3M-001',
            'image_url': '/images/usb3-ext.jpg'
        },
        {
            'name': 'Thunderbolt 4 Cable 1m',
            'description': 'Certified Thunderbolt 4 cable with 40Gbps transfer speed and 100W charging capability.',
            'category': 'Thunderbolt Cables',
            'price': 49.99,
            'stock_quantity': 60,
            'is_active': True,
            'tags': ['thunderbolt', 'tb4', 'usb4', '40gbps', 'certified'],
            'sku': 'TB4-1M-001',
            'image_url': '/images/tb4-cable.jpg'
        },
        {
            'name': 'Cable Management Sleeve Kit',
            'description': 'Flexible cable sleeve kit for organizing and protecting cables. Includes 5 sleeves of various sizes.',
            'category': 'Cable Accessories',
            'price': 16.99,
            'stock_quantity': 220,
            'is_active': True,
            'tags': ['management', 'sleeve', 'organization', 'accessory'],
            'sku': 'SLEEVE-KIT-001',
            'image_url': '/images/sleeve-kit.jpg'
        }
    ]
    
    # Insert products
    for idx, product in enumerate(sample_products):
        try:
            response = client.index(
                index='products',
                id=f'prod_{idx+1}',
                body=product
            )
            print(f"Inserted: {product['name']}")
        except Exception as e:
            print(f"Error inserting {product['name']}: {e}")
    
    # Refresh index
    client.indices.refresh(index='products')
    print(f"\nInserted {len(sample_products)} sample products")

def verify_setup():
    """Verify the setup"""
    try:
        count = client.count(index='products')
        print(f"\nTotal products in index: {count['count']}")
        
        # Test search
        result = client.search(
            index='products',
            body={
                'query': {'match': {'category': 'USB Cables'}},
                'size': 3
            }
        )
        print(f"\nSample USB cables found: {result['hits']['total']['value']}")
        for hit in result['hits']['hits']:
            print(f"  - {hit['_source']['name']}")
    except Exception as e:
        print(f"Verification error: {e}")

if __name__ == '__main__':
    print("Setting up OpenSearch for Cable Store AI...")
    print("-" * 50)
    
    create_products_index()
    print()
    insert_sample_products()
    print()
    verify_setup()
    
    print("\n" + "=" * 50)
    print("Setup complete! OpenSearch is ready.")
    print("=" * 50)