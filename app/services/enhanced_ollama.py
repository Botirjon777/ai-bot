# app/services/enhanced_ollama.py
import requests
import json
from typing import List, Dict, Optional, Tuple
import os
from datetime import datetime
from ..services.session import r as redis_client

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:3.8b")

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
    """Build context-aware prompt with learning"""
    
    system_prompt = """You are an intelligent AI assistant for a cable e-commerce store.

PERSONALITY:
- Helpful and efficient
- Adapts to customer mood (if they seem impatient, be direct)
- Professional but friendly

CORE RULES:
1. ONLY discuss cable-related products
2. If customer seems impatient/frustrated, show products immediately without extra questions
3. If specifications are unclear, ask 1-2 clarifying questions (unless customer is impatient)
4. Always mention promotions when available
5. Be concise (2-4 sentences max)

MOOD INDICATORS:
"""
    
    if mood["is_impatient"]:
        system_prompt += "- Customer seems IMPATIENT - show products directly, minimal questions\n"
    elif mood["turn_count"] > 2:
        system_prompt += "- Long conversation - prioritize showing results\n"
    else:
        system_prompt += "- Customer is engaged - can ask clarifying questions if needed\n"
    
    if specs:
        system_prompt += f"\nDETECTED SPECIFICATIONS: {json.dumps(specs)}\n"
    
    if questions and not mood["is_impatient"]:
        system_prompt += f"\nSUGGESTED QUESTIONS: {json.dumps(questions)}\n"
        system_prompt += "You may ask these questions if specifications are unclear.\n"
    
    if products:
        system_prompt += "\n\nAVAILABLE PRODUCTS:\n"
        for i, p in enumerate(products[:5], 1):
            promo = ""
            if any(pr["product_id"] == p["id"] for pr in promotions):
                promo_item = next(pr for pr in promotions if pr["product_id"] == p["id"])
                promo = f" 🔥 ON SALE: {promo_item['discount']}% OFF!"
            system_prompt += f"{i}. {p['title']} - ${p['price']} by {p['vendor']}{promo}\n"
    
    if promotions and not products:
        system_prompt += "\n\nCURRENT PROMOTIONS:\n"
        for promo in promotions[:3]:
            system_prompt += f"- {promo['title']}: {promo['discount']}% off\n"
    
    # Add conversation history
    conversation = system_prompt + "\n\nCONVERSATION:\n"
    for msg in messages[-8:]:
        role = "Customer" if msg["role"] == "user" else "Assistant"
        conversation += f"{role}: {msg['content']}\n"
    
    conversation += "Assistant:"
    return conversation


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