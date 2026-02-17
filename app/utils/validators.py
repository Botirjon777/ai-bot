"""
Input validation and sanitization utilities.
"""
import re
from typing import Optional
from .exceptions import ValidationError


def validate_message(message: str, min_length: int = 1, max_length: int = 1000) -> str:
    """
    Validate and sanitize user message.
    
    Args:
        message: User message to validate
        min_length: Minimum message length
        max_length: Maximum message length
    
    Returns:
        str: Sanitized message
    
    Raises:
        ValidationError: If validation fails
    """
    if not message or not isinstance(message, str):
        raise ValidationError("Message must be a non-empty string", field="message")
    
    message = message.strip()
    
    if len(message) < min_length:
        raise ValidationError(
            f"Message must be at least {min_length} characters",
            field="message"
        )
    
    if len(message) > max_length:
        raise ValidationError(
            f"Message must not exceed {max_length} characters",
            field="message"
        )
    
    # Check for nonsense (repeated characters or very low word diversity)
    words = message.lower().split()
    if len(words) >= 2:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:
            raise ValidationError(
                "Message appears to be nonsense or spam",
                field="message"
            )
    
    return message


def validate_email(email: str) -> str:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
    
    Returns:
        str: Validated email address
    
    Raises:
        ValidationError: If email format is invalid
    """
    if not email or not isinstance(email, str):
        raise ValidationError("Email must be a non-empty string", field="email")
    
    email = email.strip().lower()
    
    # Basic email regex pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    if not re.match(pattern, email):
        raise ValidationError("Invalid email format", field="email")
    
    return email


def sanitize_input(text: str, allow_html: bool = False) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Text to sanitize
        allow_html: Whether to allow HTML tags
    
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Remove control characters except newlines and tabs
    text = "".join(char for char in text if char.isprintable() or char in "\n\t")
    
    if not allow_html:
        # Escape HTML special characters
        text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
    
    return text.strip()


def validate_session_id(session_id: str) -> str:
    """
    Validate session ID format.
    
    Args:
        session_id: Session ID to validate
    
    Returns:
        str: Validated session ID
    
    Raises:
        ValidationError: If session ID format is invalid
    """
    if not session_id or not isinstance(session_id, str):
        raise ValidationError("Session ID must be a non-empty string", field="session_id")
    
    # Session IDs should be alphanumeric with hyphens/underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
        raise ValidationError("Invalid session ID format", field="session_id")
    
    if len(session_id) < 10 or len(session_id) > 100:
        raise ValidationError("Session ID length out of bounds", field="session_id")
    
    return session_id


def validate_product_id(product_id: str) -> str:
    """
    Validate product ID format.
    
    Args:
        product_id: Product ID to validate
    
    Returns:
        str: Validated product ID
    
    Raises:
        ValidationError: If product ID format is invalid
    """
    if not product_id or not isinstance(product_id, str):
        raise ValidationError("Product ID must be a non-empty string", field="product_id")
    
    product_id = product_id.strip()
    
    if len(product_id) < 1 or len(product_id) > 100:
        raise ValidationError("Product ID length out of bounds", field="product_id")
    
    return product_id
