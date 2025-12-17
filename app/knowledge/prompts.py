"""
Prompt management system for AI responses.
"""
from typing import Dict, Optional, List
from pathlib import Path
from .base import KnowledgeBase
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PromptManager(KnowledgeBase):
    """Manages AI prompts with context-aware selection."""
    
    def __init__(self, data_file: Optional[Path] = None):
        """Initialize prompt manager."""
        if data_file is None:
            data_file = Path(__file__).parent.parent / "data" / "prompts.yaml"
        super().__init__(data_file)
    
    def search(self, query: str, **kwargs) -> str:
        """
        Search for appropriate prompt.
        
        Args:
            query: Query type or scenario
            **kwargs: Additional context
        
        Returns:
            Prompt text
        """
        return self.get_system_prompt(query, **kwargs)
    
    def get_system_prompt(
        self,
        scenario: str = "default",
        mood: Optional[Dict] = None,
        **context
    ) -> str:
        """
        Get system prompt for a scenario.
        
        Args:
            scenario: Scenario type (default, impatient_user, technical_query, etc.)
            mood: User mood information
            **context: Additional context to inject
        
        Returns:
            System prompt text
        """
        prompts = self._data.get("system_prompts", {})
        
        # Determine scenario based on mood if provided
        if mood and scenario == "default":
            if mood.get("is_impatient"):
                scenario = "impatient_user"
            elif mood.get("turn_count", 0) == 0:
                scenario = "first_interaction"
        
        prompt = prompts.get(scenario, prompts.get("default", ""))
        
        # Inject context if provided
        if context:
            try:
                prompt = prompt.format(**context)
            except KeyError as e:
                logger.warning(f"Missing context key in prompt: {e}")
        
        return prompt
    
    def get_response_template(self, template_name: str) -> str:
        """
        Get a response template.
        
        Args:
            template_name: Template name
        
        Returns:
            Template text
        """
        templates = self._data.get("response_templates", {})
        return templates.get(template_name, "")
    
    def format_response(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """
        Format a response using a template.
        
        Args:
            template_name: Template name
            **kwargs: Template variables
        
        Returns:
            Formatted response
        """
        template = self.get_response_template(template_name)
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return template
    
    def get_mood_variation(
        self,
        mood_type: str,
        element: str
    ) -> str:
        """
        Get mood-based text variation.
        
        Args:
            mood_type: Mood type (patient, impatient, confused)
            element: Element type (greeting, transition, question_intro)
        
        Returns:
            Text variation
        """
        variations = self._data.get("mood_variations", {})
        mood_data = variations.get(mood_type, {})
        return mood_data.get(element, "")
    
    def get_error_message(self, error_type: str) -> str:
        """
        Get user-friendly error message.
        
        Args:
            error_type: Error type key
        
        Returns:
            Error message
        """
        errors = self._data.get("error_messages", {})
        return errors.get(error_type, "An error occurred. Please try again.")
    
    def get_closing_statement(self) -> str:
        """
        Get a random closing statement.
        
        Returns:
            Closing statement
        """
        import random
        
        statements = self._data.get("closing_statements", [])
        return random.choice(statements) if statements else ""
    
    def build_product_context(
        self,
        products: List[Dict],
        promotions: Optional[List[Dict]] = None
    ) -> str:
        """
        Build product context for AI prompt.
        
        Args:
            products: List of products
            promotions: Optional list of promotions
        
        Returns:
            Formatted product context
        """
        if not products:
            return ""
        
        context = "\\n\\nAVAILABLE PRODUCTS:\\n"
        
        for i, product in enumerate(products[:5], 1):
            promo_text = ""
            
            if promotions:
                for promo in promotions:
                    if promo.get("product_id") == product.get("id"):
                        promo_text = f" 🔥 ON SALE: {promo['discount']}% OFF!"
                        break
            
            context += (
                f"{i}. {product.get('title', 'Unknown')} - "
                f"${product.get('price', 0)} by {product.get('vendor', 'Unknown')}"
                f"{promo_text}\\n"
            )
        
        return context
    
    def build_conversation_history(
        self,
        messages: List[Dict],
        max_messages: int = 8
    ) -> str:
        """
        Build conversation history for context.
        
        Args:
            messages: List of message dictionaries
            max_messages: Maximum messages to include
        
        Returns:
            Formatted conversation history
        """
        history = "\\n\\nCONVERSATION:\\n"
        
        for msg in messages[-max_messages:]:
            role = "Customer" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            history += f"{role}: {content}\\n"
        
        return history
