"""
Migration script to add state machine fields to existing projects table.
Run this if you have an existing eu_ai_act_2025.db with projects that need state/confidence fields.
"""
import sqlite3
import os

DB_NAME = "eu_ai_act_2025.db"

def migrate_governance_schema():
    """Add interview_state and confidence_level columns to projects table if they don't exist."""
    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} does not exist. It will be created on first run.")
        return
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(projects)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Add interview_state if missing
        if "interview_state" not in columns:
            print("Adding 'interview_state' column...")
            cursor.execute("ALTER TABLE projects ADD COLUMN interview_state TEXT DEFAULT 'INIT'")
            # Update existing rows
            cursor.execute("UPDATE projects SET interview_state = 'INIT' WHERE interview_state IS NULL")
            conn.commit()
            print("Added 'interview_state' column successfully")
        else:
            print("'interview_state' column already exists.")
        
        # Add confidence_level if missing
        if "confidence_level" not in columns:
            print("Adding 'confidence_level' column...")
            cursor.execute("ALTER TABLE projects ADD COLUMN confidence_level TEXT DEFAULT 'LOW'")
            # Update existing rows
            cursor.execute("UPDATE projects SET confidence_level = 'LOW' WHERE confidence_level IS NULL")
            conn.commit()
            print("Added 'confidence_level' column successfully")
        else:
            print("'confidence_level' column already exists.")
        
        conn.close()
        print("\nMigration complete!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_governance_schema()

