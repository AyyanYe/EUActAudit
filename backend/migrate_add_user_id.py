# backend/migrate_add_user_id.py
"""
Migration script to add user_id column to projects table.
Run this once to update existing database.
"""
import sqlite3
import sys

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def migrate_database():
    """Add user_id column to projects table if it doesn't exist."""
    db_path = "eu_ai_act_2025.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user_id column exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "user_id" not in columns:
            print("Adding user_id column to projects table...")
            cursor.execute("ALTER TABLE projects ADD COLUMN user_id TEXT")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id)")
            conn.commit()
            print("✓ Migration completed successfully!")
        else:
            print("✓ user_id column already exists. No migration needed.")
        
        # Check if updated_at column exists
        if "updated_at" not in columns:
            print("Adding updated_at column to projects table...")
            # SQLite doesn't support DEFAULT CURRENT_TIMESTAMP in ALTER TABLE
            # We'll set it in application code instead
            cursor.execute("ALTER TABLE projects ADD COLUMN updated_at TIMESTAMP")
            # Set initial value for existing rows
            cursor.execute("UPDATE projects SET updated_at = created_at WHERE updated_at IS NULL")
            conn.commit()
            print("✓ updated_at column added successfully!")
        else:
            print("✓ updated_at column already exists.")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_database()

