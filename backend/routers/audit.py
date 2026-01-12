from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import json

from core.evaluation_engine import AuditEngine
from database import save_audit_run, DB_NAME

router = APIRouter(prefix="/audit", tags=["Audit"])

class AuditConfig(BaseModel):
    api_key: str
    selected_risks: List[str]
    model_name: Optional[str] = "gpt-3.5-turbo"

@router.post("/run-bias-test")
async def run_audit(config: AuditConfig):
    try:
        # 1. Initialize Engine
        engine = AuditEngine(
            target_api_key=config.api_key, 
            model_name=config.model_name
        )
        
        # 2. Run Execution Loop
        report_data = await engine.run_audit(config.selected_risks)
        
        # 3. SAVE TO DB (Updated to pass metric_breakdown)
        run_id = save_audit_run(
            model_name=config.model_name,
            score=report_data['compliance_score'],
            details=report_data['details'],
            metric_breakdown=report_data['metric_breakdown'] # <--- NEW
        )
        
        report_data['run_id'] = run_id
        return report_data

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_audit_history():
    """
    Fetches history and parses the JSON metric scores back into lists.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT * FROM audit_runs ORDER BY timestamp DESC")
        rows = c.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            r = dict(row)
            # Parse the JSON string back to a real list for the Frontend
            if r.get('metric_scores'):
                try:
                    r['metric_scores'] = json.loads(r['metric_scores'])
                except:
                    r['metric_scores'] = [] 
            results.append(r)
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))