# Chat-to-Data Application

A powerful natural language interface for querying and exploring databases using Gemini LLM and Model Context Protocol (MCP).

## Documentation
- [README.md](README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)

## Overview

This application allows users to interact with a database using natural language. It leverages Google's Gemini models for both standard text-to-SQL generation and advanced tool-calling through a custom MCP server.

## Features

- **Natural Language Querying**: Ask questions like "Who works in Engineering?" or "Show me the top 3 salaries" and get real-time SQL results.
- **MCP Integration**: Uses FastMCP to provide the LLM with direct access to database tools (schema viewing, raw data access, intelligent querying).
- **Interactive Chat**: A persistent chat interface that understands context and follow-up questions.
- **Schema Explorer**: Dynamically view the database structure and table definitions.
- **Raw Data Viewer**: Inspect the contents of tables directly from the UI.
- **Self-Healing Database**: The SQLite database (`backend/chat_data.db`) is automatically initialized and seeded on application startup.

## Tech Stack

- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Backend**: FastAPI (Python)
- **AI/LLM**: Google Gemini 2.0 Flash / 1.5 Flash
- **MCP**: FastMCP for Python
- **Database**: SQLite

## Getting Started

### Prerequisites

- Python 3.10+
- A Gemini API Key (get one at [Google AI Studio](https://aistudio.google.com/))

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd test-dynamic-sql
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the root directory with your Gemini API key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

### Running the Application

The project includes convenient PowerShell scripts to manage the servers:

**To Start:**
```powershell
.\start_server.ps1
```

**To Stop:**
```powershell
.\stop_server.ps1
```

The start script will:
1. Start the **MCP Server** on `http://127.0.0.1:8001`
2. Start the **Main API Server** (FastAPI) on `http://127.0.0.1:8000`
3. Automatically serve the frontend from the root URL.

Open your browser to [http://127.0.0.1:8000](http://127.0.0.1:8000) to start using the app.

## Project Structure

- `backend/`: Core logic
  - `main.py`: FastAPI application and LLM orchestration
  - `mcp_server.py`: FastMCP server implementation
  - `database.py`: SQLite database management and seeding
  - `llm_service.py`: Direct SQL generation service
- `frontend/`: UI files
  - `index.html`, `style.css`, `app.js`
- `start_server.ps1`: Automation script for server startup
- `stop_server.ps1`: Automation script for server shutdown
- `requirements.txt`: Python dependencies
