"""
Database abstraction layer supporting both SQLite (with fake data) and PostgreSQL (dynamic schema).

Uses SQLAlchemy for database abstraction and provides dynamic schema detection.
"""

import os
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

# Configuration
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite").lower()  # sqlite or postgresql

# SQLite Configuration
SQLITE_DB_PATH = "backend/chat_data.db"

# PostgreSQL Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mydb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# Global engine and session
engine = None
SessionLocal = None
Base = declarative_base()

# Cache for schema information
_schema_cache = None


def get_database_url():
    """Get the database URL based on DATABASE_TYPE."""
    if DATABASE_TYPE == "postgresql":
        return f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    else:
        # Default to SQLite
        return f"sqlite:///{SQLITE_DB_PATH}"


def init_database_engine():
    """Initialize the database engine and session factory."""
    global engine, SessionLocal
    
    database_url = get_database_url()
    print(f"Initializing database: {DATABASE_TYPE} ({database_url.split('@')[-1] if '@' in database_url else database_url})")
    
    if DATABASE_TYPE == "postgresql":
        engine = create_engine(database_url, poolclass=NullPool, echo=False)
    else:
        engine = create_engine(database_url, connect_args={"check_same_thread": False}, echo=False)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Initialize SQLite with fake data if needed
    if DATABASE_TYPE == "sqlite":
        init_sqlite_fake_data()


def init_sqlite_fake_data():
    """Initialize SQLite database with fake employee/department data."""
    global engine
    
    # Check if database file exists and has tables
    if os.path.exists(SQLITE_DB_PATH):
        inspector = inspect(engine)
        if inspector.get_table_names():
            print("SQLite database already exists with data. Skipping initialization.")
            return
    
    print("Initializing SQLite with fake employee/department data...")
    
    metadata = MetaData()
    
    # Create departments table
    departments = Table('departments', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String),
        Column('budget', Integer),
        Column('manager_id', Integer),
        Column('location', String)
    )
    
    # Create employees table
    employees = Table('employees', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String),
        Column('department', String),
        Column('role', String),
        Column('salary', Integer),
        Column('location', String),
        Column('department_id', Integer, ForeignKey('departments.id'))
    )
    
    # Create tables
    metadata.create_all(engine)
    
    # Seed data
    with engine.connect() as conn:
        # Insert departments
        conn.execute(departments.insert(), [
            {"id": 1, "name": "Engineering", "budget": 500000, "location": "TX", "manager_id": None},
            {"id": 2, "name": "Sales", "budget": 300000, "location": "CA", "manager_id": None},
            {"id": 3, "name": "HR", "budget": 200000, "location": "NY", "manager_id": None}
        ])
        
        # Insert employees
        conn.execute(employees.insert(), [
            {"id": 1, "name": "Alice", "department": "Engineering", "role": "Software Engineer", "salary": 120000, "location": "NY", "department_id": 1},
            {"id": 2, "name": "Bob", "department": "Sales", "role": "Account Manager", "salary": 90000, "location": "CA", "department_id": 2},
            {"id": 3, "name": "Charlie", "department": "Engineering", "role": "DevOps Engineer", "salary": 130000, "location": "TX", "department_id": 1},
            {"id": 4, "name": "Diana", "department": "HR", "role": "HR Manager", "salary": 85000, "location": "NY", "department_id": 3},
            {"id": 5, "name": "Evan", "department": "Engineering", "role": "Data Scientist", "salary": 140000, "location": "CA", "department_id": 1}
        ])
        
        # Update departments with managers
        conn.execute(departments.update().where(departments.c.id == 1).values(manager_id=3))
        conn.execute(departments.update().where(departments.c.id == 2).values(manager_id=2))
        conn.execute(departments.update().where(departments.c.id == 3).values(manager_id=4))
        
        conn.commit()
    
    print("SQLite database initialized with fake data.")


def detect_schema():
    """
    Detect database schema dynamically using SQLAlchemy.
    Returns structured schema information including tables, columns, types, and relationships.
    """
    global engine, _schema_cache
    
    if engine is None:
        init_database_engine()
    
    print("Detecting database schema...")
    
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    if not table_names:
        print("Warning: No tables found in database.")
        return {"tables": [], "relationships": []}
    
    schema_info = {
        "tables": [],
        "relationships": []
    }
    
    for table_name in table_names:
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        
        # Format columns
        column_info = []
        for col in columns:
            column_info.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "primary_key": col["name"] in pk_constraint.get("constrained_columns", [])
            })
        
        schema_info["tables"].append({
            "table_name": table_name,
            "columns": column_info
        })
        
        # Extract foreign key relationships
        for fk in foreign_keys:
            for i, col in enumerate(fk["constrained_columns"]):
                schema_info["relationships"].append({
                    "from_table": table_name,
                    "from_column": col,
                    "to_table": fk["referred_table"],
                    "to_column": fk["referred_columns"][i] if i < len(fk["referred_columns"]) else "id"
                })
    
    _schema_cache = schema_info
    print(f"Schema detected: {len(schema_info['tables'])} tables, {len(schema_info['relationships'])} relationships")
    
    return schema_info


def format_schema_for_llm(schema_info):
    """
    Format detected schema into a string suitable for LLM system instructions.
    Generates CREATE TABLE statements and relationship descriptions.
    """
    if not schema_info or not schema_info.get("tables"):
        return "No database schema available."
    
    output = []
    
    # Add database type info
    output.append(f"The database is {DATABASE_TYPE.upper()}.")
    table_names = ', '.join([f"`{t['table_name']}`" for t in schema_info['tables']])
    output.append(f"The database contains {len(schema_info['tables'])} table(s): {table_names}.")
    output.append("")
    output.append("SCHEMAS:")
    output.append("")
    
    # Generate CREATE TABLE statements
    for table in schema_info["tables"]:
        output.append(f"CREATE TABLE {table['table_name']} (")
        
        column_lines = []
        for col in table["columns"]:
            line = f"  {col['name']} {col['type']}"
            if col["primary_key"]:
                line += " PRIMARY KEY"
            if not col["nullable"]:
                line += " NOT NULL"
            column_lines.append(line)
        
        output.append(",\n".join(column_lines))
        output.append(");")
        output.append("")
    
    # Add relationships section
    if schema_info.get("relationships"):
        output.append("RELATIONSHIPS:")
        for rel in schema_info["relationships"]:
            output.append(f"- {rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}")
        output.append("")
    
    return "\n".join(output)


def execute_read_query(query: str):
    """Execute a read-only SQL query safely."""
    global engine
    
    if engine is None:
        init_database_engine()
    
    # Basic safety check: ensure strictly read-only
    forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "REPLACE", "CREATE"]
    if any(keyword in query.upper() for keyword in forbidden_keywords):
        return {"error": "Only SELECT queries are allowed."}
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            
            # Convert to list of dicts
            if rows:
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
            else:
                data = []
            
            return {"data": data}
    except Exception as e:
        return {"error": str(e)}


def get_schema():
    """Get schema information for all tables (API-compatible with old interface)."""
    global _schema_cache
    
    try:
        if _schema_cache is None:
            detect_schema()
        
        # Convert to old format for compatibility
        schema_list = []
        if _schema_cache:
            for table in _schema_cache.get("tables", []):
                schema_list.append({
                    "table_name": table["table_name"],
                    "columns": table["columns"]
                })
        
        return {"schema": schema_list}
    except Exception as e:
        return {"error": str(e)}


def get_table_data(table_name: str):
    """Get all data from a specific table."""
    global engine
    
    if engine is None:
        init_database_engine()
    
    try:
        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            return {"error": f"Table '{table_name}' does not exist."}
        
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()
            
            if rows:
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
            else:
                data = []
            
            return {"data": data, "table_name": table_name}
    except Exception as e:
        return {"error": str(e)}


def refresh_schema():
    """
    Refresh the cached schema by re-detecting it.
    Returns the updated schema information.
    """
    global _schema_cache
    _schema_cache = None
    return detect_schema()


# Initialize on module import
init_database_engine()
