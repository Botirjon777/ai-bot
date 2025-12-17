"""
Base class for knowledge sources.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
import yaml
import json


class KnowledgeBase(ABC):
    """Abstract base class for all knowledge sources."""
    
    def __init__(self, data_file: Optional[Path] = None):
        """
        Initialize knowledge base.
        
        Args:
            data_file: Path to data file (YAML or JSON)
        """
        self.data_file = data_file
        self._data: Dict[str, Any] = {}
        self._cache: Dict[str, Any] = {}
        
        if data_file and data_file.exists():
            self.load()
    
    def load(self) -> None:
        """Load knowledge from data file."""
        if not self.data_file or not self.data_file.exists():
            return
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            if self.data_file.suffix in ['.yaml', '.yml']:
                self._data = yaml.safe_load(f) or {}
            elif self.data_file.suffix == '.json':
                self._data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {self.data_file.suffix}")
    
    def reload(self) -> None:
        """Reload knowledge from file and clear cache."""
        self._cache.clear()
        self.load()
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> Any:
        """
        Search knowledge base.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters
        
        Returns:
            Search results
        """
        pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from knowledge base.
        
        Args:
            key: Key to retrieve
            default: Default value if key not found
        
        Returns:
            Value or default
        """
        return self._data.get(key, default)
    
    def set_cache(self, key: str, value: Any) -> None:
        """Set cache value."""
        self._cache[key] = value
    
    def get_cache(self, key: str, default: Any = None) -> Any:
        """Get cache value."""
        return self._cache.get(key, default)
    
    def clear_cache(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
