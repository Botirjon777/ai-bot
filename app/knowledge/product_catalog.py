"""
Product catalog and specifications management.
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
from .base import KnowledgeBase
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ProductCatalog(KnowledgeBase):
    """Manages product catalog and specifications."""
    
    def __init__(self, data_file: Optional[Path] = None):
        """Initialize product catalog."""
        if data_file is None:
            data_file = Path(__file__).parent.parent / "data" / "product_specs.yaml"
        super().__init__(data_file)
    
    def search(self, query: str, **kwargs) -> Dict:
        """
        Search product catalog.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters
        
        Returns:
            Search results
        """
        cable_type = self.identify_cable_type(query)
        
        if cable_type:
            return self.get_cable_info(cable_type)
        
        return {}
    
    def identify_cable_type(self, query: str) -> Optional[str]:
        """
        Identify cable type from query.
        
        Args:
            query: User query
        
        Returns:
            Cable type key or None
        """
        query_lower = query.lower()
        cable_types = self._data.get("cable_types", {})
        
        # Direct match
        for cable_type in cable_types.keys():
            if cable_type in query_lower:
                return cable_type
        
        # Check variants
        for cable_type, info in cable_types.items():
            variants = info.get("variants", [])
            for variant in variants:
                if variant.replace("-", "").replace(" ", "") in query_lower.replace("-", "").replace(" ", ""):
                    return cable_type
        
        # Check use cases
        for cable_type, info in cable_types.items():
            use_cases = info.get("typical_use_cases", [])
            for use_case in use_cases:
                if use_case.lower() in query_lower:
                    return cable_type
        
        return None
    
    def get_cable_info(self, cable_type: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a cable type.
        
        Args:
            cable_type: Cable type key
        
        Returns:
            Cable information dictionary
        """
        cable_types = self._data.get("cable_types", {})
        return cable_types.get(cable_type, {})
    
    def get_common_lengths(self, cable_type: str) -> List[str]:
        """
        Get common lengths for a cable type.
        
        Args:
            cable_type: Cable type key
        
        Returns:
            List of common lengths
        """
        info = self.get_cable_info(cable_type)
        return info.get("common_lengths", [])
    
    def get_common_colors(self, cable_type: str) -> List[str]:
        """
        Get common colors for a cable type.
        
        Args:
            cable_type: Cable type key
        
        Returns:
            List of common colors
        """
        info = self.get_cable_info(cable_type)
        return info.get("common_colors", [])
    
    def get_variants(self, cable_type: str) -> List[str]:
        """
        Get variants for a cable type.
        
        Args:
            cable_type: Cable type key
        
        Returns:
            List of variants
        """
        info = self.get_cable_info(cable_type)
        return info.get("variants", [])
    
    def get_connector_info(self, connector_type: str) -> Optional[Dict]:
        """
        Get information about a connector type.
        
        Args:
            connector_type: Connector type
        
        Returns:
            Connector information or None
        """
        connectors = self._data.get("connectors", {})
        
        for category, connector_list in connectors.items():
            for connector in connector_list:
                if connector.get("type", "").lower() == connector_type.lower():
                    return connector
        
        return None
    
    def get_price_range_info(self, range_name: str) -> Optional[Dict]:
        """
        Get price range information.
        
        Args:
            range_name: Price range name (budget, standard, premium, custom)
        
        Returns:
            Price range info or None
        """
        price_ranges = self._data.get("price_ranges", {})
        return price_ranges.get(range_name)
    
    def suggest_price_range(self, keywords: List[str]) -> Optional[str]:
        """
        Suggest price range based on keywords.
        
        Args:
            keywords: List of keywords from query
        
        Returns:
            Price range name or None
        """
        keywords_lower = [k.lower() for k in keywords]
        
        price_keywords = {
            "budget": ["cheap", "budget", "affordable", "inexpensive"],
            "standard": ["standard", "regular", "normal"],
            "premium": ["premium", "high-quality", "best", "top"],
            "custom": ["custom", "bespoke", "personalized"]
        }
        
        for range_name, range_keywords in price_keywords.items():
            if any(kw in keywords_lower for kw in range_keywords):
                return range_name
        
        return None
    
    def get_recommended_combinations(self, query: str) -> List[str]:
        """
        Get recommended product combinations based on query.
        
        Args:
            query: User query
        
        Returns:
            List of recommended products
        """
        query_lower = query.lower()
        combinations = self._data.get("common_combinations", [])
        
        for combo in combinations:
            pattern = combo.get("query_pattern", "")
            if pattern.lower() in query_lower:
                return combo.get("recommended_products", [])
        
        return []
    
    def get_all_cable_types(self) -> List[str]:
        """
        Get list of all cable types.
        
        Returns:
            List of cable type keys
        """
        cable_types = self._data.get("cable_types", {})
        return list(cable_types.keys())
    
    def get_cable_type_name(self, cable_type: str) -> str:
        """
        Get display name for cable type.
        
        Args:
            cable_type: Cable type key
        
        Returns:
            Display name
        """
        info = self.get_cable_info(cable_type)
        return info.get("name", cable_type.upper())
