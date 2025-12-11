"""
Application configuration using Pydantic Settings.

Loads environment variables and provides typed configuration access.
Supports both US and Indian healthcare markets.
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "AI Health Bill Auditor"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Multi-Region Support
    DEFAULT_REGION: Literal["US", "IN", "AUTO"] = "AUTO"
    SUPPORTED_CURRENCIES: list[str] = ["USD", "INR"]
    
    # Database - uses SQLite by default for easy local dev
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "sqlite:///./data/local_dev.db" if os.environ.get("USE_SQLITE") else "postgresql://localhost:5432/health_auditor_db"
    )

    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # MinIO / Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "health-bills"
    
    # Medical Code Database
    MEDICAL_CODES_DATA_DIR: str = "data/processed"
    
    # LLM Configuration (for negotiation letters)
    LLM_PROVIDER: Literal["openai", "groq", "ollama", "gemini"] = "openai"
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # Email Configuration
    EMAIL_PROVIDER: Literal["resend", "ses", "smtp"] = "resend"
    RESEND_API_KEY: Optional[str] = None
    
    # Indian Market Specific
    INDIA_GST_RATE: float = 0.18  # 18% GST on healthcare services
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

