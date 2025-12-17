"""
Product-related Pydantic models and schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class Product(BaseModel):
    """Product model."""
    
    id: str
    title: str
    price: float = Field(..., gt=0)
    vendor: str
    sellable: bool = True
    stock_quantity: Optional[int] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    image_url: Optional[str] = None
    sku: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "prod_123",
                "title": "USB-C to USB-C Cable 2m",
                "price": 19.99,
                "vendor": "CableCo",
                "sellable": True,
                "stock_quantity": 150
            }
        }


class Promotion(BaseModel):
    """Product promotion model."""
    
    product_id: str
    title: str
    discount: int = Field(..., ge=0, le=100, description="Discount percentage")
    end_date: str
    created_at: Optional[str] = None


class ProductWithPromotion(Product):
    """Product with optional promotion."""
    
    promotion: Optional[Promotion] = None
    discounted_price: Optional[float] = None
    score: Optional[float] = Field(None, description="Search relevance score")


class ProductSearchResult(BaseModel):
    """Search results for products."""
    
    products: List[ProductWithPromotion]
    promotions: List[Promotion] = []
    has_promotions: bool = False
    total_results: int
    query: str
    specifications: Optional[Dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "products": [],
                "promotions": [],
                "has_promotions": False,
                "total_results": 0,
                "query": "usb cable"
            }
        }


class ProductFeedback(BaseModel):
    """Product feedback/interaction tracking."""
    
    session_id: str
    product_id: str
    query: str
    action: str = Field(..., description="Action type: view, click, purchase")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_123",
                "product_id": "prod_456",
                "query": "hdmi cable",
                "action": "click"
            }
        }


class ProductSpecifications(BaseModel):
    """Extracted product specifications from user query."""
    
    cable_type: Optional[str] = None
    length_m: Optional[float] = None
    length_cm: Optional[float] = None
    length_ft: Optional[float] = None
    color: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    connector_type: Optional[str] = None
    
    def has_specs(self) -> bool:
        """Check if any specifications were extracted."""
        return any([
            self.cable_type,
            self.length_m,
            self.length_cm,
            self.length_ft,
            self.color,
            self.price_min,
            self.price_max,
            self.connector_type
        ])
