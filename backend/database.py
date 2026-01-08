import sqlite3
import os

DB_PATH = "backend/chat_data.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create departments table first (referenced by employees)
    cursor.execute("""
    CREATE TABLE departments (
      id INTEGER PRIMARY KEY,
      name TEXT,
      budget INTEGER,
      manager_id INTEGER,
      location TEXT
    );
    """)
    
    # Create employees table with department_id foreign key
    cursor.execute("""
    CREATE TABLE employees (
      id INTEGER PRIMARY KEY,
      name TEXT,
      department TEXT,
      role TEXT,
      salary INTEGER,
      location TEXT,
      department_id INTEGER,
      FOREIGN KEY (department_id) REFERENCES departments(id)
    );
    """)
    
    # Seed departments (without manager_id first, will update after employees exist)
    cursor.execute("""
    INSERT INTO departments (id, name, budget, location) VALUES
    (1, 'Engineering', 500000, 'TX'),
    (2, 'Sales', 300000, 'CA'),
    (3, 'HR', 200000, 'NY');
    """)
    
    # Seed employees with department_id references
    cursor.execute("""
    INSERT INTO employees VALUES
    (1, 'Alice', 'Engineering', 'Software Engineer', 120000, 'NY', 1),
    (2, 'Bob', 'Sales', 'Account Manager', 90000, 'CA', 2),
    (3, 'Charlie', 'Engineering', 'DevOps Engineer', 130000, 'TX', 1),
    (4, 'Diana', 'HR', 'HR Manager', 85000, 'NY', 3),
    (5, 'Evan', 'Engineering', 'Data Scientist', 140000, 'CA', 1);
    """)
    
    # Update departments with manager_id now that employees exist
    cursor.execute("""
    UPDATE departments SET manager_id = 3 WHERE id = 1;
    """)
    cursor.execute("""
    UPDATE departments SET manager_id = 2 WHERE id = 2;
    """)
    cursor.execute("""
    UPDATE departments SET manager_id = 4 WHERE id = 3;
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized and seeded with employees and departments tables.")

def execute_read_query(query: str):
    # Basic safety check: ensure strictly read-only by checking for forbidden keywords (naive but functional for POC)
    forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "REPLACE"]
    if any(keyword in query.upper() for keyword in forbidden_keywords):
        return {"error": "Only SELECT queries are allowed."}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        # Convert rows to dicts
        result = [dict(row) for row in rows]
        conn.close()
        return {"data": result}
    except Exception as e:
        return {"error": str(e)}

def get_schema():
    """Get schema information for all tables in the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        schema_info = []
        for table_row in tables:
            table_name = table_row['name']
            
            # Get column information for each table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            column_details = []
            for col in columns:
                column_details.append({
                    "name": col['name'],
                    "type": col['type'],
                    "nullable": not col['notnull'],
                    "primary_key": bool(col['pk'])
                })
            
            schema_info.append({
                "table_name": table_name,
                "columns": column_details
            })
        
        conn.close()
        return {"schema": schema_info}
    except Exception as e:
        return {"error": str(e)}

def get_table_data(table_name: str):
    """Get all data from a specific table."""
    # Validate table name to prevent SQL injection
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
        if not cursor.fetchone():
            conn.close()
            return {"error": f"Table '{table_name}' does not exist."}
        
        # Fetch all data from the table
        cursor.execute(f"SELECT * FROM {table_name};")
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        return {"data": result, "table_name": table_name}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    init_db()
