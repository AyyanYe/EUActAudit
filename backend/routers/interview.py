from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, Project, Fact, InterviewLog, Obligation
from core.engine import GovernanceEngine
from core.risk_rules import evaluate_compliance_state

router = APIRouter()
engine = GovernanceEngine()

class ChatRequest(BaseModel):
    project_id: int
    message: str

class StartRequest(BaseModel):
    name: str
    description: str

@router.post("/start")
def start_interview(request: StartRequest, db: Session = Depends(get_db)):
    """Creates a new 'Compliance Profile'."""
    new_project = Project(name=request.name, description=request.description)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return {
        "project_id": new_project.id, 
        "message": "I have created your profile. To begin, please describe the AI system you are building or using. What is its main purpose?"
    }

@router.post("/chat")
async def chat_interview(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Fetch Project
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Log User Message
    db.add(InterviewLog(project_id=request.project_id, sender="user", message=request.message))
    db.commit()
    
    # 3. Get History context
    logs = db.query(InterviewLog).filter(InterviewLog.project_id == request.project_id).order_by(InterviewLog.timestamp).all()
    history_text = "\n".join([f"{l.sender}: {l.message}" for l in logs])
    
    # 4. EXTRACT FACTS (The Sensor)
    extracted_data = await engine.extract_facts(history_text)
    
    # 5. UPDATE DB (The State Machine)
    # Save new facts or update existing ones
    for key, value in extracted_data.items():
        existing_fact = db.query(Fact).filter(Fact.project_id == project.id, Fact.key == key).first()
        if existing_fact:
            existing_fact.value = str(value)
        else:
            db.add(Fact(project_id=project.id, key=key, value=str(value), confidence=100, source="inference"))
    db.commit()
    
    # Reload facts as a dictionary for the Logic Engine
    db_facts = db.query(Fact).filter(Fact.project_id == project.id).all()
    fact_dict = {f.key: f.value for f in db_facts}
    
    # 6. RUN DETERMINISTIC RULES (The Judge)
    risk_level, required_obligations, warnings = evaluate_compliance_state(fact_dict)
    
    # Update Project State
    project.risk_level = risk_level
    db.commit()

    # Save Obligations to DB (Avoid duplicates)
    for ob in required_obligations:
        exists = db.query(Obligation).filter(Obligation.project_id == project.id, Obligation.code == ob['code']).first()
        if not exists:
            db.add(Obligation(
                project_id=project.id, 
                code=ob['code'], 
                title=ob['title'], 
                description=ob['desc'],
                status="PENDING"
            ))
    db.commit()

    # 7. GENERATE RESPONSE (The Interviewer)
    bot_response = await engine.generate_next_question(fact_dict, risk_level, required_obligations)
    
    # 8. Log Bot Response
    db.add(InterviewLog(project_id=request.project_id, sender="bot", message=bot_response))
    db.commit()
    
    return {
        "response": bot_response,
        "risk_level": risk_level,
        "facts": fact_dict,
        "obligations": [ob['code'] for ob in required_obligations]
    }