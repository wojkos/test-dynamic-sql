# Dynamic Schema Detection - Implementation Guide

## Overview

This application now features **dynamic schema detection** that automatically introspects your database structure and generates appropriate LLM system prompts without any hardcoded table or column references.

## Key Features

### 1. Multi-Database Support
- **SQLite**: Auto-initializes with sample employee/department data if no database exists
- **PostgreSQL**: Connects to your existing database and detects its schema

### 2. Dynamic Schema Detection
- Uses SQLAlchemy Inspector to introspect database structure
- Detects tables, columns, data types, primary keys, and foreign key relationships
- Generates formatted schema descriptions for LLM consumption
- Caches schema for performance

### 3. Runtime Schema Refresh
- Schema detected automatically on application startup
- Manual refresh available via `/internal/refresh-schema` endpoint
- Re-initializes LLM with updated schema without restarting

## Configuration

### Environment Variables

```env
# LLM API Key (choose one, Gemini has priority)
GEMINI_API_KEY=your_gemini_key
# or
OPENAI_API_KEY=your_openai_key

# Database Type
DATABASE_TYPE=sqlite  # or postgresql

# PostgreSQL Configuration (if DATABASE_TYPE=postgresql)
POSTGRES_HOST=localhost  # or host.docker.internal for Docker
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
```

### Database Type Selection

#### SQLite (Default)
```env
DATABASE_TYPE=sqlite
```
- Automatically creates `backend/chat_data.db`
- Initializes with sample employees and departments tables
- Perfect for development and testing

#### PostgreSQL
```env
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=langflow
POSTGRES_USER=langflow
POSTGRES_PASSWORD=langflow
```
- Connects to existing PostgreSQL database
- Detects all tables, columns, and relationships
- Works with any schema structure

## Architecture Changes

### Files Modified

1. **backend/database.py**
   - Complete rewrite using SQLAlchemy
   - `init_database_engine()`: Initializes engine based on DATABASE_TYPE
   - `detect_schema()`: Introspects database structure
   - `format_schema_for_llm()`: Generates LLM-friendly schema text
   - `refresh_schema()`: Forces schema re-detection

2. **backend/llm_service.py**
   - Removed hardcoded SYSTEM_INSTRUCTION
   - `initialize_llm_with_schema(schema_text)`: Initializes LLM with dynamic schema
   - Works with both Gemini and OpenAI models

3. **backend/mcp_server.py**
   - Removed hardcoded "employees" and "departments" references
   - Generic tool descriptions work with any database structure

4. **backend/main.py**
   - Startup calls `detect_schema()` and `initialize_llm_with_schema()`
   - New `/internal/refresh-schema` endpoint for runtime updates
   - Added missing imports

5. **requirements.txt**
   - Added `sqlalchemy`
   - Added `psycopg2-binary`

## Usage Examples

### Using with SQLite (Default)

1. Set environment:
```env
DATABASE_TYPE=sqlite
OPENAI_API_KEY=your_key
```

2. Start application:
```bash
python backend/mcp_server.py &
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

3. Database automatically initializes with:
   - `employees` table (5 sample records)
   - `departments` table (3 sample records)

### Using with PostgreSQL

1. Set environment:
```env
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
OPENAI_API_KEY=your_key
```

2. Start application (same as above)

3. Schema automatically detected from your database

### Docker with PostgreSQL in Separate Network

If PostgreSQL runs in Docker on a different network:

```env
POSTGRES_HOST=host.docker.internal  # Windows/Mac Docker Desktop
# or
POSTGRES_HOST=172.17.0.1  # Linux Docker host
```

## Schema Refresh

To refresh schema without restarting:

```bash
curl -X POST http://localhost:8000/internal/refresh-schema
```

Response:
```json
{
  "success": true,
  "message": "Schema refreshed successfully",
  "tables": 12,
  "relationships": 8
}
```

## How It Works

### Startup Sequence

1. **Database Initialization**
   - `init_database_engine()` creates SQLAlchemy engine
   - SQLite: Creates database file and seeds sample data
   - PostgreSQL: Connects to existing database

2. **Schema Detection**
   - `detect_schema()` uses SQLAlchemy Inspector
   - Iterates through all tables
   - Extracts columns, types, constraints, foreign keys
   - Caches results in `_schema_cache`

3. **Schema Formatting**
   - `format_schema_for_llm()` generates text description
   - Creates CREATE TABLE statements
   - Documents relationships
   - Formats for LLM consumption

4. **LLM Initialization**
   - `initialize_llm_with_schema(schema_text)` called
   - Builds dynamic SYSTEM_INSTRUCTION
   - Initializes Gemini or OpenAI model
   - Model now "knows" your database structure

### Query Flow

1. User asks: "Show all records from users table"
2. LLM receives system prompt with YOUR schema
3. LLM generates: `SELECT * FROM users`
4. Query executes against your database
5. Results returned to user

## Benefits

✅ **Zero Hardcoding**: No table/column names in code  
✅ **Database Agnostic**: Works with any PostgreSQL schema  
✅ **Auto-Discovery**: Detects tables, columns, relationships  
✅ **Fallback Support**: SQLite with sample data if no DB configured  
✅ **Runtime Updates**: Refresh schema without restart  
✅ **Type Safety**: SQLAlchemy ensures proper data types  
✅ **Connection Pooling**: Efficient PostgreSQL connections  

## Troubleshooting

### Schema Not Detected
- Check database connection details in `.env`
- Verify PostgreSQL is accessible (test with `psql` or pgAdmin)
- Check application logs for connection errors

### LLM Generates Wrong SQL
- Verify schema was detected: `GET http://localhost:8000/schema`
- Check LLM system prompt includes your tables
- Try refreshing schema: `POST /internal/refresh-schema`

### PostgreSQL Connection Failed
- For Docker PostgreSQL, use `host.docker.internal` (Windows/Mac)
- Verify port mapping: `docker ps` should show `0.0.0.0:5432->5432/tcp`
- Check firewall/network settings
- Test connection: `psql -h localhost -U your_user -d your_db`

## Future Enhancements

- [ ] Support for MySQL/MariaDB
- [ ] Schema change detection (webhooks/polling)
- [ ] Multi-database querying (JOINs across databases)
- [ ] Schema documentation generation
- [ ] Query performance optimization hints
- [ ] Custom type mapping for domain-specific data
