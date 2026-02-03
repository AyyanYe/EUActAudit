import sqlite3
import json
from datetime import datetime

DB_NAME = "audit_records.db"

def init_db():
    """Initializes the database with the correct schema matching audit.py."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Create table with ALL required columns
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT,           
            risk_level TEXT,      
            score INTEGER,
            details TEXT,         
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_audit_run(model, risk_level, score, details):
    """
    Saves a completed audit.
    Matches the arguments sent from routers/audit.py
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    # Dump details to JSON string
    details_json = json.dumps(details)
    
    c.execute('''
        INSERT INTO audit_runs (model, risk_level, score, details, timestamp) 
        VALUES (?, ?, ?, ?, ?)
    ''', (model, risk_level, score, details_json, timestamp))
    
    run_id = c.lastrowid
    conn.commit()
    conn.close()
    return run_id