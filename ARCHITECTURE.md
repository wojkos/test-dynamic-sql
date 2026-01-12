# Chat-to-Data Architecture Document

This document outlines the Proof of Concept (POC) architecture for the Chat-to-Data application, focusing on the integration of the Model Context Protocol (MCP) and **Dynamic SQL Generation**.

---

## 🎯 Core Objective
The primary goal of this POC is to demonstrate that an LLM can interact with **any structured database** through an MCP server using **zero hardcoded SQL queries or schema definitions**. The system automatically detects database structure at startup and dynamically generates SQL based on natural language prompts. Supports both SQLite (with auto-initialized sample data) and PostgreSQL (with runtime schema introspection).

---

## 🌐 System Context
Shows the system's relationship with external users, API providers, and databases.

<div align="center">
  <img src="docs/images/context_diagram.png" width="500" alt="System Context Diagram" style="border-radius: 8px; border: 1px solid #ddd;">
</div>

<details>
<summary>View Mermaid Source</summary>

```mermaid
graph LR
    User([Business User]) -- "Natural Language" --> App[Chat-to-Data App]
    App -- "Prompts & Context" --> LLM((Gemini/OpenAI API))
    LLM -- "SQL & Chat" --> App
    App -- "Queries" --> DB[(SQLite or PostgreSQL)]
    DB -- "Schema Detection" --> App
```
</details>

---

## 🏗️ Technical Architecture
Detailed view of the internal components with **dynamic schema detection** and the **MCP boundary**.

<div align="center">
  <img src="docs/images/system_diagram.png" width="700" alt="System Architecture Diagram" style="border-radius: 8px; border: 1px solid #ddd;">
</div>

<details>
<summary>View Mermaid Source</summary>

```mermaid
graph TD
    User([User]) --> Frontend[Frontend UI - Vanilla JS]
    Frontend --> BackendClient[FastAPI Backend - MCP Client]
    
    subgraph "Orchestration Layer"
        BackendClient --> GeminiOrch[Gemini/OpenAI - Orchestrator]
        GeminiOrch -- "Decides to call tool" --> MCPServer[FastMCP Server]
    end
    
    subgraph "MCP Server - Data Access Layer"
        MCPServer -- "rephrased_question" --> SQLGen[LLM SQL Generator]
        SQLGen -- "Dynamic SQL" --> DBExec[SQLAlchemy Executor]
        DBExec --> Database[(SQLite/PostgreSQL)]
    end
    
    subgraph "Schema Detection"
        Database -- "Introspect" --> SchemaDetector[SQLAlchemy Inspector]
        SchemaDetector -- "Tables, Columns, FKs" --> LLMInit[LLM Initialization]
        LLMInit -- "Dynamic System Prompt" --> SQLGen
    end
    
    Database --> DBExec
    DBExec -- "Query Results" --> MCPServer
    MCPServer -- "Protocol Response" --> BackendClient
    BackendClient --> GeminiOrch
    GeminiOrch -- "Natural Language Answer" --> Frontend
```
</details>

---

## 📊 Data Model
The system **automatically detects** the database schema at startup using SQLAlchemy introspection. Below is an example schema (SQLite default with employee/department sample data).

**Note:** When using PostgreSQL, the system will detect YOUR actual schema and generate appropriate LLM prompts for whatever tables exist in your database.

<div align="center">
  <img src="docs/images/er_diagram.png" width="450" alt="Database ER Diagram" style="border-radius: 8px; border: 1px solid #ddd;">
</div>

<details>
<summary>View Mermaid Source (Example: Default SQLite Schema)</summary>

```mermaid
erDiagram
    DEPARTMENTS ||--o{ EMPLOYEES : "has"
    EMPLOYEES ||--o| DEPARTMENTS : "manages"

    EMPLOYEES {
        int id PK
        string name
        string department
        string role
        int salary
        string location
        int department_id FK
    }

    DEPARTMENTS {
        int id PK
        string name
        int budget
        int manager_id FK
        string location
    }
```
</details>

---

### Independent Multi-Server Registry
The system is designed to treat MCP servers as modular, independent units.
- **Registry**: The `MCP_SERVER_REGISTRY` in `main.py` acts as a central list of local or remote MCP URLs.
- **Aggregated Discovery**: On startup, the client polls *every* server in the registry, aggregating their tools into a single logical "toolbox" for Gemini.
- **Dynamic Routing**: The system maintains a `TOOL_TO_SERVER_MAP`. When Gemini requests a tool call, the backend automatically routes the request to the specific server that provides that tool.
- **Horizontal Scaling**: You can add specialized servers (e.g., Google Search, Slack, GitHub) simply by adding their endpoint URL to the registry.

---

## 🔄 Dynamic SQL Flow
The system generates required SQL on-the-fly, mapping natural language to the schema without any pre-defined query strings.

### Execution Sequence

<div align="center">
  <img src="docs/images/sequence_diagram_refined.png" width="800" alt="Query Processing Flow Sequence Diagram" style="border-radius: 8px; border: 1px solid #ddd;">
</div>

<details>
<summary>View Mermaid Source</summary>

```mermaid
sequenceDiagram
    U->>F: "Show me the manager of Engineering"
    F->>B: POST /mcp-chat
    Note over B,G: PHASE 1: DECISION
    B->>G: User Prompt + Tool Definitions (The "Menu")
    G->>G: Analysis: Intent requires database access
    G-->>B: DECISION: Call tool "query_database(question=...)"
    
    Note over B,D: PHASE 2: EXECUTION (Inside MCP Boundary)
    B->>S: MCP.call_tool("query_database", args)
    S->>L: generate_sql("Who is the manager...")
    L-->>S: "SELECT e.name FROM employees..."
    S->>D: Execute Dynamic SQL
    D-->>S: Raw Data: {"name": "Alice"}
    S-->>B: Protocol Response (JSON Results)
    
    Note over B,G: PHASE 3: SYNTHESIS
    B->>G: "Tool result provided: Alice"
    G-->>B: Final Answer: "The manager... is Alice."
    B->>F: Response to UI
    F->>U: Display Answer
```
</details>

---

## 🧩 Key Components

| Component | Responsibility | Technology |
| :--- | :--- | :--- |
| **Frontend** | Interactive UI and result visualization. | HTML, CSS, Vanilla JS |
| **MCP Client** | FastAPI backend orchestrating LLM tool calls. | Python, FastAPI, FastMCP |
| **MCP Server** | Encapsulates database tools and SQL generation (generic). | Python, FastMCP Server |
| **Schema Detector** | Introspects database structure and generates LLM prompts. | SQLAlchemy Inspector |
| **SQL Generator** | Translates text to SQL queries via dynamic schema context. | Gemini 2.0 Flash or GPT-4o-mini |
| **Database** | Stores data (auto-initialized SQLite or existing PostgreSQL). | SQLite or PostgreSQL |
| **ORM Layer** | Database abstraction and query execution. | SQLAlchemy |

---

## 🛡️ Security & Constraints
- **Read-Only**: SQL generation is restricted to `SELECT` operations only.
- **Protocol Isolation**: LLM access is filtered through enforced MCP tool boundaries.
- **Query Sanitization**: Backend validation prevents execution of destructive commands.
