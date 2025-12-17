# AI Chatbot for Cable E-commerce Store

A comprehensive AI-powered chatbot system that helps customers find the right cables and accessories. Built with Python FastAPI backend featuring intelligent product search, context-aware conversations, and a robust knowledge management system.

## 🎯 Features

- **Intelligent Product Search**: Uses OpenSearch for fast, relevant product searches with fuzzy matching
- **Context-Aware Conversations**: Maintains conversation history with mood detection and adaptive responses
- **Knowledge Management**: Structured FAQ system, product catalog, and dynamic prompt management
- **Stock-Aware Recommendations**: Only recommends available products, mentions out-of-stock items
- **Scope-Limited Responses**: Focuses on cable-related products, politely declines off-topic queries
- **Learning System**: Tracks user interactions to improve recommendations over time
- **Admin Panel**: Real-time session monitoring and human intervention capabilities
- **Promotion Management**: Dynamic promotion system with automatic discount application

## 📁 Project Structure

```
ai-bot/
├── app/
│   ├── config.py                 # Centralized configuration management
│   ├── main.py                   # FastAPI application entry point
│   ├── models/                   # Pydantic models and schemas
│   │   ├── chat.py              # Chat request/response models
│   │   ├── product.py           # Product-related schemas
│   │   ├── session.py           # Session management models
│   │   └── admin.py             # Admin panel models
│   ├── routes/                   # API route handlers
│   │   ├── chat.py              # Chat endpoints
│   │   ├── system.py            # System endpoints (health, FAQ)
│   │   └── admin.py             # Admin panel endpoints
│   ├── services/                 # Business logic services
│   │   ├── search.py            # Basic product search
│   │   ├── enhanced_search.py   # Advanced search with learning
│   │   ├── ollama.py            # AI service integration
│   │   ├── enhanced_ollama.py   # Enhanced AI with intent analysis
│   │   └── session.py           # Session management
│   ├── knowledge/                # Knowledge base system
│   │   ├── base.py              # Abstract base class
│   │   ├── faq.py               # FAQ management
│   │   ├── prompts.py           # Prompt templates
│   │   └── product_catalog.py  # Product specifications
│   ├── utils/                    # Utility functions
│   │   ├── exceptions.py        # Custom exceptions
│   │   ├── logging.py           # Logging configuration
│   │   └── validators.py        # Input validation
│   └── data/                     # Static knowledge files
│       ├── product_specs.yaml   # Cable specifications
│       ├── faqs.yaml            # FAQ database
│       └── prompts.yaml         # AI prompt templates
├── .env                          # Environment variables (create from .env.example)
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
└── run.py                        # Application runner

```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenSearch running on `https://localhost:9200`
- Redis running on `localhost:6379`
- Ollama with phi3:3.8b model (or configure different model)

### Step 1: Clone and Setup

```bash
# Clone the repository
cd ai-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and configure:
# - OpenSearch credentials
# - Redis URL
# - Ollama settings
# - Security secrets (IMPORTANT: change in production!)
```

### Step 3: Start the Application

```bash
# Run the FastAPI server
python run.py

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## 🔧 Configuration

The application uses a centralized configuration system (`app/config.py`) with environment variable support:

### Key Configuration Sections

- **OpenSearch**: Search engine connection and index settings
- **Redis**: Session storage and caching configuration
- **Ollama**: AI model settings and parameters
- **Security**: API keys, session secrets, JWT configuration
- **Rate Limiting**: Request throttling settings
- **CORS**: Allowed origins for cross-origin requests

See `.env.example` for all available options.

## 📊 API Endpoints

### Chat Endpoints

**POST /api/session**

- Initialize a new chat session
- Returns session ID and signature cookies

**POST /api/chat**

- Send a message and get AI response
- Requires valid session
- Returns streaming response with products

**POST /api/product-click**

- Track product interactions for learning
- Improves future recommendations

**POST /api/human-request**

- Request human assistance
- Rate limited to prevent abuse

### System Endpoints

**GET /api/health**

- Health check with service status
- Returns Ollama, Redis, and OpenSearch status

**GET /api/faq**

- Get frequently asked questions
- Organized by category

**DELETE /api/session/{session_id}**

- Clear chat session history

### Admin Endpoints

**GET /api/admin/sessions**

- List all active sessions
- Requires admin API key

**GET /api/admin/session/{session_id}**

- Get full chat history for a session

**GET /api/admin/session/{session_id}/stream**

- Real-time session monitoring (SSE)

**POST /api/admin/session/{session_id}/send**

- Send message to user as admin

## 💡 Knowledge Management System

### FAQ System

The FAQ system (`app/knowledge/faq.py`) provides:

- Intelligent keyword matching
- Category-based organization
- Priority-based ranking
- Quick responses for common scenarios

FAQs are stored in `app/data/faqs.yaml` and can be easily updated.

### Prompt Management

The prompt manager (`app/knowledge/prompts.py`) handles:

- Context-aware prompt selection
- Mood-based variations (patient, impatient, confused)
- Response templates
- Error messages

Prompts are defined in `app/data/prompts.yaml`.

### Product Catalog

The product catalog (`app/knowledge/product_catalog.py`) manages:

- Cable type specifications
- Common lengths and colors
- Connector information
- Price range recommendations
- Product combinations

Catalog data is in `app/data/product_specs.yaml`.

## 🧪 Testing

```bash
# Install development dependencies
pip install pytest pytest-cov pytest-asyncio

# Run tests
pytest tests/ -v

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_knowledge.py -v
```

## 🔒 Security Best Practices

1. **Environment Variables**: Never commit `.env` to version control
2. **API Keys**: Change all default secrets in production
3. **CORS**: Configure allowed origins for your domain
4. **Rate Limiting**: Adjust limits based on your traffic
5. **Session Security**: Use secure cookies in production (HTTPS)
6. **Admin Access**: Implement proper JWT authentication for admin panel

## 📈 Scaling Considerations

### Current Setup (Development)

- In-memory session storage via Redis
- Single FastAPI instance
- Local OpenSearch and Redis

### Production Recommendations

1. **Load Balancing**: Deploy multiple FastAPI instances behind a load balancer
2. **Redis Cluster**: Use Redis cluster for high availability
3. **OpenSearch Cluster**: Multi-node setup for reliability and performance
4. **CDN**: Serve static assets through CDN
5. **Caching**: Implement response caching for common queries
6. **Monitoring**: Add logging aggregation (e.g., ELK stack) and monitoring (e.g., Prometheus)
7. **Database**: Consider PostgreSQL for persistent data storage

## 🐛 Troubleshooting

### OpenSearch Connection Issues

```bash
# Verify OpenSearch is running
curl -k https://admin:Str0ngP@ssw0rd1245!@localhost:9200

# Check credentials in .env
# Ensure SSL settings match your OpenSearch configuration
```

### Ollama API Errors

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify model is installed
ollama list

# Pull model if needed
ollama pull phi3:3.8b
```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping

# Should return: PONG
```

## 🔄 Customization

### Adding New Cable Types

1. Edit `app/data/product_specs.yaml`
2. Add new cable type with specifications
3. Restart the application

### Modifying AI Behavior

1. Edit prompts in `app/data/prompts.yaml`
2. Adjust system prompts for different scenarios
3. Changes take effect immediately (no restart needed)

### Adding New FAQs

1. Edit `app/data/faqs.yaml`
2. Add questions to appropriate category
3. Include keywords for better matching

## 📝 License

MIT License - feel free to use in your projects!

## 🤝 Contributing

Contributions welcome! Please:

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Create detailed pull requests

## 📧 Support

For issues or questions, please open an issue on the repository.

---

**Built with ❤️ for cable enthusiasts**
