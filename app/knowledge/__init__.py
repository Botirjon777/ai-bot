"""
Knowledge base system for the AI Bot application.
"""
from .base import KnowledgeBase
from .faq import FAQSystem
from .prompts import PromptManager
from .product_catalog import ProductCatalog

__all__ = [
    "KnowledgeBase",
    "FAQSystem",
    "PromptManager",
    "ProductCatalog",
]
