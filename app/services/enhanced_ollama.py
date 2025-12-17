# app/services/enhanced_ollama.py
import requests
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from ..services.session import r as redis_client
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
# User Intent Analysis
# ------------------------------------------------------------------ #
class IntentAnalyzer:
    """Analyzes user messages to determine intent and completeness"""
    
    URGENCY_KEYWORDS = {
        "urgent": 3,
        "asap": 3,
        "quickly": 2,
        "fast": 2,
        "need now": 3,
        "immediately": 3,
        "hurry": 2,
    }
    
    FRUSTRATION_KEYWORDS = {
        "frustrated": 2,
        "annoyed": 2,
        "tired": 1,
        "enough": 2,
        "just show": 3,
        "stop asking": 3,
        "whatever": 2,
    }
    
    @staticmethod
    def analyze_mood(message: str, conversation_history: List[Dict]) -> Dict:
        """Detect user mood and patience level"""
        msg_lower = message.lower()
        
        urgency_score = sum(
            score for keyword, score in IntentAnalyzer.URGENCY_KEYWORDS.items()
            if keyword in msg_lower
        )
        
        frustration_score = sum(
            score for keyword, score in IntentAnalyzer.FRUSTRATION_KEYWORDS.items()
            if keyword in msg_lower
        )
        
        # Check conversation length
        turn_count = len([m for m in conversation_history if m["role"] == "user"])
        
        # Detect if user is giving short answers to questions
        if turn_count > 2:
            recent_msgs = [m["content"] for m in conversation_history[-3:] if m["role"] == "user"]
            avg_length = sum(len(m.split()) for m in recent_msgs) / len(recent_msgs)
            if avg_length < 3:
                frustration_score += 1
        
        return {
            "urgency": min(urgency_score, 3),
            "frustration": min(frustration_score, 3),
            "turn_count": turn_count,
            "is_impatient": urgency_score >= 2 or frustration_score >= 2 or turn_count > 3
        }
    
    @staticmethod
    def extract_specifications(message: str) -> Dict:
        """Extract product specifications from message"""
        msg_lower = message.lower()
        specs = {}
        
        # Length detection
        length_patterns = [
            (r"(\d+\.?\d*)\s*(m|meter|metre)", "length_m"),
            (r"(\d+\.?\d*)\s*(cm|centimeter)", "length_cm"),
            (r"(\d+\.?\d*)\s*(ft|foot|feet)", "length_ft"),
        ]
        import re
        for pattern, key in length_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                specs[key] = float(match.group(1))
        
        # Color detection
        colors = ["black", "white", "red", "blue", "green", "yellow", "orange", "purple", "gray", "silver", "gold"]
        for color in colors:
            if color in msg_lower:
                specs["color"] = color
                break
        
        # Cable type detection
        cable_types = ["24pin", "8pin", "6pin", "usb", "hdmi", "displayport", "ethernet", "sata", "molex"]
        for ctype in cable_types:
            if ctype in msg_lower.replace(" ", "").replace("-", ""):
                specs["cable_type"] = ctype
                break
        
        # Price range
        price_keywords = {
            "cheap": (0, 20),
            "budget": (0, 30),
            "affordable": (10, 40),
            "premium": (50, 200),
            "expensive": (80, 300),
        }
        for keyword, (min_p, max_p) in price_keywords.items():
            if keyword in msg_lower:
                specs["price_min"] = min_p
                specs["price_max"] = max_p
                break
        
        return specs


# ------------------------------------------------------------------ #
# Learning System
# ------------------------------------------------------------------ #
class LearningSystem:
    """Stores and retrieves learned patterns from user interactions"""
    
    @staticmethod
    def log_search_pattern(session_id: str, query: str, specs: Dict, selected_product_id: Optional[str] = None):
        """Log successful search patterns"""
        pattern = {
            "query": query,
            "specs": specs,
            "selected_product": selected_product_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in Redis with TTL of 90 days
        key = f"learning:search:{query.lower()[:50]}"
        redis_client.lpush(key, json.dumps(pattern))
        redis_client.ltrim(key, 0, 99)  # Keep last 100 patterns
        redis_client.expire(key, 7776000)  # 90 days
    
    @staticmethod
    def log_clarification_needed(query: str, missing_specs: List[str]):
        """Log when clarification was needed"""
        key = f"learning:clarify:{query.lower()[:50]}"
        data = {
            "missing_specs": missing_specs,
            "timestamp": datetime.now().isoformat()
        }
        redis_client.lpush(key, json.dumps(data))
        redis_client.ltrim(key, 0, 49)
        redis_client.expire(key, 7776000)
    
    @staticmethod
    def get_learned_patterns(query: str) -> List[Dict]:
        """Retrieve learned patterns for similar queries"""
        key = f"learning:search:{query.lower()[:50]}"
        patterns = redis_client.lrange(key, 0, 9)
        return [json.loads(p) for p in patterns]
    
    @staticmethod
    def get_common_specs(cable_type: str) -> Dict:
        """Get commonly requested specs for a cable type"""
        key = f"learning:specs:{cable_type}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        
        # Default common specs by type
        defaults = {
            "24pin": {"common_lengths": ["0.3m", "0.5m"], "common_colors": ["black", "white"]},
            "8pin": {"common_lengths": ["0.3m", "0.5m"], "common_colors": ["black"]},
            "usb": {"common_lengths": ["1m", "2m"], "common_colors": ["black", "white"]},
            "hdmi": {"common_lengths": ["1m", "2m", "3m"], "common_colors": ["black"]},
        }
        return defaults.get(cable_type, {})


# ------------------------------------------------------------------ #
# Smart Question Generator
# ------------------------------------------------------------------ #
class QuestionGenerator:
    """Generates contextual follow-up questions"""
    
    @staticmethod
    def should_ask_questions(mood: Dict, specs: Dict, cable_type: Optional[str]) -> bool:
        """Decide if we should ask clarifying questions"""
        # Don't ask if user is impatient
        if mood["is_impatient"]:
            return False
        
        # Don't ask if specs are reasonably complete
        if cable_type and len(specs) >= 2:
            return False
        
        # Don't ask after 2 rounds of questions
        if mood["turn_count"] > 2:
            return False
        
        return True
    
    @staticmethod
    def generate_questions(specs: Dict, cable_type: Optional[str], learned_patterns: List[Dict]) -> List[str]:
        """Generate smart follow-up questions based on context"""
        questions = []
        
        # Check what's missing
        missing = []
        if not specs.get("length_m") and not specs.get("length_cm") and not specs.get("length_ft"):
            missing.append("length")
        if not specs.get("color"):
            missing.append("color")
        if not specs.get("price_min"):
            missing.append("price")
        
        # Generate questions based on learned patterns
        if learned_patterns and cable_type:
            common_specs = LearningSystem.get_common_specs(cable_type)
            if "length" in missing and common_specs.get("common_lengths"):
                lengths = common_specs["common_lengths"]
                questions.append(f"What length do you need? (Most customers choose {' or '.join(lengths)})")
            if "color" in missing and common_specs.get("common_colors"):
                colors = common_specs["common_colors"]
                questions.append(f"Any color preference? We have {', '.join(colors)} available.")
        else:
            # Fallback questions
            if "length" in missing:
                questions.append("What length would you prefer?")
            if "color" in missing and cable_type:
                questions.append("Do you have a color preference?")
        
        return questions[:2]  # Max 2 questions at a time


# ------------------------------------------------------------------ #
# Enhanced Prompt Builder
# ------------------------------------------------------------------ #
def build_enhanced_prompt(
    messages: List[Dict],
    products: List[Dict],
    mood: Dict,
    specs: Dict,
    questions: List[str],
    promotions: List[Dict]
) -> str:
    """Build clear, strict prompt to prevent hallucinations"""
    
    prompt = ""
    
    # List products with exact titles
    if products:
        prompt += "Available products (use these exact titles):\n"
        for i, p in enumerate(products[:5], 1):
            promo_text = ""
            if any(pr.get("product_id") == p["id"] for pr in promotions):
                promo_item = next(pr for pr in promotions if pr.get("product_id") == p["id"])
                promo_text = f" (Sale: {promo_item.get('discount', 0)}% off)"
            prompt += f'{i}. "{p["title"]}" - ${p["price"]:.2f}{promo_text}\n'
        prompt += "\n"
    else:
        prompt += "No matching products found.\n\n"
    
    # Customer question
    prompt += f"Customer: {messages[-1]['content']}\n\n"
    prompt += "Respond in 1-2 sentences. Recommend products using their exact titles from the list above."
    
    return prompt


# ------------------------------------------------------------------ #
# Main Streaming Function
# ------------------------------------------------------------------ #
async def stream_enhanced_ollama_response(
    messages: List[Dict],
    products: List[Dict],
    session_id: str
):
    """Enhanced streaming with learning and context awareness"""
    
    current_message = messages[-1]["content"]
    
    # Analyze user intent and mood
    mood = IntentAnalyzer.analyze_mood(current_message, messages[:-1])
    specs = IntentAnalyzer.extract_specifications(current_message)
    cable_type = specs.get("cable_type")
    
    # Get learned patterns
    learned_patterns = LearningSystem.get_learned_patterns(current_message)
    
    # Generate questions if appropriate
    questions = []
    if QuestionGenerator.should_ask_questions(mood, specs, cable_type):
        questions = QuestionGenerator.generate_questions(specs, cable_type, learned_patterns)
    
    # Get promotions (you'll need to implement this in search.py)
    promotions = []  # TODO: get_active_promotions()
    
    # Build prompt
    prompt = build_enhanced_prompt(messages, products, mood, specs, questions, promotions)
    
    # Log for learning
    if questions:
        LearningSystem.log_clarification_needed(current_message, list(specs.keys()))
    
    # Stream response
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
                    "num_predict": 250,
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
    
    except Exception as e:
        print(f"Enhanced Ollama error: {e}")
        yield f"data: {json.dumps({'token': 'Sorry, I am having trouble right now.', 'done': True, 'error': True})}\n\n"


# ------------------------------------------------------------------ #
# Non-Streaming Function (Complete Response)
# ------------------------------------------------------------------ #
def get_enhanced_ollama_response(
    messages: List[Dict],
    products: List[Dict],
    session_id: str
) -> str:
    """Enhanced non-streaming response - returns complete answer at once"""
    
    current_message = messages[-1]["content"]
    
    # Analyze user intent and mood
    mood = IntentAnalyzer.analyze_mood(current_message, messages[:-1])
    specs = IntentAnalyzer.extract_specifications(current_message)
    cable_type = specs.get("cable_type")
    
    # Get learned patterns
    learned_patterns = LearningSystem.get_learned_patterns(current_message)
    
    # Generate questions if appropriate
    questions = []
    if QuestionGenerator.should_ask_questions(mood, specs, cable_type):
        questions = QuestionGenerator.generate_questions(specs, cable_type, learned_patterns)
    
    # Get promotions
    promotions = []  # TODO: get_active_promotions()
    
    # Build prompt
    prompt = build_enhanced_prompt(messages, products, mood, specs, questions, promotions)
    
    # Log for learning
    if questions:
        LearningSystem.log_clarification_needed(current_message, list(specs.keys()))
    
    # Get complete response from Ollama (non-streaming)
    try:
        # Build system message (rules)
        system_message = """You are a helpful cable store assistant.
- Recommend products from the list provided
- Use exact product titles from the list
- Keep responses brief (1-2 sentences)
- Do not invent product names"""
        
        # Build user message with product list
        user_message = prompt
        
        # Use chat API instead of generate for better instruction following
        response = requests.post(
            f"{OLLAMA_API_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Low but not too low - for natural responses
                    "top_p": 0.5,
                    "top_k": 10,
                    "num_predict": 150,
                    "repeat_penalty": 1.2,  # Moderate penalty to avoid garbled text
                },
            },
            timeout=config.ollama.timeout,
        )
        
        if response.status_code != 200:
            logger.error(f"Ollama error {response.status_code}: {response.text}")
            return "Sorry, I am having trouble right now. Please try again."
        
        data = response.json()
        assistant_response = data.get("message", {}).get("content", "")
        
        if not assistant_response:
            # Fallback: Simple template without AI
            if products:
                product_list = []
                for p in products[:3]:
                    promo = ""
                    if any(pr.get("product_id") == p["id"] for pr in promotions):
                        promo_item = next(pr for pr in promotions if pr.get("product_id") == p["id"])
                        promo = f" (Sale: {promo_item.get('discount', 0)}% off)"
                    product_list.append(f'{p["title"]} (${p["price"]:.2f}{promo})')
                
                return f"We have these options: {', '.join(product_list)}."
            else:
                return "I don't have exact matches for that. Could you provide more details?"
        
        # Check if response looks garbled or has hallucinations
        response_lower = assistant_response.lower()
        if any(indicator in response_lower for indicator in ['$35.08', '$29', '$5.78', 'package deal', '✅', '🔧']):
            # AI is hallucinating - use simple template instead
            if products:
                product_list = []
                for p in products[:3]:
                    promo = ""
                    if any(pr.get("product_id") == p["id"] for pr in promotions):
                        promo_item = next(pr for pr in promotions if pr.get("product_id") == p["id"])
                        promo = f" (Sale: {promo_item.get('discount', 0)}% off)"
                    product_list.append(f'{p["title"]} (${p["price"]:.2f}{promo})')
                
                return f"We have these options: {', '.join(product_list)}."
            else:
                return "I don't have exact matches for that. Could you provide more details?"
            
        return assistant_response.strip()
    
    except requests.exceptions.Timeout:
        logger.error("Ollama request timeout")
        return "Sorry, the request took too long. Please try again."
    
    except Exception as e:
        logger.error(f"Enhanced Ollama error: {e}")
        return "Sorry, I am having trouble right now. Please try again."