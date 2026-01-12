from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import time
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
from fastmcp import Client
import openai

# Import database functions
from backend.database import detect_schema, format_schema_for_llm, execute_read_query, get_schema, get_table_data, refresh_schema
from backend.llm_service import initialize_llm_with_schema, generate_sql

# Load environment variables
load_dotenv()

# Check for API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if GEMINI_API_KEY:
    provider = "gemini"
    API_KEY = GEMINI_API_KEY
    MODEL_NAME = 'gemini-2.0-flash'
    genai.configure(api_key=API_KEY)
elif OPENAI_API_KEY:
    provider = "openai"
    API_KEY = OPENAI_API_KEY
    MODEL_NAME = 'gpt-4o-mini'
    client = openai.OpenAI(api_key=API_KEY)
else:
    provider = None
    print("Warning: Neither GEMINI_API_KEY nor OPENAI_API_KEY found.")

app = FastAPI()

# Enable CORS for development convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# SESSION MANAGEMENT FOR MCP CHAT
# ============================================================
# Store chat sessions: session_id -> {"chat": ChatSession, "last_accessed": timestamp}
chat_sessions: dict = {}
SESSION_TIMEOUT = 3600  # 1 hour timeout for inactive sessions

def cleanup_old_sessions():
    """Remove sessions older than SESSION_TIMEOUT."""
    current_time = time.time()
    expired = [sid for sid, data in chat_sessions.items() 
               if current_time - data["last_accessed"] > SESSION_TIMEOUT]
    for sid in expired:
        del chat_sessions[sid]

def get_or_create_chat_session(session_id: str):
    """Get existing chat session or create a new one."""
    cleanup_old_sessions()
    
    # Ensure model is initialized
    if mcp_chat_model is None:
        raise HTTPException(status_code=503, detail="MCP Chat model is initializing. Please try again in a few seconds.")

    if session_id not in chat_sessions:
        # Create new chat session
        if mcp_chat_provider == "gemini":
            chat_sessions[session_id] = {
                "chat": mcp_chat_model.start_chat(),
                "last_accessed": time.time()
            }
        elif mcp_chat_provider == "openai":
            chat_sessions[session_id] = {
                "messages": [{"role": "system", "content": mcp_chat_model["system_instruction"]}],
                "last_accessed": time.time()
            }
    else:
        # Update last accessed time
        chat_sessions[session_id]["last_accessed"] = time.time()
    
    return chat_sessions[session_id]

# Global variables (initialized in startup)
mcp_chat_provider = None
mcp_chat_model = None

# Startup configuration
@app.on_event("startup")
async def startup_event():
    global mcp_chat_provider, mcp_chat_model
    mcp_chat_provider = provider
    
    # Initialize database and detect schema
    print("Initializing database and detecting schema...")
    schema_info = detect_schema()
    schema_text = format_schema_for_llm(schema_info)
    
    # Initialize LLM with dynamic schema
    print("Initializing LLM with dynamic schema...")
    initialize_llm_with_schema(schema_text)
    
    # Aggregated tool discovery from all independent servers
    try:
        print("Discovering tools from all registered MCP servers...")
        mcp_tools = await get_tools_from_all_mcp_servers()
        
        if provider == "gemini":
            mcp_chat_model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                system_instruction=MCP_CHAT_SYSTEM_INSTRUCTION,
                tools=[mcp_tools] if mcp_tools.function_declarations else []
            )
        elif provider == "openai":
            # For OpenAI, store the tools for later use
            mcp_chat_model = {
                "client": client,
                "model": MODEL_NAME,
                "tools": mcp_tools.function_declarations if mcp_tools else [],
                "system_instruction": MCP_CHAT_SYSTEM_INSTRUCTION
            }
        print(f"MCP Chat model initialized with {len(mcp_tools.function_declarations) if mcp_tools else 0} tools from aggregated registry.")
    except Exception as e:
        print(f"Failed to discover MCP tools: {e}")
        if provider == "gemini":
            mcp_chat_model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                system_instruction=MCP_CHAT_SYSTEM_INSTRUCTION
            )
        elif provider == "openai":
            mcp_chat_model = {
                "client": client,
                "model": MODEL_NAME,
                "tools": [],
                "system_instruction": MCP_CHAT_SYSTEM_INSTRUCTION
            }

class QueryRequest(BaseModel):
    question: str

class MCPChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

# ============================================================
# MCP CHAT ENDPOINT - LLM decides whether to use MCP tools
# ============================================================

# ============================================================
# DYNAMIC MCP TOOL DISCOVERY & MULTI-SERVER REGISTRY
# ============================================================

# Registry of independent MCP servers (can be local or remote URLs)
MCP_SERVER_REGISTRY = [
    "http://127.0.0.1:8001/sse",
    # Add external servers here, e.g., "https://mcp.external-api.com/sse"
]

# Map to store which tool belongs to which server URL for dynamic routing
TOOL_TO_SERVER_MAP = {}

def convert_json_schema_to_gemini_schema(json_schema: dict):
    """Recursively convert JSON Schema to genai.protos.Schema format."""
    type_map = {
        "string": genai.protos.Type.STRING,
        "number": genai.protos.Type.NUMBER,
        "integer": genai.protos.Type.INTEGER,
        "boolean": genai.protos.Type.BOOLEAN,
        "object": genai.protos.Type.OBJECT,
        "array": genai.protos.Type.ARRAY,
    }
    
    schema_type = type_map.get(json_schema.get("type", "object"), genai.protos.Type.OBJECT)
    
    properties = {}
    if "properties" in json_schema:
        for key, value in json_schema["properties"].items():
            properties[key] = convert_json_schema_to_gemini_schema(value)
            
    return genai.protos.Schema(
        type=schema_type,
        properties=properties,
        required=json_schema.get("required", []),
        description=json_schema.get("description", "")
    )

async def get_tools_from_all_mcp_servers():
    """Fetch tool definitions from all registered MCP servers and aggregate them."""
    global TOOL_TO_SERVER_MAP
    TOOL_TO_SERVER_MAP = {} # Reset map
    
    all_function_declarations = []
    
    for server_url in MCP_SERVER_REGISTRY:
        try:
            print(f"Connecting to MCP server at {server_url}...")
            async with Client(server_url) as mcp_client:
                mcp_tools_list = await mcp_client.list_tools()
                
                for tool in mcp_tools_list:
                    # Register tool-to-server mapping for routing
                    TOOL_TO_SERVER_MAP[tool.name] = server_url
                    
                    # Convert MCP tool to Gemini FunctionDeclaration
                    gemini_params = convert_json_schema_to_gemini_schema(tool.inputSchema)
                    decl = genai.protos.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=gemini_params
                    )
                    all_function_declarations.append(decl)
            print(f"Discovered {len(mcp_tools_list)} tools from {server_url}")
        except Exception as e:
            print(f"Failed to connect to MCP server at {server_url}: {e}")
            
    return genai.protos.Tool(function_declarations=all_function_declarations)

# System instruction for the MCP chat
MCP_CHAT_SYSTEM_INSTRUCTION = """You are a helpful assistant that can answer general questions and also query complex datasets through independent MCP servers.

Multiple MCP servers are connected to this interface. Each server provides specialized tools.

CRITICAL FOR FOLLOW-UP QUESTIONS:
If the user asks a follow-up question that refers to previous results or context (e.g., "who is that?", "how many of them?", "show their roles"), you MUST rephrase the user's request into a COMPREHENSIVE and SELF-CONTAINED natural language query for the tool. Use the conversation history to resolve all pronouns and ambiguous references before calling the tool.

Always be helpful and concise in your responses."""

@app.post("/mcp-chat")
async def mcp_chat(request: MCPChatRequest):
    """
    MCP Chat endpoint - LLM decides whether to use MCP tools based on user intent.
    
    Flow:
    1. Send user message to LLM with tool definitions (with session persistence)
    2. If LLM calls a tool, invoke the MCP server
    3. Return tool results back to LLM for final response
    4. If no tool needed, return direct response
    """
    try:
        user_message = request.message
        session_id = request.session_id
        
        # Generate session ID if not provided
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
        
        # Step 1: Get or create chat session for context persistence
        session_data = get_or_create_chat_session(session_id)
        
        if mcp_chat_provider == "gemini":
            chat = session_data["chat"]
            response = chat.send_message(user_message)
            
            # Check if Gemini wants to call a function
            if response.candidates[0].content.parts:
                first_part = response.candidates[0].content.parts[0]
                
                # Check if it's a function call
                if hasattr(first_part, 'function_call') and first_part.function_call.name:
                    function_call = first_part.function_call
                    tool_name = function_call.name
                    tool_args = dict(function_call.args) if function_call.args else {}
                    
                    # Step 2: Dynamically route tool call to the correct MCP server
                    mcp_result = None
                    server_url = TOOL_TO_SERVER_MAP.get(tool_name)
                    
                    if not server_url:
                        mcp_result_data = {"error": f"No server registered for tool: {tool_name}"}
                    else:
                        try:
                            async with Client(server_url) as mcp_client:
                                mcp_result = await mcp_client.call_tool(tool_name, tool_args)
                                # Extract the result data
                                if mcp_result and hasattr(mcp_result, 'content'):
                                    # Parse the content from MCP response
                                    result_text = mcp_result.content[0].text if mcp_result.content else "{}"
                                    mcp_result_data = json.loads(result_text)
                                else:
                                    mcp_result_data = {"error": "No result from MCP server"}
                        except Exception as mcp_error:
                            mcp_result_data = {"error": f"MCP server error ({server_url}): {str(mcp_error)}"}
                    
                    # Step 3: Send tool result back to Gemini for final response
                    from google.generativeai.types import content_types
                    
                    function_response = content_types.to_content({
                        "parts": [{
                            "function_response": {
                                "name": tool_name,
                                "response": {"result": mcp_result_data}
                            }
                        }]
                    })
                    
                    final_response = chat.send_message(function_response)
                    final_text = final_response.text if hasattr(final_response, 'text') else str(final_response)
                    
                    return {
                        "type": "mcp_tool",
                        "session_id": session_id,
                        "tool_used": tool_name,
                        "tool_args": tool_args,
                        "tool_result": mcp_result_data,
                        "response": final_text
                    }
                
                # No function call - direct text response
                response_text = response.text if hasattr(response, 'text') else str(response)
                return {
                    "type": "direct",
                    "session_id": session_id,
                    "tool_used": None,
                    "response": response_text
                }
        
        elif mcp_chat_provider == "openai":
            # For OpenAI, simple chat without tools for now
            messages = session_data["messages"]
            messages.append({"role": "user", "content": user_message})
            
            try:
                response = mcp_chat_model["client"].chat.completions.create(
                    model=mcp_chat_model["model"],
                    messages=messages
                )
                assistant_message = response.choices[0].message.content
                messages.append({"role": "assistant", "content": assistant_message})
                
                return {
                    "type": "direct",
                    "session_id": session_id,
                    "tool_used": None,
                    "response": assistant_message
                }
            except Exception as e:
                return {
                    "type": "error",
                    "session_id": session_id,
                    "response": f"Error with OpenAI: {str(e)}"
                }
        
        # Fallback response
        return {
            "type": "direct",
            "session_id": session_id,
            "tool_used": None,
            "response": "I'm not sure how to respond to that."
        }
    
    except Exception as e:
        return {
            "type": "error",
            "session_id": session_id if 'session_id' in locals() else None,
            "response": f"Chat error: {str(e)}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP Chat error: {str(e)}")

@app.delete("/mcp-chat/session/{session_id}")
async def clear_chat_session(session_id: str):
    """Clear a chat session to start fresh."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"message": "Session cleared", "session_id": session_id}
    return {"message": "Session not found", "session_id": session_id}

# ============================================================
# EXISTING ENDPOINTS (unchanged)
# ============================================================

@app.post("/query")
async def query_database(request: QueryRequest):
    question = request.question
    if not question:
        raise HTTPException(status_code=400, detail="No question provided")

    # 1. Generate SQL
    generated_sql_query = generate_sql(question)
    
    # 2. Execute SQL
    result = execute_read_query(generated_sql_query)
    
    response = {
        "sql": generated_sql_query,
        "data": result.get("data", []),
        "error": result.get("error")
    }
    
    return response

@app.get("/schema")
async def get_database_schema():
    """Get schema information for all tables."""
    result = get_schema()
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/internal/refresh-schema")
async def refresh_database_schema():
    """
    Internal endpoint to refresh the database schema and re-initialize the LLM.
    This is automatically called on startup and can be called manually when database structure changes.
    """
    try:
        print("Refreshing database schema...")
        schema_info = refresh_schema()
        schema_text = format_schema_for_llm(schema_info)
        
        # Re-initialize LLM with updated schema
        print("Re-initializing LLM with updated schema...")
        initialize_llm_with_schema(schema_text)
        
        return {
            "success": True,
            "message": "Schema refreshed successfully",
            "tables": len(schema_info.get("tables", [])),
            "relationships": len(schema_info.get("relationships", []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh schema: {str(e)}")

@app.get("/tables/{table_name}/data")
async def get_table_raw_data(table_name: str):
    """Get all raw data from a specific table."""
    result = get_table_data(table_name)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result

# Mount frontend directory to serve static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

