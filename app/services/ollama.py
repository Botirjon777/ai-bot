import requests
import json
from typing import List, Dict

from ..config import get_config
from ..utils.logging import get_logger

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
config = get_config()
logger = get_logger(__name__)

OLLAMA_API_URL = config.ollama.api_url
OLLAMA_MODEL = config.ollama.model

# ------------------------------------------------------------------ #
# Prompt builder
# ------------------------------------------------------------------ #
def build_prompt(messages: List[Dict], products: List[Dict]) -> str:
    system_prompt = """You are a helpful AI assistant for a cable and PC accessories e-commerce store.
Your role is to help customers find the right cables, custom cables, and cable-related products.

IMPORTANT RULES:
1. ONLY discuss products related to cables (PC cables, custom cables, USB cables, HDMI cables, power cables, adapters, etc.)
2. If users ask about products NOT related to cables (like GPUs, graphics cards, games, consoles, furniture, clothing), politely inform them: "I apologize, but we only sell cables and cable-related accessories. We don't carry that item."
3. ALWAYS check product availability before recommending
4. If a product is out of stock, mention it clearly and suggest alternatives
5. Be concise and helpful (2-3 sentences maximum)
6. Remember the conversation context
7. Ask clarifying questions if needed (cable type, length, connector type, etc.)

PRODUCT KNOWLEDGE:
- We sell: PC cables, custom cables, USB cables, HDMI cables, power cables (24-pin, 8-pin, etc.), DisplayPort cables, Ethernet cables, adapters, cable extensions, cable sleeves, and cable management accessories
- We DO NOT sell: Gaming consoles, games, computers, monitors, keyboards, mice, GPUs, graphics cards, or any non-cable products"""

    if products:
        system_prompt += "\n\nCURRENT AVAILABLE PRODUCTS:\n"
        for p in products:
            system_prompt += f"- {p['title']} (${p['price']}) by {p['vendor']}\n"

    conversation = system_prompt + "\n\n"
    for msg in messages[-10:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        conversation += f"{role}: {msg['content']}\n"
    conversation += "Assistant:"
    return conversation


# ------------------------------------------------------------------ #
# Streaming generator
# ------------------------------------------------------------------ #
async def stream_ollama_response(messages: List[Dict], products: List[Dict]):
    prompt = build_prompt(messages, products)

    try:
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": 200,
                },
            },
            stream=True,
            timeout=60,
        )

        if response.status_code != 200:
            raise ValueError(f"Ollama error {response.status_code}")

        for line in response.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
                token = data.get("response", "")
                done = data.get("done", False)

                if token:
                    yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
                if done:
                    yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
                    break
            except json.JSONDecodeError:
                continue

    except requests.exceptions.Timeout:
        yield f"data: {json.dumps({'token': 'Sorry, the response is taking too long. Please try again.', 'done': True, 'error': True})}\n\n"
    except Exception as e:
        print(f"Ollama error: {e}")
        yield f"data: {json.dumps({'token': 'Sorry, I am having trouble right now.', 'done': True, 'error': True})}\n\n"