# AI Chatbot for Cable E-commerce Store

A comprehensive AI-powered chatbot system that helps customers find the right cables and accessories. Built with Python FastAPI backend and Next.js frontend.

## 🎯 Features

- **Intelligent Product Search**: Uses OpenSearch for fast, relevant product searches
- **Context-Aware Conversations**: Remembers conversation history for better assistance
- **Stock-Aware Recommendations**: Only recommends available products, mentions out-of-stock items
- **Scope-Limited Responses**: Only discusses cable-related products, politely declines off-topic queries
- **FAQ Quick Access**: Predefined answers to common questions
- **Product Suggestions**: Shows relevant products with availability status
- **Persistent Sessions**: Maintains conversation context across interactions
- **Beautiful UI**: User-friendly chat interface that appears on every page

gpt-3.5-turbo

## 📁 Project Structure

```
cable-store-ai/
├── python-backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt        # Python dependencies
│   ├── setup_opensearch.py     # OpenSearch setup script
│   ├── Dockerfile
│   └── .env
├── nextjs-frontend/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with chatbot
│   │   └── api/
│   │       └── chat/
│   │           └── route.ts    # API proxy route
│   ├── components/
│   │   └── AIChatbot.tsx       # Main chatbot component
│   └── package.json
└── docker-compose.yml
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenSearch running on `https://localhost:9200`
- OpenAI API key

### Step 1: Setup Python Backend

```bash
# Navigate to python backend directory
cd python-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Step 2: Setup OpenSearch

```bash
# Run the OpenSearch setup script
python setup_opensearch.py
```

This will:
- Create the `products` index
- Insert sample cable products
- Verify the setup

### Step 3: Start Python Backend

```bash
# Run the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Step 4: Setup Next.js Frontend

```bash
# Navigate to Next.js project
cd ../nextjs-frontend

# Install dependencies
npm install

# Copy the AIChatbot component
# Copy components/AIChatbot.tsx to your project
# Update app/layout.tsx to include the chatbot
```

### Step 5: Start Next.js application

```bash
npm run dev
```

Your application will be available at `http://localhost:3000`

## 🐳 Docker Setup (Alternative)

```bash
# Set your OpenAI API key in .env
echo "OPENAI_API_KEY=your-key-here" > .env

# Start all services
docker-compose up -d

# Setup OpenSearch (run once)
docker-compose exec chatbot-api python setup_opensearch.py
```

## 🔧 Configuration

### Environment Variables

**Python Backend (.env)**
```env
OPENAI_API_KEY=your-openai-api-key
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=Str0ngP@ssw0rd1245!
REDIS_URL=redis://localhost:6379
```

**Next.js (.env.local)**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
PYTHON_API_URL=http://localhost:8000
```

### OpenSearch Index Structure

The `products` index contains:
- `name`: Product name (text, analyzed)
- `description`: Product description (text, analyzed)
- `category`: Product category (keyword)
- `price`: Product price (float)
- `stock_quantity`: Available stock (integer)
- `is_active`: Product active status (boolean)
- `tags`: Product tags (keyword array)
- `sku`: Stock keeping unit (keyword)
- `image_url`: Product image URL (keyword)

## 📊 API Endpoints

### Python Backend

**POST /api/chat**
```json
{
  "session_id": "session_123",
  "message": "I need a USB-C cable for my laptop",
  "user_info": {
    "timestamp": "2025-10-31T10:00:00Z"
  }
}
```

**Response:**
```json
{
  "response": "I can help you with that! We have...",
  "session_id": "session_123",
  "suggested_products": [
    {
      "id": "prod_1",
      "name": "USB-C to USB-C Cable 2m",
      "price": 19.99,
      "stock_quantity": 150
    }
  ]
}
```

**GET /api/faq**
- Returns list of frequently asked questions

**DELETE /api/session/{session_id}**
- Clears chat session

**POST /api/search-products**
- Search products directly

## 💡 How It Works

### 1. User Interaction Flow

```
User Message → Next.js Component → Python API → OpenAI + OpenSearch → Response
                                                      ↓
                                            Product Context Added
                                                      ↓
                                            AI Generates Response
                                                      ↓
                                            Returns with Products
```

### 2. Intelligent Product Search

- Uses OpenSearch fuzzy matching for typo tolerance
- Searches across product names, descriptions, categories, and tags
- Filters for active products only
- Returns relevance-scored results

### 3. Context Management

- Maintains last 10 messages per session
- Stores user information across conversation
- Provides conversation context to AI

### 4. Scope Limiting

The AI is configured to:
- ✅ Only discuss cable-related products
- ✅ Check product availability before recommending
- ✅ Suggest alternatives when items are out of stock
- ❌ Politely decline requests for non-cable products
- ❌ Avoid spending tokens on irrelevant queries

## 🎨 UI Features

### Chat Interface
- Floating button in bottom-right corner
- Expandable/collapsible chat window
- Minimize functionality
- Message history with timestamps
- Typing indicators
- Product cards with stock status

### User Experience
- FAQ quick access for new users
- Clear conversation option
- Suggested products inline with responses
- Mobile-responsive design
- Accessible ARIA labels

## 🔒 Security Best Practices

1. **API Keys**: Never commit API keys to version control
2. **CORS**: Configure allowed origins in production
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Input Validation**: All user inputs are validated
5. **OpenSearch Security**: Use SSL and authentication

## 📈 Scaling Considerations

### Current Setup (Development)
- In-memory session storage
- Single FastAPI instance
- Local OpenSearch

### Production Recommendations
1. **Session Storage**: Replace in-memory with Redis
2. **Load Balancing**: Use multiple FastAPI instances
3. **OpenSearch Cluster**: Multi-node setup for reliability
4. **CDN**: Serve frontend through CDN
5. **Caching**: Implement response caching for common queries
6. **Monitoring**: Add logging and monitoring (e.g., Sentry)

## 🧪 Testing

### Test the Python API

```bash
# Health check
curl http://localhost:8000/api/health

# Test chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_123",
    "message": "I need a USB cable"
  }'

# Test FAQ
curl http://localhost:8000/api/faq
```

### Test OpenSearch Connection

```bash
python -c "
from opensearchpy import OpenSearch
client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    http_auth=('admin', 'Str0ngP@ssw0rd1245!'),
    use_ssl=True,
    verify_certs=False
)
print(client.info())
"
```

## 🐛 Troubleshooting

### OpenSearch Connection Issues
- Verify OpenSearch is running: `curl -k https://admin:Str0ngP@ssw0rd1245!@localhost:9200`
- Check credentials in `.env`
- Ensure SSL is properly configured

### OpenAI API Errors
- Verify API key is valid
- Check rate limits
- Ensure sufficient credits

### CORS Errors
- Update `allow_origins` in `main.py`
- Add your production domain

### Session Not Persisting
- Implement Redis for production
- Check session_id consistency

## 🔄 Customization

### Adding New Product Fields

1. Update OpenSearch mapping in `setup_opensearch.py`
2. Update search query in `main.py`
3. Update product display in `AIChatbot.tsx`

### Changing AI Behavior

Edit the system prompt in `get_system_prompt()` function in `main.py`:
```python
def get_system_prompt(products_context: str = "") -> str:
    base_prompt = """Your custom instructions here..."""
    return base_prompt
```

### Adding New FAQ Categories

Update the `/api/faq` endpoint in `main.py`.

## 📝 License

MIT License - feel free to use in your projects!

## 🤝 Contributing

Contributions welcome! Please follow clean code practices and add tests for new features.

## 📧 Support

For issues or questions, please open an issue on the repository.

---

**Built with ❤️ for cable enthusiasts**