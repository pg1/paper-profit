#!/bin/bash
# Start the backend server

echo "🚀 Starting PaperProfit ..."
echo "================================"

# Check if we're in the right directory
if [ ! -f "backend/app/main.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   Current directory should contain 'backend/' and 'frontend/' folders"
    exit 1
fi

# Navigate to backend directory
cd backend

# Check if virtual venvironment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual venvironment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt | grep -v "Requirement already satisfied"

cd app

#check if it's a new install
if [ ! -f "PaperProfit.db" ]; then
    echo "⚙️  New install starting migration script ..."
    python main.py migrate     
fi


# Function to handle cleanup on exit
cleanup() {
    echo "Stopping processes..."
    kill $API_PID $BACKGROUND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start the background job
echo "Starting background jobs ..."
python background.py &
BACKGROUND_PID=$!

# Start the API
echo "🌐 Starting FastAPI server"
echo "   API Documentation: http://localhost:8000/docs"
echo ""
python api.py &
API_PID=$!

# Wait for both processes
echo "Both processes started. Press Ctrl+C to stop."
echo "API PID: $API_PID"
echo "Background Job PID: $BACKGROUND_PID"

wait
