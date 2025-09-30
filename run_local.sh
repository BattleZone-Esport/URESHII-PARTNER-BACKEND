#!/bin/bash

# Quick start script for local development

echo "🚀 Starting Coding AI Assistant Backend..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create models directory if it doesn't exist
mkdir -p models

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your MongoDB URI and other settings"
fi

# Start the application
echo ""
echo "✨ Starting FastAPI application..."
echo "📍 API will be available at http://localhost:8000"
echo "📚 Documentation at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the application
python main.py