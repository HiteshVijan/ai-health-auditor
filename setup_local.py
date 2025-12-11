#!/usr/bin/env python3
"""
🏥 AI Health Bill Auditor - Local Setup Script

This script sets up everything you need to run the application locally
using FREE resources only:

- SQLite database (no install needed)
- Local file storage (no S3/MinIO needed)
- No Docker required
- No paid services

Usage:
    python setup_local.py

After setup, run:
    python run_demo.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def run_command(cmd, cwd=None, check=True):
    """Run a shell command."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, 
            capture_output=True, text=True, check=check
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def main():
    print(f"""
{Colors.BOLD}
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🏥 AI HEALTH BILL AUDITOR - LOCAL SETUP                ║
    ║                                                           ║
    ║   Setting up with FREE resources only!                   ║
    ║   No Docker • No Paid Services • No Cloud Required       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
{Colors.END}
    """)

    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Step 1: Check Python version
    print_header("Step 1: Checking Python Environment")
    
    python_version = sys.version_info
    if python_version >= (3, 9):
        print_success(f"Python {python_version.major}.{python_version.minor} detected")
    else:
        print_error(f"Python 3.9+ required. You have {python_version.major}.{python_version.minor}")
        sys.exit(1)

    # Step 2: Create required directories
    print_header("Step 2: Creating Directory Structure")
    
    directories = [
        "data/uploads",
        "data/processed", 
        "data/icd10",
        "data/hcpcs",
        "data/cpt",
        "data/fee_schedules",
        "data/indian_rates",
        "logs",
    ]
    
    for dir_path in directories:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print_success(f"Created {dir_path}/")

    # Step 3: Install Python dependencies
    print_header("Step 3: Installing Python Dependencies")
    
    # Core dependencies for local dev
    core_deps = [
        "fastapi",
        "uvicorn[standard]",
        "sqlalchemy",
        "pydantic",
        "pydantic-settings",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "python-multipart",
        "slowapi",
        "rapidfuzz",
        "pandas",
        "numpy",
        "python-dotenv",
        "httpx",  # For testing
        "aiosqlite",  # SQLite async support
    ]
    
    print_info("Installing core dependencies...")
    success, _ = run_command(f"pip install {' '.join(core_deps)} --quiet", check=False)
    if success:
        print_success("Core dependencies installed")
    else:
        print_warning("Some dependencies may have issues, continuing...")

    # Step 4: Download/Generate medical code data
    print_header("Step 4: Setting Up Medical Code Database")
    
    # Check if data already exists
    combined_codes = project_root / "data" / "processed" / "combined_codes.json"
    if combined_codes.exists():
        print_success("Medical code database already exists")
    else:
        print_info("Generating medical code database...")
        sys.path.insert(0, str(project_root))
        try:
            from scripts.download_medical_codes import main as download_codes
            download_codes()
            print_success("Medical code database created")
        except Exception as e:
            print_warning(f"Could not auto-generate: {e}")
            print_info("Run 'python -m scripts.download_medical_codes' manually")

    # Step 5: Create local environment file
    print_header("Step 5: Creating Environment Configuration")
    
    env_local = project_root / ".env.local"
    env_content = f"""# Local Development Configuration
# Generated by setup_local.py

# Application
APP_NAME="AI Health Bill Auditor"
DEBUG=true
API_V1_PREFIX=/api/v1

# Database (SQLite - no install needed!)
DATABASE_URL=sqlite:///{project_root}/data/local_dev.db

# JWT Secret (change in production!)
SECRET_KEY=local-dev-secret-key-{os.urandom(8).hex()}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Storage (local filesystem)
STORAGE_TYPE=local
LOCAL_STORAGE_PATH={project_root}/data/uploads

# Medical Codes
MEDICAL_CODES_DATA_DIR={project_root}/data/processed

# Region
DEFAULT_REGION=AUTO

# LLM (optional - set your API key if you have one)
LLM_PROVIDER=none
# OPENAI_API_KEY=your-key-here
# GROQ_API_KEY=your-key-here

# Email (disabled for local dev)
EMAIL_ENABLED=false
"""
    
    with open(env_local, "w") as f:
        f.write(env_content)
    print_success(f"Created .env.local")

    # Step 6: Initialize SQLite database
    print_header("Step 6: Initializing Database")
    
    db_path = project_root / "data" / "local_dev.db"
    if db_path.exists():
        print_success("Database already exists")
    else:
        print_info("Creating SQLite database...")
        # Create a minimal database setup
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    full_name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_superuser BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    filename TEXT NOT NULL,
                    file_key TEXT,
                    content_type TEXT,
                    file_size INTEGER,
                    status TEXT DEFAULT 'uploaded',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            conn.commit()
            conn.close()
            print_success("SQLite database initialized")
        except Exception as e:
            print_error(f"Database setup failed: {e}")

    # Step 7: Check Node.js for frontend
    print_header("Step 7: Checking Frontend Dependencies")
    
    success, output = run_command("node --version", check=False)
    if success and output:
        print_success(f"Node.js {output.strip()} detected")
        
        # Check if node_modules exists
        node_modules = project_root / "frontend" / "node_modules"
        if node_modules.exists():
            print_success("Frontend dependencies already installed")
        else:
            print_info("Installing frontend dependencies...")
            success, _ = run_command("npm install", cwd=str(project_root / "frontend"), check=False)
            if success:
                print_success("Frontend dependencies installed")
            else:
                print_warning("Frontend install had issues - run 'cd frontend && npm install' manually")
    else:
        print_warning("Node.js not found - frontend won't work")
        print_info("Install Node.js from https://nodejs.org/ (free)")

    # Step 8: Verify setup
    print_header("Step 8: Verifying Setup")
    
    checks = [
        ("Medical code database", (project_root / "data" / "processed" / "combined_codes.json").exists()),
        ("Environment config", (project_root / ".env.local").exists()),
        ("SQLite database", (project_root / "data" / "local_dev.db").exists()),
        ("Upload directory", (project_root / "data" / "uploads").exists()),
    ]
    
    all_good = True
    for name, passed in checks:
        if passed:
            print_success(name)
        else:
            print_error(name)
            all_good = False

    # Final summary
    print_header("Setup Complete!")
    
    if all_good:
        print(f"""
{Colors.GREEN}{Colors.BOLD}
    ✅ Everything is set up and ready!
{Colors.END}

    To run the application:

    {Colors.BOLD}1. Start the Backend API:{Colors.END}
       cd backend
       python run_local.py
       
       API will be at: http://localhost:8000
       Docs at: http://localhost:8000/docs

    {Colors.BOLD}2. Start the Frontend (in another terminal):{Colors.END}
       cd frontend
       npm run dev
       
       App will be at: http://localhost:5173

    {Colors.BOLD}3. Or run the demo script:{Colors.END}
       python run_demo.py

    {Colors.BOLD}Free Resources Used:{Colors.END}
    • SQLite database (no install needed)
    • Local file storage
    • CGHS/PMJAY pricing data (free, public)
    • CMS medical codes (free, public domain)

    {Colors.YELLOW}💡 Tip: For a pitch demo, run 'python run_demo.py'{Colors.END}
        """)
    else:
        print(f"""
{Colors.YELLOW}
    ⚠ Setup completed with some issues.
    Check the errors above and fix them manually.
{Colors.END}
        """)

if __name__ == "__main__":
    main()

