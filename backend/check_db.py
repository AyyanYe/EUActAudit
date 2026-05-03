import sqlite3
import pandas as pd

# Connect to the DB
conn = sqlite3.connect("audit_records.db")

# Read the high-level runs
print("--- AUDIT RUNS ---")
runs = pd.read_sql_query("SELECT * FROM audit_runs", conn)
print(runs)

# Read the specific test inputs/outputs (The Evidence)
print("\n--- TEST DETAILS (EVIDENCE) ---")
details = pd.read_sql_query("SELECT * FROM test_results LIMIT 5", conn)
print(details)

conn.close()
