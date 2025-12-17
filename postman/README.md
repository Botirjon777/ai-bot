# Postman Testing for AI Cable Store Bot

This directory contains a complete Postman collection and testing documentation for the AI Cable Store Bot API.

## 📁 Files

- **`AI-Bot-API.postman_collection.json`** - Complete Postman collection with all API endpoints
- **`ai-bot.postman_environment.json`** - Environment variables for different environments
- **`POSTMAN_TESTING_GUIDE.md`** - Comprehensive testing guide with setup instructions
- **`TEST_SCENARIOS.md`** - Detailed test scenarios and workflows

## 🚀 Quick Start

1. **Import Collection**

   - Open Postman
   - Click **Import** → Select `AI-Bot-API.postman_collection.json`
   - Click **Import** → Select `ai-bot.postman_environment.json`

2. **Configure Environment**

   - Select "AI Bot - Development" environment (top right)
   - Edit `admin_api_key` to match your `.env` file
   - Verify `base_url` is `http://localhost:8000`

3. **Start Testing**
   - Run "Health Check" to verify services
   - Run "Initialize Session" to create a session
   - Run "Send Chat Message" to test chat functionality

## 📚 Documentation

- **[POSTMAN_TESTING_GUIDE.md](POSTMAN_TESTING_GUIDE.md)** - Complete setup and usage guide
- **[TEST_SCENARIOS.md](TEST_SCENARIOS.md)** - 16 comprehensive test scenarios

## 🔑 API Endpoints

### Chat Endpoints (4)

- `GET /api/session` - Initialize session
- `POST /api/chat` - Send chat message
- `POST /api/product-click` - Track product click
- `POST /api/human-request` - Request human assistant

### System Endpoints (3)

- `GET /api/health` - Health check
- `GET /api/faq` - Get FAQs
- `DELETE /api/session/{id}` - Clear session

### Admin Endpoints (4)

- `GET /api/admin/sessions` - List active sessions
- `GET /api/admin/session/{id}` - Get session history
- `GET /api/admin/session/{id}/stream` - Stream session updates
- `POST /api/admin/session/{id}/send` - Send admin message

## ⚙️ Environment Variables

| Variable           | Description        | Default                           |
| ------------------ | ------------------ | --------------------------------- |
| `base_url`         | API base URL       | `http://localhost:8000`           |
| `admin_api_key`    | Admin API key      | `admin-secret-key-change-in-prod` |
| `session_id`       | Current session ID | Auto-set                          |
| `admin_session_id` | Admin test session | Auto-set                          |

## 🧪 Test Scenarios

The collection includes 16 comprehensive test scenarios:

**User Flows:**

- New user chat session
- Returning user session
- Human assistant request
- GPU filter test

**Admin Workflows:**

- Session monitoring
- Live intervention

**Error Handling:**

- Invalid sessions
- Rate limiting
- Input validation
- Admin authentication

**Edge Cases:**

- Concurrent sessions
- Special characters
- Long conversation history
- Session cleanup

**Performance:**

- Response time benchmarks
- Streaming performance

## 📊 Running Tests

### In Postman UI

1. Click collection → **Run**
2. Select requests to run
3. Set iterations and delays
4. Click **Run**

### Using Newman (CLI)

```bash
# Install Newman
npm install -g newman

# Run tests
newman run AI-Bot-API.postman_collection.json \
  -e ai-bot.postman_environment.json

# Run with iterations
newman run AI-Bot-API.postman_collection.json \
  -e ai-bot.postman_environment.json \
  -n 10 --delay-request 500
```

## 🔧 Prerequisites

Before testing, ensure:

- ✅ Redis is running
- ✅ OpenSearch is running
- ✅ Ollama is running with `phi3:3.8b` model
- ✅ AI Bot server is running (`python run.py`)

## 📖 Additional Resources

- **Project README:** `../readme.md`
- **Environment Setup:** `../.env.example`
- **API Routes:** `../app/routes/`
- **Request Models:** `../app/models/chat.py`

## 🐛 Troubleshooting

Common issues and solutions:

**"Session not found"**

- Run "Initialize Session" first
- Check session cookies are set

**"Invalid admin key" (403)**

- Verify `admin_api_key` matches `.env` file
- Check `x-admin-key` header is set

**"Too many requests" (429)**

- Wait for rate limit window to reset
- Chat: 5 req/min, Human: 2 req/5min

**Service "disconnected" in health check**

- Verify Redis: `redis-server`
- Verify OpenSearch: `docker start opensearch-node1`
- Verify Ollama: `ollama serve`

## 📝 Notes

- Session cookies are automatically managed by Postman
- Admin endpoints require `x-admin-key` header
- Streaming responses (SSE) may not display fully in Postman UI
- Use `curl` or browser for better SSE testing experience

---

For detailed documentation, see [POSTMAN_TESTING_GUIDE.md](POSTMAN_TESTING_GUIDE.md)
