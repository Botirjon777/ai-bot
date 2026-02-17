"""
Chat-related Pydantic models and schemas.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    user_info: Optional[Dict] = Field(None, description="Additional user information")
    
    @validator("message")
    def validate_message(cls, v):
        """Validate message is not just whitespace."""
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "I need a USB-C cable for my laptop",
                "user_info": {"timestamp": "2025-12-17T10:00:00Z"}
            }
        }


class ProductSuggestion(BaseModel):
    """Product suggestion in chat response."""
    
    id: str
    title: str
    price: float
    vendor: str
    promotion: Optional[Dict] = None
    discounted_price: Optional[float] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    
    response: str = Field(..., description="AI assistant response")
    session_id: str = Field(..., description="Session identifier")
    suggested_products: Optional[List[ProductSuggestion]] = Field(
        None, description="List of suggested products"
    )
    has_promotions: bool = Field(False, description="Whether response includes promotions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "I can help you with that! We have several USB-C cables available.",
                "session_id": "abc123",
                "suggested_products": [
                    {
                        "id": "prod_1",
                        "title": "USB-C to USB-C Cable 2m",
                        "price": 19.99,
                        "vendor": "CableCo"
                    }
                ],
                "has_promotions": False
            }
        }


class HumanRequest(BaseModel):
    """Request to speak with a human assistant."""
    
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    message: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "message": "I need help with a custom cable order"
            }
        }


class ProductClickRequest(BaseModel):
    """Track when user clicks on a product."""
    
    product_id: str = Field(..., description="Product identifier")
    query: str = Field(..., description="Search query that led to this product")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "prod_123",
                "query": "usb-c cable 2m"
            }
        }
