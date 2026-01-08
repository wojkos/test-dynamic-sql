import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    # Just a warning, main.py might handle this or it will fail at runtime
    print("Warning: GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=API_KEY)

# Use a model that is good at code/logic. Gemini 1.5 Flash is usually good for this speed/cost.
MODEL_NAME = 'gemini-2.0-flash'

SYSTEM_INSTRUCTION = """You are an assistant that generates read-only SQL queries for a SQLite database.
The database contains two tables: `employees` and `departments`.

SCHEMAS:

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

CREATE TABLE departments (
  id INTEGER PRIMARY KEY,
  name TEXT,
  budget INTEGER,
  manager_id INTEGER,
  location TEXT,
  FOREIGN KEY (manager_id) REFERENCES employees(id)
);

RELATIONSHIPS:
- employees.department_id → departments.id (each employee belongs to a department)
- departments.manager_id → employees.id (each department has a manager who is an employee)
- Note: employees.department column contains the department name (text), while department_id is the foreign key

RULES:
1. Only generate SELECT queries. Do not generate INSERT, UPDATE, DELETE, DROP, etc.
2. Return only the raw SQL query. Do not wrap it in markdown block quotes (e.g. ```sql ... ```).
3. Use JOINs when the question requires data from both tables.
4. Use appropriate JOIN types (INNER JOIN, LEFT JOIN, etc.) based on the question.
5. Use table aliases (e.g., 'e' for employees, 'd' for departments) for readability in JOIN queries.
6. For simple questions about one table, query only that table.
7. If the user asks for something outside the scope of the data, try to interpret it as best as possible or return a generic SELECT * if unsure but safe.

EXAMPLES:
- "Show all employees" → SELECT * FROM employees
- "What's the Engineering budget?" → SELECT budget FROM departments WHERE name='Engineering'
- "Show employees with their department budgets" → SELECT e.*, d.budget FROM employees e INNER JOIN departments d ON e.department_id = d.id
- "Who manages each department?" → SELECT d.name AS department, e.name AS manager FROM departments d INNER JOIN employees e ON d.manager_id = e.id
"""

model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_INSTRUCTION)

def generate_sql(question: str) -> str:
    """
    Generates a SQL query from a natural language question using Gemini.
    """
    # Mock Mode removed as per user request.
    if not API_KEY:
         print("Warning: API Key is missing, but Mock Mode is disabled. Calls will fail.")

    prompt = f"User question: {question}\n\nGenerate a SQLite SELECT query only."
    
    try:
        response = model.generate_content(prompt)
        sql = response.text.strip()
        
        # Cleanup: remove markdown code blocks if the model puts them in
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
            
        return sql.strip()
    except Exception as e:
        print(f"Error generating SQL: {e}")
        return "SELECT * FROM employees LIMIT 0;" # Safe fallback or error indicator
