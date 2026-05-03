import sqlite3

DB_NAME = "audit_records.db"


def add_system_prompt_column():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(audit_runs)")
        columns = [info[1] for info in cursor.fetchall()]

        if "system_prompt" not in columns:
            print("Adding 'system_prompt' column...")
            cursor.execute("ALTER TABLE audit_runs ADD COLUMN system_prompt TEXT")
            conn.commit()
            print("Done. Database updated.")
        else:
            print("'system_prompt' column already exists.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    add_system_prompt_column()
