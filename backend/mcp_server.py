"""
MCP Server for Database Queries

This FastMCP server exposes tools for querying the employees and departments database.
The LLM uses the tool descriptions to decide when to invoke these tools.
"""

from fastmcp import FastMCP
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import execute_read_query, get_schema, get_table_data
from backend.llm_service import generate_sql

# Create FastMCP server with clear description for tool discovery
mcp = FastMCP(
    name="DatabaseMCPServer",
    instructions="""
    MCP server for querying employee and department data.
    Use this server when users ask about employees, departments, salaries, roles, budgets, managers, or locations.
    """
)


@mcp.tool
def query_database(question: str) -> dict:
    """
    Query the employees and departments database using natural language.
    
    Use this tool for ANY questions about:
    - Employees (names, roles, salaries, locations)
    - Departments (names, budgets, managers, locations)
    - Relationships between employees and departments
    - Salary information and comparisons
    - Role and position queries
    - Location-based queries
    - Manager assignments
    
    Args:
        question: Natural language question about employees or departments
        
    Returns:
        Dictionary with generated SQL, query results, and any errors
    """
    try:
        # Generate SQL from natural language using LLM
        generated_sql = generate_sql(question)
        
        # Execute the query
        result = execute_read_query(generated_sql)
        
        return {
            "success": True,
            "sql": generated_sql,
            "data": result.get("data", []),
            "error": result.get("error"),
            "row_count": len(result.get("data", []))
        }
    except Exception as e:
        return {
            "success": False,
            "sql": None,
            "data": [],
            "error": str(e),
            "row_count": 0
        }


@mcp.tool
def get_database_schema() -> dict:
    """
    Get the database schema including all tables and their columns.
    
    Use this tool when users want to:
    - See what tables exist in the database
    - Understand the database structure
    - Know what columns are available
    - Learn about table relationships
    
    Returns:
        Dictionary with schema information for all tables
    """
    try:
        result = get_schema()
        return {
            "success": True,
            "schema": result.get("schema", []),
            "error": result.get("error")
        }
    except Exception as e:
        return {
            "success": False,
            "schema": [],
            "error": str(e)
        }


@mcp.tool
def get_table_raw_data(table_name: str) -> dict:
    """
    Get all raw data from a specific database table.
    
    Use this tool when users want to:
    - See all data in a specific table
    - View raw/unfiltered table contents
    - Export or review complete table data
    
    Args:
        table_name: Name of the table (either 'employees' or 'departments')
        
    Returns:
        Dictionary with all rows from the specified table
    """
    try:
        result = get_table_data(table_name)
        return {
            "success": True,
            "table_name": table_name,
            "data": result.get("data", []),
            "error": result.get("error"),
            "row_count": len(result.get("data", []))
        }
    except Exception as e:
        return {
            "success": False,
            "table_name": table_name,
            "data": [],
            "error": str(e),
            "row_count": 0
        }


if __name__ == "__main__":
    # Run with HTTP transport for easy integration
    # Allow host binding to be configured via env var (default to 0.0.0.0 for Docker)
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8001"))
    
    print(f"Starting MCP Server on {host}:{port}")
    mcp.run(transport="sse", host=host, port=port)
