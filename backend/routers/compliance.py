from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Any, Optional, List


# Import the Compliance Logic and Report Generator
from core.risk_logic import ComplianceAgent
from core.report_gen import create_compliance_cert

router = APIRouter(prefix="/compliance", tags=["Compliance"])
agent = ComplianceAgent()

# 1. Data Models definitions
class RiskRequest(BaseModel):
    description: str
    user_metrics: Optional[List[str]] = []

class ReportRequest(BaseModel):
    results: Dict[str, Any]
    use_case_info: Optional[Dict[str, Any]] = None

# Endpoints

@router.post("/risk-assessment")
async def assess_risk(request: RiskRequest):
    try:
        # Pass the user_metrics to the agent
        return agent.analyze_use_case(request.description, request.user_metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-pdf")
async def generate_pdf(request: ReportRequest):
    """
    Generates the physical PDF certificate.
    """
    try:
        # Generate PDF bytes using the report generator
        pdf_bytes = create_compliance_cert(request.results)
        
        # Return as a downloadable file
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))