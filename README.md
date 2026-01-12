# Chat-to-Data Application

A powerful natural language interface for querying and exploring databases using Gemini LLM and Model Context Protocol (MCP).

## Documentation
- [README.md](README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)

## Overview

This application allows users to interact with databases using natural language. It dynamically detects database schemas and generates appropriate SQL queries without any hardcoded table or column references. The system supports both SQLite (with sample data) and PostgreSQL databases, leveraging Google's Gemini or OpenAI models for text-to-SQL generation and advanced tool-calling through a custom MCP server.

## Features

- **Dynamic Schema Detection**: Automatically detects database structure at startup and generates LLM prompts based on actual tables, columns, and relationships.
- **Multi-Database Support**: Works with SQLite (auto-initialized with sample data) or PostgreSQL (connects to existing database).
- **Natural Language Querying**: Ask questions about any data in your database and get real-time SQL results.
- **MCP Integration**: Uses FastMCP to provide the LLM with direct access to database tools (schema viewing, raw data access, intelligent querying).
- **Interactive Chat**: A persistent chat interface that understands context and follow-up questions.
- **Schema Explorer**: Dynamically view the database structure and table definitions.
- **Raw Data Viewer**: Inspect the contents of tables directly from the UI.
- **Schema Refresh Endpoint**: Runtime schema updates without restarting the application (`/internal/refresh-schema`).
- **Dual LLM Support**: Works with Google Gemini (priority) or OpenAI GPT-4o-mini.

## Tech Stack

- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Backend**: FastAPI (Python)
- **AI/LLM**: Google Gemini 2.0 Flash or OpenAI GPT-4o-mini
- **MCP**: FastMCP for Python
- **Database**: SQLite or PostgreSQL
- **ORM**: SQLAlchemy (for database abstraction and schema introspection)

## Getting Started

### Prerequisites

- Python 3.10+
- An API key for either:
  - **Gemini** (get one at [Google AI Studio](https://aistudio.google.com/)) - Recommended
  - **OpenAI** (get one at [OpenAI Platform](https://platform.openai.com/))
- Optional: PostgreSQL database (if not using SQLite)

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
   Create a `.env` file in the root directory:
   
   **For SQLite (default - auto-initializes with sample employee/department data):**
   ```env
   # LLM API Key (choose one, Gemini has priority)
   GEMINI_API_KEY=your_gemini_key_here
   # or
   OPENAI_API_KEY=your_openai_key_here
   
   # Database Configuration
   DATABASE_TYPE=sqlite
   ```
   
   **For PostgreSQL (connects to your existing database):**
   ```env
   # LLM API Key
   OPENAI_API_KEY=your_openai_key_here
   
   # Database Configuration
   DATABASE_TYPE=postgresql
   POSTGRES_HOST=localhost  # or host.docker.internal if PG is in Docker
   POSTGRES_PORT=5432
   POSTGRES_DB=your_database_name
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=your_password
   ```
   
   The application will automatically detect your database schema and generate appropriate system prompts for the LLM.

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
  - `main.py`: FastAPI application, MCP orchestration, and schema refresh endpoint
  - `mcp_server.py`: FastMCP server implementation (generic, database-agnostic)
  - `database.py`: SQLAlchemy-based database abstraction with dynamic schema detection
  - `llm_service.py`: Dynamic SQL generation service with runtime schema initialization
- `frontend/`: UI files
  - `index.html`, `style.css`, `app.js`
- `start_server.ps1`: Automation script for server startup (Windows)
- `start.sh`: Automation script for server startup (Linux/Docker)
- `stop_server.ps1`: Automation script for server shutdown
- `requirements.txt`: Python dependencies
- `.env`: Configuration for API keys and database connection
- `docker-compose.yml`: Docker containerization
