#!/bin/bash

# Start MCP Server in background
# We default to 0.0.0.0 via python code modification, or we can explicit set here
export MCP_HOST=0.0.0.0
export MCP_PORT=8001

echo "Starting MCP Server..."
python backend/mcp_server.py &

# Wait a moment for MCP server to start
sleep 2

# Start Main API Server
# App connects to MCP server at localhost:8001 (inside container loopback)
echo "Starting Main API Server..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000
