"""
Centralized Path Configuration

Simple, consistent paths for the entire application.
"""

import os
from pathlib import Path

# Project root - the main project directory (not backend/)
_current_file = Path(__file__).resolve()
# backend/app/core/paths.py -> backend/app/core -> backend/app -> backend -> project root
PROJECT_ROOT = _current_file.parent.parent.parent.parent

# Override with env var if set
if os.environ.get("PROJECT_ROOT"):
    PROJECT_ROOT = Path(os.environ["PROJECT_ROOT"])

# Key directories
DATA_DIR = PROJECT_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
LOGS_DIR = PROJECT_ROOT / "logs"

# Database
DATABASE_PATH = DATA_DIR / "local_dev.db"


def get_upload_path(file_key: str) -> Path:
    """
    Get the actual file path for an upload.
    Handles the 'uploads/' prefix in file_key.
    """
    # file_key is like "uploads/1/filename.jpeg"
    # Files are stored at "data/uploads/uploads/1/filename.jpeg"
    
    # Try direct path first
    path = DATA_DIR / file_key
    if path.exists():
        return path
    
    # Try with extra uploads folder (legacy)
    path = UPLOADS_DIR / file_key
    if path.exists():
        return path
    
    # Return the expected path even if not found
    return DATA_DIR / file_key


# Create directories if they don't exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

