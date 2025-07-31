#!/bin/bash
# Start HubSpot Encyclopedia Middleware Server

# Navigate to middleware directory
cd "$(dirname "$0")"

# Check if server is already running
if lsof -ti:8000 > /dev/null; then
    echo "✅ Middleware server already running on port 8000"
    exit 0
fi

# Start the server in background
echo "🚀 Starting HubSpot Encyclopedia Middleware..."
python3 main.py &

# Wait a moment for startup
sleep 2

# Verify it started
if lsof -ti:8000 > /dev/null; then
    echo "✅ Middleware server started successfully on http://localhost:8000"
    echo "📚 Encyclopedia tools now available in Claude Desktop"
else
    echo "❌ Failed to start middleware server"
    exit 1
fi