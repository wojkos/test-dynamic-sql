# Start Server Script for Chat-to-Data Application
# This script starts both the MCP server and FastAPI backend server

Write-Host "Starting Chat-to-Data Application..." -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Please create a .env file with your configuration." -ForegroundColor Yellow
    Write-Host ""
}

# Function to check if fastmcp is installed
$fastmcpInstalled = pip show fastmcp 2>$null
if (-not $fastmcpInstalled) {
    Write-Host "Installing FastMCP..." -ForegroundColor Yellow
    pip install fastmcp
    Write-Host ""
}

# Start MCP Server in background
Write-Host "Starting MCP Server on http://127.0.0.1:8001 ..." -ForegroundColor Green
$mcpJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python backend/mcp_server.py
}
Write-Host "MCP Server started (Job ID: $($mcpJob.Id))" -ForegroundColor Cyan

# Give MCP server a moment to start
Start-Sleep -Seconds 2

# Start the main FastAPI server
Write-Host ""
Write-Host "Starting Main API Server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  Open http://127.0.0.1:8000 in your browser  " -ForegroundColor White
Write-Host "  Click 'MCP Chat' to test MCP functionality  " -ForegroundColor White
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all servers" -ForegroundColor Yellow
Write-Host ""

try {
    uvicorn backend.main:app --reload
} finally {
    # Cleanup: Stop MCP server when main server stops
    Write-Host ""
    Write-Host "Stopping MCP Server..." -ForegroundColor Yellow
    Stop-Job -Job $mcpJob -ErrorAction SilentlyContinue
    Remove-Job -Job $mcpJob -Force -ErrorAction SilentlyContinue
    Write-Host "All servers stopped." -ForegroundColor Cyan
}

