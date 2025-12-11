#!/usr/bin/env python3
"""
🤖 AI Setup Script for Health Bill Auditor

Sets up FREE AI capabilities using:
1. Groq (recommended) - Free tier: 30 req/min
2. Ollama (local) - Completely free, runs locally

Run this to enable AI-powered:
- Bill Analysis
- Issue Detection
- Negotiation Letter Generation
"""

import os
import sys
import subprocess

# Colors
G = '\033[92m'
Y = '\033[93m'
R = '\033[91m'
B = '\033[94m'
C = '\033[96m'
BOLD = '\033[1m'
END = '\033[0m'

def print_header():
    print(f"""
{BOLD}{C}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🤖 AI SETUP - Health Bill Auditor                                 ║
║                                                                      ║
║   Enable FREE AI-powered analysis and letter generation             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
{END}
""")

def check_groq():
    """Check if Groq API key is set."""
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        print(f"{G}✓ Groq API key found{END}")
        return True
    return False

def check_ollama():
    """Check if Ollama is running."""
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"{G}✓ Ollama running with {len(models)} models{END}")
            return True
    except:
        pass
    return False

def setup_groq():
    """Guide user to set up Groq (free tier)."""
    print(f"""
{BOLD}{B}Option 1: Groq Cloud (Recommended){END}

Groq offers a FREE tier with:
  • 30 requests per minute
  • Llama 3.1, Mixtral, Gemma models
  • Super fast inference

{BOLD}Steps:{END}
  1. Go to: {C}https://console.groq.com/{END}
  2. Sign up for FREE (Google/GitHub login)
  3. Go to API Keys → Create new key
  4. Copy your API key

""")
    
    key = input(f"{Y}Paste your Groq API key (or press Enter to skip): {END}").strip()
    
    if key:
        # Save to .env file
        env_path = os.path.join(os.path.dirname(__file__), ".env.local")
        
        # Read existing content
        existing = ""
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                existing = f.read()
        
        # Add or update GROQ_API_KEY
        if "GROQ_API_KEY" in existing:
            lines = existing.split("\n")
            lines = [l for l in lines if not l.startswith("GROQ_API_KEY")]
            existing = "\n".join(lines)
        
        with open(env_path, "a") as f:
            f.write(f"\nGROQ_API_KEY={key}\n")
        
        print(f"{G}✓ Groq API key saved to .env.local{END}")
        
        # Also export for current session
        os.environ["GROQ_API_KEY"] = key
        
        # Test the key
        print(f"\n{Y}Testing Groq API...{END}")
        test_groq(key)
        return True
    
    return False

def test_groq(api_key):
    """Test Groq API."""
    try:
        import httpx
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": "Say 'AI is ready!' in 3 words"}],
                "max_tokens": 20,
            },
            timeout=10.0,
        )
        
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            print(f"{G}✓ Groq API working! Response: {reply}{END}")
            return True
        else:
            print(f"{R}✗ Groq API error: {response.status_code}{END}")
            
    except Exception as e:
        print(f"{R}✗ Groq test failed: {e}{END}")
    
    return False

def setup_ollama():
    """Guide user to set up Ollama (local)."""
    print(f"""
{BOLD}{B}Option 2: Ollama (Local AI){END}

Ollama runs AI models locally on your machine.
  • Completely FREE
  • No API keys needed
  • Works offline

{BOLD}Steps:{END}
  1. Install Ollama: {C}https://ollama.ai/download{END}
  2. Run: {C}ollama pull llama3.2{END}
  3. Ollama runs automatically in background

""")
    
    install = input(f"{Y}Try to install Ollama now? (y/n): {END}").strip().lower()
    
    if install == 'y':
        print(f"\n{Y}Installing Ollama...{END}")
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["brew", "install", "ollama"], check=True)
            else:
                print(f"Please install from: https://ollama.ai/download")
                return False
            
            print(f"{G}✓ Ollama installed{END}")
            
            # Pull a model
            print(f"\n{Y}Pulling llama3.2 model (this may take a few minutes)...{END}")
            subprocess.run(["ollama", "pull", "llama3.2"], check=True)
            
            print(f"{G}✓ Model ready{END}")
            return True
            
        except Exception as e:
            print(f"{R}Installation failed: {e}{END}")
            print(f"Please install manually from: https://ollama.ai/download")
    
    return False

def show_status():
    """Show current AI status."""
    print(f"\n{BOLD}Current AI Status:{END}")
    
    has_groq = check_groq()
    has_ollama = check_ollama()
    
    if has_groq:
        print(f"\n{G}🤖 AI is READY using Groq Cloud{END}")
        print(f"   Model: llama-3.1-8b-instant")
        print(f"   Free tier: 30 requests/minute")
    elif has_ollama:
        print(f"\n{G}🤖 AI is READY using Ollama (Local){END}")
        print(f"   Model: llama3.2")
        print(f"   Completely free, runs locally")
    else:
        print(f"\n{Y}⚠️ No AI provider configured{END}")
        print(f"   Running in demo mode with sample responses")
        return False
    
    return True

def main():
    print_header()
    
    print(f"{BOLD}Checking current AI setup...{END}\n")
    
    has_ai = show_status()
    
    if has_ai:
        print(f"\n{G}You're all set! AI is ready to use.{END}")
        
        again = input(f"\n{Y}Configure a different provider? (y/n): {END}").strip().lower()
        if again != 'y':
            return
    
    print(f"\n{BOLD}Choose an AI provider:{END}")
    print(f"  1. Groq Cloud (recommended, free tier)")
    print(f"  2. Ollama (local, completely free)")
    print(f"  3. Skip for now (demo mode)")
    
    choice = input(f"\n{Y}Enter choice (1/2/3): {END}").strip()
    
    if choice == "1":
        setup_groq()
    elif choice == "2":
        setup_ollama()
    else:
        print(f"\n{Y}Skipping AI setup. Running in demo mode.{END}")
    
    print(f"""
{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{END}

{BOLD}To start the app with AI:{END}

  # If using Groq, make sure the key is exported:
  export GROQ_API_KEY="your-key-here"
  
  # Start backend
  cd backend && uvicorn app.main:app --reload
  
  # In another terminal, start frontend
  cd frontend && npm run dev

{BOLD}AI will be used for:{END}
  ✅ Bill Analysis & Issue Detection
  ✅ Fair Price Comparison
  ✅ Negotiation Letter Generation
  ✅ Patient Assistance

{G}Happy auditing! 🏥{END}
""")

if __name__ == "__main__":
    main()

