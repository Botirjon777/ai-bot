"""
Session-related Pydantic models and schemas.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class SessionMessage(BaseModel):
    """Individual message in a session."""
    
    role: str = Field(..., description="Message role: user, assistant, or admin")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "I need a USB cable",
                "timestamp": "2025-12-17T10:00:00Z"
            }
        }


class SessionInfo(BaseModel):
    """Session information and metadata."""
    
    session_id: str
    created_at: Optional[datetime] = None
    last_activity: Optional[int] = None
    ttl_seconds: Optional[int] = None
    message_count: int = 0
    messages: Optional[List[SessionMessage]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "message_count": 5,
                "ttl_seconds": 86400
            }
        }


class SessionCreate(BaseModel):
    """Session creation request."""
    
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class SessionResponse(BaseModel):
    """Session creation response."""
    
    session_id: str
    expires_in: int = Field(..., description="Session expiration in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "expires_in": 86400
            }
        }
