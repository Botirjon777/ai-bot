"""
FAQ (Frequently Asked Questions) system.
"""
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from .base import KnowledgeBase
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FAQSystem(KnowledgeBase):
    """Manages FAQs with intelligent search and matching."""
    
    def __init__(self, data_file: Optional[Path] = None):
        """Initialize FAQ system."""
        if data_file is None:
            data_file = Path(__file__).parent.parent / "data" / "faqs.yaml"
        super().__init__(data_file)
    
    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search FAQs by query and optional category.
        
        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum number of results
        
        Returns:
            List of matching FAQs with scores
        """
        query_lower = query.lower()
        results = []
        
        categories = self._data.get("categories", [])
        
        for cat in categories:
            # Skip if category filter doesn't match
            if category and cat.get("name") != category:
                continue
            
            for faq in cat.get("questions", []):
                score = self._calculate_match_score(query_lower, faq)
                
                if score > 0:
                    results.append({
                        "category": cat.get("name"),
                        "icon": cat.get("icon", ""),
                        "question": faq.get("question"),
                        "answer": faq.get("answer"),
                        "priority": faq.get("priority", "medium"),
                        "score": score
                    })
        
        # Sort by score (descending) and priority
        priority_weight = {"high": 3, "medium": 2, "low": 1}
        results.sort(
            key=lambda x: (x["score"], priority_weight.get(x["priority"], 0)),
            reverse=True
        )
        
        return results[:limit]
    
    def _calculate_match_score(self, query: str, faq: Dict) -> float:
        """
        Calculate match score for a FAQ.
        
        Args:
            query: Search query (lowercase)
            faq: FAQ dictionary
        
        Returns:
            Match score (0.0 to 1.0)
        """
        score = 0.0
        
        # Check question match
        question = faq.get("question", "").lower()
        if query in question:
            score += 0.8
        elif any(word in question for word in query.split()):
            score += 0.4
        
        # Check keywords match
        keywords = faq.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in query:
                score += 0.6
                break
        
        # Check answer match (lower weight)
        answer = faq.get("answer", "").lower()
        if query in answer:
            score += 0.2
        
        return min(score, 1.0)
    
    def get_by_category(self, category: str) -> List[Dict]:
        """
        Get all FAQs in a category.
        
        Args:
            category: Category name
        
        Returns:
            List of FAQs
        """
        categories = self._data.get("categories", [])
        
        for cat in categories:
            if cat.get("name") == category:
                return [
                    {
                        "question": faq.get("question"),
                        "answer": faq.get("answer"),
                        "priority": faq.get("priority", "medium")
                    }
                    for faq in cat.get("questions", [])
                ]
        
        return []
    
    def get_all_categories(self) -> List[Dict]:
        """
        Get all FAQ categories.
        
        Returns:
            List of category information
        """
        categories = self._data.get("categories", [])
        return [
            {
                "name": cat.get("name"),
                "icon": cat.get("icon", ""),
                "count": len(cat.get("questions", []))
            }
            for cat in categories
        ]
    
    def get_quick_response(self, scenario: str) -> Optional[str]:
        """
        Get a quick response for common scenarios.
        
        Args:
            scenario: Scenario key (greeting, unclear_request, etc.)
        
        Returns:
            Quick response text or None
        """
        import random
        
        quick_responses = self._data.get("quick_responses", {})
        responses = quick_responses.get(scenario, [])
        
        if responses:
            return random.choice(responses) if isinstance(responses, list) else responses
        
        return None
    
    def suggest_faq(self, query: str) -> Optional[Dict]:
        """
        Suggest a single most relevant FAQ.
        
        Args:
            query: User query
        
        Returns:
            Most relevant FAQ or None
        """
        results = self.search(query, limit=1)
        
        if results and results[0]["score"] > 0.5:
            return results[0]
        
        return None
