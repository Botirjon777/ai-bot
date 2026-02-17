"""
Custom exception hierarchy for the AI Bot application.
"""
from typing import Optional, Dict, Any


class AIBotException(Exception):
    """Base exception for all AI Bot errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(AIBotException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class SearchError(AIBotException):
    """Raised when product search fails."""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if query:
            details["query"] = query
        super().__init__(message, error_code="SEARCH_ERROR", details=details)


class SessionError(AIBotException):
    """Raised when session operations fail."""
    
    def __init__(self, message: str, session_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if session_id:
            details["session_id"] = session_id
        super().__init__(message, error_code="SESSION_ERROR", details=details)


class RateLimitError(AIBotException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None, **kwargs):
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, error_code="RATE_LIMIT_ERROR", details=details)


class AIServiceError(AIBotException):
    """Raised when AI service (Ollama) fails."""
    
    def __init__(self, message: str, service: str = "ollama", **kwargs):
        details = kwargs.get("details", {})
        details["service"] = service
        super().__init__(message, error_code="AI_SERVICE_ERROR", details=details)


class OpenSearchError(AIBotException):
    """Raised when OpenSearch operations fail."""
    
    def __init__(self, message: str, index: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if index:
            details["index"] = index
        super().__init__(message, error_code="OPENSEARCH_ERROR", details=details)


class RedisError(AIBotException):
    """Raised when Redis operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code="REDIS_ERROR", details=details)
