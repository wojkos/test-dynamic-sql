import os
import google.generativeai as genai
from dotenv import load_dotenv
import openai

load_dotenv()

# Global variables for provider and models
provider = None
API_KEY = None
MODEL_NAME = None
model = None
client = None
SYSTEM_INSTRUCTION = None

def initialize_llm_with_schema(schema_text: str):
    """
    Initialize the LLM provider (Gemini or OpenAI) with dynamic schema.
    This should be called after database schema is detected.
    """
    global provider, API_KEY, MODEL_NAME, model, client, SYSTEM_INSTRUCTION
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Build dynamic system instruction
    SYSTEM_INSTRUCTION = f"""You are an assistant that generates read-only SQL queries for a database.

{schema_text}

RULES:
1. Only generate SELECT queries. Do not generate INSERT, UPDATE, DELETE, DROP, etc.
2. Return only the raw SQL query. Do not wrap it in markdown block quotes (e.g. ```sql ... ```).
3. Use JOINs when the question requires data from multiple tables.
4. Use appropriate JOIN types (INNER JOIN, LEFT JOIN, etc.) based on the question.
5. Use table aliases for readability in JOIN queries.
6. For simple questions about one table, query only that table.
7. If the user asks for something outside the scope of the data, try to interpret it as best as possible or return a safe fallback query.
8. Pay attention to the exact table and column names from the schema above.
"""
    
    if GEMINI_API_KEY:
        provider = "gemini"
        API_KEY = GEMINI_API_KEY
        MODEL_NAME = 'gemini-2.0-flash'
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_INSTRUCTION)
        print(f"LLM initialized: Gemini ({MODEL_NAME})")
    elif OPENAI_API_KEY:
        provider = "openai"
        API_KEY = OPENAI_API_KEY
        MODEL_NAME = 'gpt-4o-mini'
        client = openai.OpenAI(api_key=API_KEY)
        print(f"LLM initialized: OpenAI ({MODEL_NAME})")
    else:
        provider = None
        print("Warning: Neither GEMINI_API_KEY nor OPENAI_API_KEY found in environment variables.")
    
    return provider is not None

def generate_sql(question: str) -> str:
    """
    Generates a SQL query from a natural language question using Gemini or OpenAI.
    """
    global provider, model, client, MODEL_NAME, SYSTEM_INSTRUCTION
    
    if provider is None or SYSTEM_INSTRUCTION is None:
        print("Error: LLM not initialized. Call initialize_llm_with_schema() first.")
        return "SELECT 1 LIMIT 0;"  # Safe fallback
    
    if provider == "gemini":
        prompt = f"User question: {question}\n\nGenerate a SELECT query only."
        
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
            print(f"Error generating SQL with Gemini: {e}")
            return "SELECT 1 LIMIT 0;" # Safe fallback or error indicator
    elif provider == "openai":
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": f"User question: {question}\n\nGenerate a SELECT query only."}
                ]
            )
            sql = response.choices[0].message.content.strip()
            
            # Cleanup: remove markdown code blocks if the model puts them in
            if sql.startswith("```sql"):
                sql = sql[6:]
            if sql.startswith("```"):
                sql = sql[3:]
            if sql.endswith("```"):
                sql = sql[:-3]
                
            return sql.strip()
        except Exception as e:
            print(f"Error generating SQL with OpenAI: {e}")
            return "SELECT 1 LIMIT 0;" # Safe fallback or error indicator
    else:
        print("No API key available for either provider.")
        return "SELECT 1 LIMIT 0;"
