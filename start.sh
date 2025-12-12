#!/bin/bash
#
# 🏥 AI Health Bill Auditor - Quick Start Script
#

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🏥 AI HEALTH BILL AUDITOR                                         ║
║                                                                      ║
║   Starting with AI-powered analysis (Groq Llama 3.1)                ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"

# Load environment from .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
    echo "✅ Loaded .env file"
fi

export USE_SQLITE=true
export STORAGE_TYPE=local
export DEBUG=true
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
export DATABASE_URL="sqlite:///$SCRIPT_DIR/data/local_dev.db"

# Kill any existing processes
pkill -f "uvicorn app.main" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 1

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

echo "🔧 Starting Backend API (port 8000)..."
cd "$SCRIPT_DIR/backend"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$SCRIPT_DIR/logs/backend.log" 2>&1 &

echo "🎨 Starting Frontend (port 3000)..."
cd "$SCRIPT_DIR/frontend"
nohup npm run dev > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &

# Return to script dir
cd "$SCRIPT_DIR"

# Wait for services to start
sleep 5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check backend
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✅ Backend API: http://localhost:8000"
    echo "   📚 API Docs: http://localhost:8000/docs"
    
    if [ -n "$GROQ_API_KEY" ]; then
        echo "   🤖 AI: GROQ (Llama 3.1) - ACTIVE"
    else
        echo "   ⚠️  AI: No API key found. Set GROQ_API_KEY in .env"
    fi
else
    echo "❌ Backend failed to start"
    echo "   Check logs: tail -f logs/backend.log"
fi

# Check frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo ""
    echo "✅ Frontend: http://localhost:3000"
else
    echo ""
    echo "⏳ Frontend starting... http://localhost:3000"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Test Account:"
echo "   Email: testone@gmail.com"
echo "   Password: testpassword123"
echo ""
echo "🛑 To stop: pkill -f uvicorn && pkill -f vite"
echo ""
