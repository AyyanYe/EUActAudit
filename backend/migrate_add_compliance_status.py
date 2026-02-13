"""
Migration script to add compliance_status column to projects table.
Run this once to add the compliance status tracking feature.
"""
import sqlite3

DB_PATH = "./eu_ai_act_2025.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if compliance_status column already exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'compliance_status' in columns:
            print("compliance_status column already exists in projects table. Skipping.")
        else:
            # Add compliance_status column to projects
            cursor.execute("ALTER TABLE projects ADD COLUMN compliance_status TEXT DEFAULT 'PENDING'")
            print("Added compliance_status column to projects table.")
        
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

