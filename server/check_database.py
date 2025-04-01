import psycopg2
import os
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

# ✅ PostgreSQL Configuration
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", 5432),
}

# ✅ Function to Check Database Connection
def check_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Database connected successfully!")
        conn.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

# ✅ Function to List Tables
def list_tables():
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                tables = cursor.fetchall()
                print("✅ Tables in database:", [table[0] for table in tables])
    except Exception as e:
        print(f"❌ Error checking tables: {e}")

# ✅ Function to Check Table Schema
def check_table_schema(table_name):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}';")
                columns = cursor.fetchall()
                if columns:
                    print(f"✅ Schema for `{table_name}`:", columns)
                else:
                    print(f"❌ Table `{table_name}` does not exist.")
    except Exception as e:
        print(f"❌ Error checking schema for {table_name}: {e}")

# ✅ Function to Test a Query
def test_query(table_name):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
                results = cursor.fetchall()
                print(f"✅ Sample data from `{table_name}`:", results)
    except Exception as e:
        print(f"❌ Error running query on `{table_name}`: {e}")

# ✅ Run All Tests
if __name__ == "__main__":
    print("\n🔹 Checking Database Connection...")
    check_connection()
    
    print("\n🔹 Listing Tables...")
    list_tables()
    
    table_name = input("\nEnter table name to check schema: ").strip()
    if table_name:
        print(f"\n🔹 Checking Schema for `{table_name}`...")
        check_table_schema(table_name)
        
        print(f"\n🔹 Running Query on `{table_name}`...")
        test_query(table_name)
