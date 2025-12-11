#!/bin/bash
#
# 🏥 AI Health Bill Auditor - Quick Start Script
#
# Starts both backend and frontend with AI enabled
#

echo "
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🏥 AI HEALTH BILL AUDITOR                                         ║
║                                                                      ║
║   Starting with AI-powered analysis (Groq Llama 3.1)                ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"

# Load environment
# Set your GROQ_API_KEY in .env file or export it before running
export GROQ_API_KEY="${GROQ_API_KEY:-}"
export USE_SQLITE=true
export STORAGE_TYPE=local
export DEBUG=true
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Kill any existing processes
pkill -f "uvicorn app.main" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 1

# Create logs directory
mkdir -p logs

echo "🔧 Starting Backend API (port 8000)..."
cd backend && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
cd ..

echo "🎨 Starting Frontend (port 3000)..."
cd frontend && nohup npm run dev > ../logs/frontend.log 2>&1 &
cd ..

# Wait for services to start
sleep 5

# Check status
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend API: http://localhost:8000"
    echo "   📚 API Docs: http://localhost:8000/docs"
    
    # Check AI status
    AI_STATUS=$(curl -s http://localhost:8000/api/v1/audit/ai/status 2>/dev/null)
    if echo "$AI_STATUS" | grep -q "groq"; then
        echo "   🤖 AI: GROQ (Llama 3.1) - ACTIVE"
    else
        echo "   🤖 AI: Demo Mode"
    fi
else
    echo "❌ Backend failed to start"
    echo "   Check logs: tail -f logs/backend.log"
fi

# Check frontend
sleep 2
FRONTEND_PORT=$(grep -o "localhost:[0-9]*" logs/frontend.log 2>/dev/null | head -1)
if [ -n "$FRONTEND_PORT" ]; then
    echo ""
    echo "✅ Frontend: http://$FRONTEND_PORT"
else
    echo ""
    echo "⏳ Frontend starting... Check http://localhost:3000"
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
echo "📋 View logs:"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""

