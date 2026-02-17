"""
Admin-related Pydantic models and schemas.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from .session import SessionInfo, SessionMessage


class AdminMessage(BaseModel):
    """Admin message to send to a user session."""
    
    message: str = Field(..., min_length=1, max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello! I'm a human assistant. How can I help you?"
            }
        }


class SessionListResponse(BaseModel):
    """Response containing list of active sessions."""
    
    sessions: List[SessionInfo]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "sessions": [],
                "total": 0
            }
        }


class SessionHistoryResponse(BaseModel):
    """Response containing full session history."""
    
    session_id: str
    messages: List[SessionMessage]
    message_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_123",
                "messages": [],
                "message_count": 0
            }
        }


class AdminAuth(BaseModel):
    """Admin authentication credentials."""
    
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str
    ollama: str
    redis: str = "unknown"
    opensearch: str = "unknown"
    model: str
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "ollama": "connected",
                "redis": "connected",
                "opensearch": "connected",
                "model": "phi3:3.8b",
                "timestamp": "2025-12-17T10:00:00Z"
            }
        }
