from dotenv import load_dotenv
import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import re

# ✅ Load environment variables
load_dotenv()

# ✅ PostgreSQL Database Connection
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", 5432),
}

# ✅ Ollama API Configuration (Llama 3)
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

# 🔹 1. Fetch Database Schema Dynamically
def get_database_schema():
    """Fetches the table and column names from PostgreSQL using pg_catalog."""
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

# 🔹 2. Generate SQL Query from User Prompt using Llama 3
def generate_sql_query(user_prompt):
    """ Uses Llama 3 (via Ollama) to generate an SQL query from the user prompt with schema awareness. """
    print(f"📝 Generating SQL for: {user_prompt}")

    # Fetch schema dynamically
    schema_info = get_database_schema()
    
    if not schema_info:
        print("❌ No schema information available.")
        return None

    # 🔹 Get a dictionary of correct column names for each table
    table_columns = {}
    for row in schema_info:
        table_name = row['table_name']
        column_name = row['column_name']
        if table_name not in table_columns:
            table_columns[table_name] = set()
        table_columns[table_name].add(column_name.lower())  # Store as lowercase for matching

    # Format schema for Llama 3
    schema_str = "\n".join(
        [f"Table: {row['table_name']}, Column: {row['column_name']} ({row['data_type']})" for row in schema_info]
    )

    prompt = f"""
    You are an SQL expert. Based on the following database schema, generate an optimized SQL query for PostgreSQL.

    Schema Information:
    {schema_str}

    User Request:
    {user_prompt}

    - Use the correct column names as per the schema above.
    - If column names have uppercase letters, wrap them in double quotes (e.g., "fromDate").
    - Provide only the SQL query without any explanation.
    """

    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response_data = response.json()
        sql_query = response_data.get("response", "").strip()

        # 🔹 Clean up the query
        sql_query = re.sub(r"```sql|```", "", sql_query).strip()

        # 🔹 Ensure column names match (fix case issues)
        for table, columns in table_columns.items():
            for col in columns:
                pattern = rf"\b{col}\b"  # Match exact column name
                if col.lower() != col:  # If it has uppercase letters
                    sql_query = re.sub(pattern, f'"{col}"', sql_query, flags=re.IGNORECASE)

        print(f"✅ Generated SQL: {sql_query}")
        return sql_query

    except Exception as e:
        print(f"❌ Error generating SQL: {e}")
        return None

# 🔹 3. Execute SQL Query
def execute_sql(sql_query):
    """ Executes the SQL query and returns results. """
    if not sql_query:
        return {"error": "No valid SQL query generated."}

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchall()  # Fetch all results
                return format_response(result)

    except Exception as e:
        print(f"❌ Database error: {e}")
        return {"error": "Database query failed."}

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

# 🔹 5. Main SQL Agent Function
def sql_agent():
    """ Handles SQL query generation and execution using Llama 3. """
    user_prompt = input("Enter your query: ")  # Ask user for input
    sql_query = generate_sql_query(user_prompt)
    result = execute_sql(sql_query)
    print(result)

# ✅ Run the Agent
if __name__ == "__main__":
    sql_agent()
