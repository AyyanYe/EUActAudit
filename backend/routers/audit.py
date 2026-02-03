from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import json
import sqlite3
from datetime import datetime
from core.evaluation_engine import AuditEngine

router = APIRouter()

# 1. Request Model
class AuditRequest(BaseModel):
    api_key: str
    selected_risks: List[str]
    model_name: str
    risk_level: str = "Unknown"
    user_id: str = "anonymous"
    system_prompt: str

def get_db_connection():
    conn = sqlite3.connect('audit_records.db')
    conn.row_factory = sqlite3.Row
    return conn

# 2. Save Function
def save_audit_run(model, risk_level, score, details, user_id, system_prompt):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audit_runs (model, risk_level, score, details, user_id, system_prompt, timestamp) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (model, risk_level, score, json.dumps(details), user_id, system_prompt, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

@router.post("/run-bias-test")
async def run_audit_endpoint(request: AuditRequest):
    try:
        print(f"Received Audit Request for {request.model_name} from {request.user_id}")
        
        # Initialize Engine
        engine = AuditEngine(
            target_api_key=request.api_key,
            model_name=request.model_name
        )
        
        # Run Audit
        results = await engine.run_audit(
            request.selected_risks, 
            system_instruction=request.system_prompt
        )
        
        # --- CRITICAL FIX: Inject missing data for the Report Generator ---
        results["risk_level"] = request.risk_level
        results["system_prompt"] = request.system_prompt
        # -------------------------------------------------------------------

        # Save to DB
        save_audit_run(
            request.model_name, 
            request.risk_level, 
            results['compliance_score'], 
            results,
            request.user_id,
            request.system_prompt
        )
        
        return results
    except Exception as e:
        print(f"Audit Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
def get_audit_history(user_id: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute(
            "SELECT id, model, risk_level, score, timestamp, system_prompt FROM audit_runs WHERE user_id = ? ORDER BY timestamp DESC", 
            (user_id,)
        )
    else:
        cursor.execute("SELECT id, model, risk_level, score, timestamp, system_prompt FROM audit_runs ORDER BY timestamp DESC")
        
    rows = cursor.fetchall()
    conn.close()
    # Convert rows to dicts
    history = [dict(row) for row in rows]
    
    # Optional: Parse 'details' if you need it in frontend history
    # for item in history:
    #     if 'details' in item and isinstance(item['details'], str):
    #         item['details'] = json.loads(item['details'])
            
    return history