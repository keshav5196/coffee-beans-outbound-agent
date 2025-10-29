#!/bin/bash

# Setup script for Outbound AI Agent

echo "🚀 Setting up Outbound AI Agent..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Sync dependencies using uv
echo "📦 Installing dependencies..."
uv sync

# Create .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env with your Twilio credentials"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env with your Twilio credentials"
echo "2. Run: ngrok http 8000 (in another terminal)"
echo "3. Run: uv run python main.py"
