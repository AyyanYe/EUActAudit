from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
from sqlalchemy.orm import Session
from database import get_db, AuditRun

router = APIRouter()


# Lazy import for AuditEngine (only import when needed to avoid numpy dependency at startup)
def get_audit_engine():
    """Lazy import of AuditEngine to avoid numpy dependency at startup."""
    try:
        from core.evaluation_engine import AuditEngine

        return AuditEngine
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Audit engine dependencies not installed. Please install numpy and other required packages: {str(e)}",
        )


# 1. Request Model
class AuditRequest(BaseModel):
    api_key: str
    selected_risks: List[str]
    model_name: str
    risk_level: str = "Unknown"
    user_id: str = "anonymous"
    system_prompt: str


# 2. Save Function (now uses SQLAlchemy + unified DB)
def save_audit_run(
    db: Session, model, risk_level, score, details, user_id, system_prompt
):
    audit_run = AuditRun(
        model=model,
        risk_level=risk_level,
        score=score,
        details=json.dumps(details),
        user_id=user_id,
        system_prompt=system_prompt,
        timestamp=datetime.now().isoformat(),
    )
    db.add(audit_run)
    db.commit()


@router.post("/run-bias-test")
async def run_audit_endpoint(request: AuditRequest, db: Session = Depends(get_db)):
    try:
        print(f"Received Audit Request for {request.model_name} from {request.user_id}")

        # Initialize Engine (lazy import)
        AuditEngine = get_audit_engine()
        engine = AuditEngine(
            target_api_key=request.api_key, model_name=request.model_name
        )

        # Run Audit
        results = await engine.run_audit(
            request.selected_risks, system_instruction=request.system_prompt
        )

        # --- CRITICAL FIX: Inject missing data for the Report Generator ---
        results["risk_level"] = request.risk_level
        results["system_prompt"] = request.system_prompt
        # -------------------------------------------------------------------

        # Save to DB (unified database)
        save_audit_run(
            db,
            request.model_name,
            request.risk_level,
            results["compliance_score"],
            results,
            request.user_id,
            request.system_prompt,
        )

        return results
    except Exception as e:
        print(f"Audit Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_audit_history(
    user_id: Optional[str] = Query(None), db: Session = Depends(get_db)
):
    """Get audit history, optionally filtered by user_id."""
    query = db.query(AuditRun)

    if user_id and user_id.strip():
        query = query.filter(AuditRun.user_id == user_id)

    runs = query.order_by(AuditRun.timestamp.desc()).all()

    return [
        {
            "id": run.id,
            "model": run.model,
            "risk_level": run.risk_level,
            "score": run.score,
            "timestamp": run.timestamp,
            "system_prompt": run.system_prompt,
        }
        for run in runs
    ]
