# app/services/enhanced_ollama.py
import requests
import json
from typing import List, Dict
from datetime import datetime

from ..config import get_config
from ..utils.logging import get_logger

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
config = get_config()
logger = get_logger(__name__)

# ------------------------------------------------------------------ #
# Intent Analysis
# ------------------------------------------------------------------ #
class IntentAnalyzer:
    """Extract user intent and specifications from queries"""
    
    @staticmethod
    def extract_specifications(query: str) -> Dict:
        """Extract cable specifications from user query"""
        specs = {}
        query_lower = query.lower()
        
        # Cable type detection
        cable_types = {
            "usb": "usb",
            "hdmi": "hdmi",
            "displayport": "displayport",
            "ethernet": "ethernet",
            "power": "power",
            "sata": "sata",
            "pcie": "pcie",
            "24-pin": "24-pin atx",
            "24 pin": "24-pin atx",
            "8-pin": "8-pin eps",
            "8 pin": "8-pin eps",
        }
        
        for keyword, cable_type in cable_types.items():
            if keyword in query_lower:
                specs["cable_type"] = cable_type
                break
        
        # Length extraction (simple pattern matching)
        import re
        
        # Meters
        meter_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:m|meter|meters)', query_lower)
        if meter_match:
            specs["length_m"] = float(meter_match.group(1))
        
        # Feet
        feet_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ft|feet|foot)', query_lower)
        if feet_match:
            specs["length_ft"] = float(feet_match.group(1))
        
        # Inches
        inch_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:in|inch|inches|")', query_lower)
        if inch_match:
            specs["length_cm"] = float(inch_match.group(1)) * 2.54
        
        # Color detection
        colors = ["black", "white", "red", "blue", "green", "yellow", "orange", "purple", "gray", "silver"]
        for color in colors:
            if color in query_lower:
                specs["color"] = color
                break
        
        return specs


# ------------------------------------------------------------------ #
# Learning System (DISABLED - requires Redis)
# ------------------------------------------------------------------ #
class LearningSystem:
    """Track and learn from user interactions (DISABLED without Redis)"""
    
    @staticmethod
    def log_search_pattern(session_id: str, query: str, specs: Dict, selected_product: str = None):
        """Log search patterns for learning (disabled without Redis)"""
        pass
    
    @staticmethod
    def log_user_mood(session_id: str, mood: str):
        """Track user mood/frustration level (disabled without Redis)"""
        pass
    
    @staticmethod
    def get_common_patterns(cable_type: str = None) -> List[Dict]:
        """Get common search patterns (disabled without Redis)"""
        return []
    
    @staticmethod
    def get_user_mood(session_id: str) -> str:
        """Get user's current mood (disabled without Redis)"""
        return "neutral"


# ------------------------------------------------------------------ #
# Enhanced Ollama Response
# ------------------------------------------------------------------ #
def get_enhanced_ollama_response(
    messages: List[Dict],
    products: List[Dict],
    session_id: str
) -> str:
    """
    Get AI response with product context (optimized for speed)
    """
    
    # Build concise system prompt with product context
    system_prompt = """You are a helpful AI assistant for a cable store.

Rules:
- Help customers find cables and accessories
- Keep responses under 2-3 sentences
- Only recommend products from our catalog
- We do NOT sell GPUs or computer components

Be friendly, concise, and helpful."""

    if products:
        product_list = "\n".join([
            f"- {p['title']} (${p['price']:.2f})"
            for p in products[:5]
        ])
        system_prompt += f"\n\nAvailable products:\n{product_list}"
    
    # Prepare messages for Ollama
    ollama_messages = [{"role": "system", "content": system_prompt}]
    ollama_messages.extend(messages)
    
    # Call Ollama API with optimized parameters
    try:
        import time
        start_time = time.time()
        
        response = requests.post(
            f"{config.ollama.api_url}/api/chat",
            json={
                "model": config.ollama.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": config.ollama.temperature,
                    "top_p": config.ollama.top_p,
                    "top_k": config.ollama.top_k,
                    "num_predict": config.ollama.max_tokens,
                    "num_ctx": config.ollama.num_ctx,
                    "repeat_penalty": config.ollama.repeat_penalty,
                    "num_gpu": 1,  # Use GPU if available
                }
            },
            timeout=config.ollama.timeout
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result["message"]["content"]
            logger.info(f"Ollama response time: {elapsed:.2f}s for {len(ai_response)} chars")
            return ai_response
        else:
            logger.error(f"Ollama API error: {response.status_code}")
            return "I'm having trouble processing your request. Please try again."
            
    except requests.Timeout:
        logger.error(f"Ollama request timeout after {config.ollama.timeout}s")
        return "I'm taking too long to respond. Please try a simpler question."
    except Exception as e:
        logger.error(f"Ollama request failed: {e}")
        return "I'm having trouble connecting to my AI service. Please try again in a moment."