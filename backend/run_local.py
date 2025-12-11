#!/usr/bin/env python3
"""
Run the backend locally - No Docker Required!

Usage:
    python run_local.py

This will start the API server at http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
"""

import sys
import os
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Set environment for local development
os.environ["DATABASE_URL"] = f"sqlite:///{project_root}/data/local_dev.db"
os.environ["DEBUG"] = "true"

def main():
    print("=" * 60)
    print("  🏥 AI Health Bill Auditor - Local Development Server")
    print("=" * 60)
    print()
    print("  Starting server...")
    print()
    print("  📍 API URL:      http://localhost:8000")
    print("  📚 API Docs:     http://localhost:8000/docs")
    print("  ❤️  Health Check: http://localhost:8000/health")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info",
    )


if __name__ == "__main__":
    main()

