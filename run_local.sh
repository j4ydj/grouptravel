#!/bin/bash
# Quick start script for local development

echo "Starting Group Travel Optimiser..."

# Create data directory if it doesn't exist
mkdir -p data

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements-backend.txt
pip install -q -r requirements-frontend.txt

# Initialize database
echo "Initializing database..."
cd app/backend
python -m app.backend.db.init_db
cd ../..

# Start backend in background
echo "Starting backend..."
cd app/backend
uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend..."
cd app/frontend
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
