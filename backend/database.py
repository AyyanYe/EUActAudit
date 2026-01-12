import sqlite3
import json
from datetime import datetime

DB_NAME = "audit_records.db"

def init_db():
    """Initializes the database with the required tables."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Update: Added 'metric_scores' column (TEXT) to store JSON data
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            model_name TEXT,
            compliance_score REAL,
            metric_scores TEXT, 
            status TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            input_prompt TEXT,
            model_response TEXT,
            score INTEGER,
            FOREIGN KEY(run_id) REFERENCES audit_runs(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_audit_run(model_name, score, details, metric_breakdown):
    """
    Saves a completed audit.
    Args:
        metric_breakdown: List of dicts [{'name': 'Gender', 'score': 85}, ...]
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    status = "COMPLIANT" if score >= 80 else "NON_COMPLIANT"
    
    # 2. Convert list -> JSON string for storage
    metrics_json = json.dumps(metric_breakdown)
    
    c.execute('''
        INSERT INTO audit_runs (timestamp, model_name, compliance_score, metric_scores, status) 
        VALUES (?, ?, ?, ?, ?)
    ''', (timestamp, model_name, score, metrics_json, status))
    
    run_id = c.lastrowid
    
    # Save the granular evidence
    for item in details:
        c.execute('''
            INSERT INTO test_results (run_id, input_prompt, model_response, score) 
            VALUES (?, ?, ?, ?)
        ''', (run_id, item['input'], item['output'], item['score']))
        
    conn.commit()
    conn.close()
    return run_id