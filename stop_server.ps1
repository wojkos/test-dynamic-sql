# Stop Server Script for Chat-to-Data Application
# This script stops both the MCP server and FastAPI backend server

Write-Host "Stopping Chat-to-Data Application..." -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Yellow

# 1. Stop PowerShell Jobs
$jobs = Get-Job | Where-Object { $_.Command -like "*backend/mcp_server.py*" -or $_.Name -eq "mcpJob" }
if ($jobs) {
    Write-Host "Stopping background jobs..." -ForegroundColor Cyan
    $jobs | Stop-Job -ErrorAction SilentlyContinue
    $jobs | Remove-Job -Force -ErrorAction SilentlyContinue
}

# 2. Kill processes by port (more reliable if terminal was closed)
function Stop-ProcessByPort($port) {
    $processId = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($processId) {
        Write-Host "Stopping process on port $port (PID: $processId)..." -ForegroundColor Cyan
        foreach ($pid in $processId) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}

Stop-ProcessByPort 8000 # FastAPI
Stop-ProcessByPort 8001 # MCP Server

Write-Host ""
Write-Host "All servers stopped successfully." -ForegroundColor Green
