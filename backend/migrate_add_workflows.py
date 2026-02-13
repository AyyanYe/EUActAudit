"""
Migration script to add workflows table and update interview_logs table.
Run this once to add the workflows feature to existing databases.
"""
import sqlite3
from datetime import datetime

DB_PATH = "./eu_ai_act_2025.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if workflows table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workflows'")
        if cursor.fetchone():
            print("Workflows table already exists. Skipping creation.")
        else:
            # Create workflows table
            cursor.execute("""
                CREATE TABLE workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    risk_level TEXT DEFAULT 'Unknown',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            print("Created workflows table.")
        
        # Check if workflow_id column already exists in interview_logs
        cursor.execute("PRAGMA table_info(interview_logs)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'workflow_id' in columns:
            print("workflow_id column already exists in interview_logs. Skipping.")
        else:
            # Add workflow_id column to interview_logs
            cursor.execute("ALTER TABLE interview_logs ADD COLUMN workflow_id INTEGER")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_interview_logs_workflow_id 
                ON interview_logs(workflow_id)
            """)
            print("Added workflow_id column to interview_logs table.")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

