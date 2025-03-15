import os
import json
import psycopg2
import requests
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from typing import List, Optional
from psycopg2.extras import RealDictCursor
import re

# ✅ Load Environment Variables
load_dotenv()

# ✅ Define State Schema
class ChatState(BaseModel):
    messages: List[HumanMessage]
    user_email: str
    intent: str = "general"
    response: str = ""
    name: Optional[str] = None
    requested_field: Optional[str] = None
    userData: Optional[dict] = None  

# ✅ PostgreSQL Connection
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", 5432),
}

# ✅ Load HR Policies
try:
    with open("policies.json", "r", encoding="utf-8") as file:
        policies = json.load(file)
except Exception as e:
    print(f"❌ Failed to load policies.json: {e}")
    policies = {}

# ✅ Ollama Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

# 🔹 1. Classify Intent
def classify_intent(state: ChatState):
    messages = state.messages
    message = messages[-1].content if messages else ""

    if not message:
        return state.copy(update={"intent": "general"})

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": f"""
            Classify this message into one of these categories:
            - 'user_details' (if the user asks about their name, email, phone number, or address)
            - 'leave_balance' (if the user asks about their remaining leave balance)
            - 'attendance' (if the user asks about their attendance records)
            - 'paid_leave' (if the user asks about their paid leave records)
            - 'hr_policy' (if the user asks about HR policies)
            - 'general' (for anything else)

            Only return the category name without extra text.

            Message: '{message}'
            """,
            "stream": False,
        })
        
        response_json = response.json()
        intent = response_json.get("response", "general").strip()
        intent = intent.replace("'", "").replace('"', '')  # Ensure clean output
        print(f"✅ Classified intent: {intent}")
        return state.copy(update={"intent": intent})

    except Exception as e:
        print(f"❌ Error classifying intent: {e}")
        return state.copy(update={"intent": "general"})

# 🔹 2. Fetch Database Schema
def get_database_schema():
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        c.relname AS table_name,
                        a.attname AS column_name,
                        t.typname AS data_type
                    FROM pg_catalog.pg_class c
                    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                    JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid
                    JOIN pg_catalog.pg_type t ON a.atttypid = t.oid
                    WHERE n.nspname = 'public' 
                    AND a.attnum > 0 
                    AND NOT a.attisdropped;
                """)
                return cursor.fetchall()
    except Exception as e:
        print(f"❌ Error fetching schema: {e}")
        return []

def generate_sql_query(state: ChatState):
    """Generates an SQL query using Llama 3 (via Ollama) with schema awareness,
    ensuring email filtering except when retrieving all employees."""

    message = state.messages[-1].content if state.messages else ""

    schema_info = get_database_schema()
    if not schema_info:
        return state.copy(update={"response": "Database schema unavailable."})

    # 🔹 Extract schema details
    table_columns = {}
    for row in schema_info:
        table_name = row["table_name"]
        column_name = row["column_name"]
        if table_name not in table_columns:
            table_columns[table_name] = set()
        table_columns[table_name].add(column_name.lower())

    schema_str = "\n".join(
        [f"Table: {row['table_name']}, Column: {row['column_name']} ({row['data_type']})" for row in schema_info]
    )

    # 🔹 Check if the user is asking for all employees (skip filtering)
    all_employees_keywords = ["all employees", "list of employees", "everyone"]
    is_fetching_all_employees = any(keyword in message.lower() for keyword in all_employees_keywords)

    # 🔹 Construct the SQL prompt
    if is_fetching_all_employees:
        filtering_instruction = "- Do NOT filter by email_address. Retrieve all records."
    else:
        filtering_instruction = f"- Ensure the WHERE clause includes email_address = '{state.user_email}'"

    prompt = f"""
    You are an SQL expert. Based on the following database schema, generate an optimized SQL query for PostgreSQL.

    Schema Information:
    {schema_str}

    User Request:
    {message}

    {filtering_instruction}

    - ONLY use column names that exist in the schema above.
    - If column names have uppercase letters, wrap them in double quotes (e.g., "fromDate").
    - Provide **only the SQL query** without any explanation, introduction, or additional text.
    - Do **not** include "Here is your query" or any extra words. Only output the raw SQL.
    """

    try:
        response = requests.post(OLLAMA_URL, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
        sql_query = response.json().get("response", "").strip()

        # 🔹 Remove any unexpected text around SQL
        sql_query = re.sub(r"```sql|```", "", sql_query).strip()
        print(f"✅ Generated SQL query: {sql_query}")

        return state.copy(update={"response": sql_query})

    except Exception as e:
        print(f"❌ Error generating SQL: {e}")
        return state.copy(update={"response": "Failed to generate SQL query."})

# 🔹 4. Execute SQL Query
def execute_sql(state: ChatState):
    print("🔹 Executing SQL query...")
    sql_query = state.response
    if not sql_query:
        return state.copy(update={"response": "No SQL query to execute."})

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchall()

                print(f"✅ SQL query executed successfully. Result: {result}")

        return state.copy(update={"response": format_response(result)})

    except Exception as e:
        print(f"❌ Database error: {e}")
        return state.copy(update={"response": "Database query failed."})
    
# 🔹 4. Format Response Based on Query Type
def format_response(data):
    """ Formats the response dynamically based on query results. """
    if not data:
        return "No results found."

    if isinstance(data, list):
        if isinstance(data[0], dict):
            keys = list(data[0].keys())

            # If only one column is retrieved, format as a list
            if len(keys) == 1:
                key = keys[0]
                values = [row[key] for row in data]
                return f"The {key}s are: {', '.join(map(str, values))}."

            # If multiple columns, format as table-like output
            table = "\n".join([", ".join([f"{k}: {v}" for k, v in row.items()]) for row in data])
            return f"Here is the requested data:\n{table}"

    return data  # Default case    

# 🔹 5. Get HR Policy
def get_policy(state: ChatState):
    message = state.messages[-1].content if state.messages else ""

    for key, value in policies.items():
        if key.lower() in message.lower():
            return state.copy(update={"response": value})

    return state.copy(update={"response": "Policy not found."})

# 🔹 6. Generate AI Response
def generate_response(state: ChatState):
    message = state.messages[-1].content if state.messages else ""
    user_name = state.name if state.name else "User"
    if(state.intent != "general"):
        answer = state.response

    try:
        if(state.intent != "general"):
            response = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": f"Respond as an HR assistant.\nUser: {message} answer: {answer}",
                "stream": False,
        })
        else:    
            response = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": f"Respond as an HR assistant.\nUser: {message}",
                "stream": False,
            })

        response_data = response.json()
        ai_response = response_data.get("response", "").strip().replace("[Your Name]", user_name)

        return state.copy(update={"response": ai_response})

    except Exception as e:
        print(f"❌ Error in AI response generation: {e}")
        return state.copy(update={"response": "I'm sorry, I couldn't process your request."})

# ✅ Define LangGraph Workflow
graph = StateGraph(ChatState)
graph.add_node("classify_intent", classify_intent)
graph.add_node("generate_sql_query", generate_sql_query)
graph.add_node("execute_sql", execute_sql)
graph.add_node("get_policy", get_policy)
graph.add_node("generate_response", generate_response)

def intent_router(state: ChatState):
    if state.intent in ["user_details", "leave_balance", "attendance", "paid_leave"]:
        print(f"🔹 Route to SQL query generation for intent: {state.intent}")
        return "generate_sql_query"
    elif state.intent == "hr_policy":
        print("🔹 Route to get_policy")
        return "get_policy"
    else:
        print("🔹 Route to AI response generation")
        return "generate_response"

graph.add_edge("__start__", "classify_intent")
graph.add_conditional_edges("classify_intent", intent_router)
graph.add_edge("generate_sql_query", "execute_sql")
graph.add_edge("execute_sql", "generate_response")
graph.add_edge("get_policy", "generate_response")

# ✅ Compile Workflow
workflow = graph.compile()

print("✅ Workflow Compiled Successfully.")

# ✅ Function to Handle Chat Requests
def chatbot(message, user_email):
    print(f"📝 Debug: Received message = '{message}', user_email = {user_email}")

    if not message or not isinstance(message, str) or not user_email:
        print("❌ Error: Invalid input received.")
        return {"response": "Invalid input. Please provide a valid message."}

    try:
        # ✅ Invoke workflow
        result = workflow.invoke(ChatState(messages=[HumanMessage(content=message)], user_email=user_email))

        # ✅ Extract response from dictionary
        if isinstance(result, dict) and "response" in result:
            response_text = result["response"]
            print(f"✅ Final AI Response: {response_text}")
            return {"response": response_text}
        else:
            print(f"❌ Unexpected result format: {result}")
            return {"response": "An internal error occurred. Please try again."}

    except Exception as e:
        print(f"❌ Critical Error in chatbot function: {e}")
        return {"response": "An internal error occurred. Please try again."}


