from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from fastapi.responses import Response

# Initialize the router - THIS WAS MISSING
router = APIRouter(
    prefix="/compliance",
    tags=["Compliance"]
)

# --- Data Models ---
class RiskRequest(BaseModel):
    description: str

class ReportRequest(BaseModel):
    results: Dict[str, Any]
    use_case_info: Optional[Dict[str, Any]] = None

# --- Endpoints ---

@router.post("/risk-assessment")
async def assess_risk(request: RiskRequest):
    """
    Analyzes the user's description to determine High/Low risk.
    """
    desc = request.description.lower()
    
    # Logic based on EU AI Act Annex III (High Risk Categories)
    high_risk_keywords = [
        "hr", "recruitment", "hiring", "employment", 
        "credit", "loan", "banking", "insurance",
        "biometric", "facial recognition", "education", "grading"
    ]
    
    is_high_risk = any(keyword in desc for keyword in high_risk_keywords)
    
    return {
        "risk_level": "High" if is_high_risk else "Limited",
        "category": "Annex III (Employment)" if "hr" in desc else "General Purpose",
        "requirements": [
            "Article 10 (Data Governance)",
            "Article 13 (Transparency)", 
            "Article 15 (Accuracy & Robustness)"
        ] if is_high_risk else ["Article 50 (Transparency)"]
    }

@router.post("/generate-pdf")
async def generate_pdf(request: ReportRequest):
    """
    Generates a mock PDF certificate for the audit results.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from io import BytesIO

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Draw Header
        p.setFont("Helvetica-Bold", 24)
        p.drawString(100, 750, "EU AI Act Compliance Certificate")
        
        # Draw Body
        p.setFont("Helvetica", 12)
        p.drawString(100, 700, f"Status: {request.results.get('status', 'Unknown')}")
        p.drawString(100, 680, f"Bias Score: {request.results.get('bias_score', 'N/A')}")
        p.drawString(100, 660, f"Transparency Score: {request.results.get('transparency_score', 'N/A')}")
        
        p.save()
        
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        
        # Return PDF as a binary blob
        return Response(content=pdf_bytes, media_type="application/pdf")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Generation Failed: {str(e)}")