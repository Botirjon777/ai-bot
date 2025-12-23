"""
Centralized configuration management for the AI Bot application.

This module provides type-safe configuration using Pydantic Settings,
with support for environment variables and validation.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class OpenSearchConfig(BaseSettings):
    """OpenSearch connection configuration."""
    
    host: str = "localhost"
    port: int = 9200
    use_ssl: bool = False
    verify_certs: bool = False
    index_name: str = "new-products-index"
    
    class Config:
        env_prefix = "OPENSEARCH_"
        extra = "ignore"


class RedisConfig(BaseSettings):
    """Redis connection configuration."""
    
    url: str = "redis://localhost:6379"
    session_ttl: int = 86400  # 24 hours
    cache_ttl: int = 3600  # 1 hour
    
    class Config:
        env_prefix = "REDIS_"
        extra = "ignore"


class OllamaConfig(BaseSettings):
    """Ollama AI service configuration."""
    
    api_url: str = "http://localhost:11434"
    model: str = "llama3:8b"
    timeout: int = 60
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 250
    
    class Config:
        env_prefix = "OLLAMA_"
        extra = "ignore"


class SecurityConfig(BaseSettings):
    """Security and authentication configuration."""
    
    session_secret: str = "change-me-to-32-bytes-secret-key-here"
    admin_api_key: str = "admin-secret-key-change-in-prod"
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600  # 1 hour
    
    class Config:
        env_prefix = "SECURITY_"
        extra = "ignore"


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""
    
    requests_per_minute: int = 5
    window_seconds: int = 60
    human_request_limit: int = 2
    human_request_window: int = 300  # 5 minutes
    
    class Config:
        env_prefix = "RATE_LIMIT_"
        extra = "ignore"


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    # Environment
    env: str = "dev"
    debug: bool = True
    
    # CORS
    cors_origins: list[str] = ["*"]  # Allow all origins for development
    
    # API
    api_prefix: str = "/api"
    
    # OpenAI (legacy, keeping for compatibility)
    openai_api_key: Optional[str] = None
    
    # Sub-configurations
    opensearch: OpenSearchConfig = OpenSearchConfig()
    redis: RedisConfig = RedisConfig()
    ollama: OllamaConfig = OllamaConfig()
    security: SecurityConfig = SecurityConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env.lower() in ("prod", "production")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env.lower() in ("dev", "development")


# Global configuration instance
config = AppConfig()


def get_config() -> AppConfig:
    """
    Get the global configuration instance.
    
    Returns:
        AppConfig: The application configuration
    """
    return config
