"""
Local Development Configuration - No Docker Required!

This config uses:
- SQLite instead of PostgreSQL
- Local filesystem instead of MinIO/S3
- No Redis/Celery (synchronous processing)

Perfect for local laptop development.
"""

from pydantic_settings import BaseSettings
from typing import Optional, Literal
from pathlib import Path


# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class LocalSettings(BaseSettings):
    """Local development settings - no external dependencies."""

    # Application
    APP_NAME: str = "AI Health Bill Auditor (Local Dev)"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Multi-Region Support
    DEFAULT_REGION: Literal["US", "IN", "AUTO"] = "AUTO"
    SUPPORTED_CURRENCIES: list[str] = ["USD", "INR"]
    
    # Database - SQLite (no install needed!)
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT}/data/local_dev.db"
    
    # JWT Authentication
    SECRET_KEY: str = "local-dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Longer for dev
    
    # Storage - Local filesystem
    STORAGE_TYPE: str = "local"
    LOCAL_STORAGE_PATH: str = str(PROJECT_ROOT / "data" / "uploads")
    
    # Medical Code Database
    MEDICAL_CODES_DATA_DIR: str = str(PROJECT_ROOT / "data" / "processed")
    
    # LLM Configuration (optional - for negotiation letters)
    LLM_PROVIDER: Literal["openai", "groq", "ollama", "none"] = "none"
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # Email (disabled for local dev)
    EMAIL_ENABLED: bool = False
    
    # Indian Market
    INDIA_GST_RATE: float = 0.18
    
    class Config:
        env_file = ".env.local"
        case_sensitive = True


# Create instance
local_settings = LocalSettings()

# Ensure directories exist
Path(local_settings.LOCAL_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

