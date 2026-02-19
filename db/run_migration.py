"""
Run SQL migrations directly against Supabase PostgreSQL database.
Usage: python run_migration.py 04_add_audio_path.sql
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 not installed. Install it with:")
    print("   pip install psycopg2-binary")
    sys.exit(1)


def get_db_connection_string() -> str:
    """
    Build PostgreSQL connection string from environment variables.
    Supabase provides a connection string in this format:
    postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
    """
    # Option 1: Use direct connection string if available
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    
    # Option 2: Build from Supabase URL components
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_db_password = os.getenv("SUPABASE_DB_PASSWORD")
    
    if not supabase_url:
        raise ValueError("Missing DATABASE_URL or SUPABASE_URL in environment variables")
    
    if not supabase_db_password:
        raise ValueError(
            "Missing SUPABASE_DB_PASSWORD in environment variables.\n"
            "Find it in: Supabase Dashboard > Project Settings > Database > Connection string"
        )
    
    # Extract project reference from URL (e.g., https://abc123xyz.supabase.co)
    project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "")
    
    return f"postgresql://postgres:{supabase_db_password}@db.{project_ref}.supabase.co:5432/postgres"


def run_migration(sql_file_path: str):
    """Execute SQL migration file."""
    if not os.path.exists(sql_file_path):
        print(f"❌ File not found: {sql_file_path}")
        sys.exit(1)
    
    # Read SQL file
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print(f"📄 Running migration: {sql_file_path}")
    print(f"📝 SQL:\n{sql_content}\n")
    
    # Connect to database
    try:
        conn_string = get_db_connection_string()
        print("🔌 Connecting to database...")
        
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        # Execute migration
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ Migration executed successfully!")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <sql_file>")
        print("Example: python run_migration.py 04_add_audio_path.sql")
        sys.exit(1)
    
    sql_file = sys.argv[1]
    
    # If relative path, look in db/ directory
    if not os.path.isabs(sql_file):
        db_dir = os.path.dirname(__file__)
        sql_file = os.path.join(db_dir, sql_file)
    
    run_migration(sql_file)
