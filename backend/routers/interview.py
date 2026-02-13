import json
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from datetime import datetime
from database import get_db, Project, Fact, InterviewLog, Obligation, Workflow
from core.engine import GovernanceEngine
from core.risk_rules import evaluate_compliance_state
from core.state_machine import StateMachine, InterviewState, ConfidenceLevel
from core.auth import get_clerk_user_id, get_user_id_optional
from core.high_risk_checklist import can_complete_high_risk_assessment
from core.obligation_mapper import (
    get_obligation_code_for_fact, 
    is_negative_value, 
    is_positive_value, 
    is_planned_value
)
from core.dialogue_memory import compute_topic_ask_count, compute_stuck_on_topic

# Lazy import for report generation (optional dependency)
try:
    from core.report_gen import create_compliance_cert
except ImportError:
    create_compliance_cert = None

router = APIRouter()
engine = GovernanceEngine()


def _parse_workflow_steps(fact_dict: dict) -> List[str]:
    """Parse workflow_steps from fact_dict (stored as JSON string)."""
    raw = fact_dict.get("workflow_steps")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(s).strip() for s in raw if s]
    try:
        arr = json.loads(raw) if isinstance(raw, str) else []
        return [str(s).strip() for s in arr if s] if isinstance(arr, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


class ChatRequest(BaseModel):
    project_id: int
    message: str
    workflow_id: Optional[int] = None  # Optional: if None, uses General/Default chat

class StartRequest(BaseModel):
    name: str
    description: str

@router.post("/start")
def start_interview(
    request: StartRequest, 
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Creates a new 'Compliance Profile' in INIT state."""
    # Get user_id from Clerk token (optional for backward compatibility)
    user_id = get_user_id_optional(authorization) or "anonymous"
    
    new_project = Project(
        user_id=user_id,
        name=request.name, 
        description=request.description,
        interview_state=InterviewState.INIT.value,
        confidence_level=ConfidenceLevel.LOW.value
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    print(f"Project Created: {new_project.id} (user_id={new_project.user_id}, name={new_project.name})")
    
    # Log the initial bot message to InterviewLog so it persists
    initial_message = "I have created your profile. To begin, please describe the AI system you are building or using. What is its main purpose?"
    db.add(InterviewLog(
        project_id=new_project.id,
        sender="bot",
        message=initial_message
    ))
    db.commit()
    
    return {
        "project_id": new_project.id, 
        "message": initial_message,
        "state": InterviewState.INIT.value,
        "confidence": ConfidenceLevel.LOW.value
    }

@router.post("/chat")
async def chat_interview(
    request: ChatRequest, 
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """
    State Machine-Driven Chat Loop:
    1. Extract facts from conversation
    2. Update state machine state
    3. Calculate confidence
    4. Run risk rules (if state requires it)
    5. Generate state-aware response
    """
    # 1. Fetch Project
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Verify user owns this project (if authenticated)
    user_id = get_user_id_optional(authorization)
    if user_id and project.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this project")

    # 2. Log User Message (with workflow_id if provided)
    db.add(InterviewLog(
        project_id=request.project_id, 
        workflow_id=request.workflow_id,
        sender="user", 
        message=request.message
    ))
    db.commit()
    
    # 3. Get History context (filtered by workflow_id if provided)
    query = db.query(InterviewLog).filter(InterviewLog.project_id == request.project_id)
    if request.workflow_id is not None:
        # Get messages for this specific workflow
        query = query.filter(InterviewLog.workflow_id == request.workflow_id)
    else:
        # Get messages for General/Default chat (workflow_id is NULL)
        query = query.filter(InterviewLog.workflow_id.is_(None))
    
    logs = query.order_by(InterviewLog.timestamp).all()
    history_text = "\n".join([f"{l.sender}: {l.message}" for l in logs])
    
    # 4. EXTRACT FACTS (The Sensor)
    extracted_data = await engine.extract_facts(history_text)
    
    # Snapshot facts BEFORE applying this turn's extraction (for context-aware next question)
    facts_before = {f.key: f.value for f in db.query(Fact).filter(Fact.project_id == project.id).all()}
    
    # Use confidence_scores for Fact.confidence; do not store as a fact key
    confidence_scores = extracted_data.pop("confidence_scores", None) or {}
    if not isinstance(confidence_scores, dict):
        confidence_scores = {}
    
    # 5. UPDATE DB with extracted facts
    for key, value in extracted_data.items():
        if key == "confidence_scores":
            continue
        existing_fact = db.query(Fact).filter(Fact.project_id == project.id, Fact.key == key).first()
        if key == "workflow_steps" and isinstance(value, list):
            fact_value = json.dumps(value)
        else:
            fact_value = str(value)
        conf = 100
        if isinstance(confidence_scores.get(key), (int, float)):
            conf = max(0, min(100, int(confidence_scores[key])))
        if existing_fact:
            existing_fact.value = fact_value
            existing_fact.confidence = conf
        else:
            db.add(Fact(project_id=project.id, key=key, value=fact_value, confidence=conf, source="inference"))
    db.commit()
    
    # 5.25. UNIVERSAL GAP DETECTION - Update obligation status based on facts dynamically
    # This works for ALL risk levels and ALL articles without hardcoding
    # OPTIMIZATION: Only run if there are obligations (avoid unnecessary queries)
    try:
        obligation_count = db.query(Obligation).filter(Obligation.project_id == project.id).count()
        if obligation_count > 0:
            all_obligations = db.query(Obligation).filter(Obligation.project_id == project.id).all()
            fact_to_ob_map = {
                "human_oversight": "ART_14_OVERSIGHT",
                "data_governance": "ART_10",
                "accuracy_robustness": "ART_15",
                "record_keeping": "ART_12",
                "transparency": "ART_50",
                "article_50_notice": "ART_50"
            }
            
            # Batch fetch all relevant facts to avoid N+1 queries
            fact_keys_to_check = list(fact_to_ob_map.keys())
            all_facts = {f.key: f for f in db.query(Fact).filter(
                Fact.project_id == project.id,
                Fact.key.in_(fact_keys_to_check + [f"{k}_remediation" for k in fact_keys_to_check])
            ).all()}
            
            for obligation in all_obligations:
                # Find corresponding fact key
                fact_key = None
                for fk, oc in fact_to_ob_map.items():
                    if oc == obligation.code:
                        fact_key = fk
                        break
                
                if fact_key:
                    fact = all_facts.get(fact_key)
                    if fact:
                        fact_value = fact.value.lower() if fact.value else ""
                        
                        # Check for remediation acceptance
                        remediation_key = f"{fact_key}_remediation"
                        remediation_fact = all_facts.get(remediation_key)
                        remediation_value = remediation_fact.value.lower() if remediation_fact and remediation_fact.value else ""
                        
                        # Update obligation status dynamically (soft states: under_review, planned)
                        if is_planned_value(fact_value) or remediation_value == "yes":
                            obligation.status = "planned_remediation"
                        elif fact_value == "partial_or_unclear":
                            obligation.status = "under_review"
                        elif is_negative_value(fact_value):
                            obligation.status = "gap_detected"
                        elif is_positive_value(fact_value):
                            obligation.status = "MET"
                        # Otherwise keep current status (PENDING, etc.)
            
            db.commit()
    except Exception as e:
        print(f"[WARNING] Error in universal gap detection: {e}")
        # Don't fail the request if gap detection fails
        pass
    
    # 5.5. REMEDIATION CLOSURE - Auto-update main facts when remediation is accepted
    # This ensures that when user accepts remediation, we mark the topic as "planned_remediation"
    # Get risk_level from project (may be updated later by risk rules, but we need it here for closure check)
    current_risk_level = project.risk_level or "Unknown"
    if current_risk_level == "HIGH":
        remediation_mapping = {
            "data_governance_remediation": "data_governance",
            "accuracy_robustness_remediation": "accuracy_robustness",
            "record_keeping_remediation": "record_keeping"
        }
        
        for remediation_key, main_fact_key in remediation_mapping.items():
            remediation_fact = db.query(Fact).filter(
                Fact.project_id == project.id, 
                Fact.key == remediation_key
            ).first()
            
            if remediation_fact and remediation_fact.value.lower() == "yes":
                # User accepted remediation - check if main fact needs updating
                main_fact = db.query(Fact).filter(
                    Fact.project_id == project.id,
                    Fact.key == main_fact_key
                ).first()
                
                main_value = main_fact.value.lower() if main_fact else ""
                
                # If main fact is still "no" or "absent", update to "planned_remediation"
                if main_value in ["no", "absent"]:
                    if main_fact:
                        main_fact.value = "planned_remediation"
                    else:
                        db.add(Fact(
                            project_id=project.id,
                            key=main_fact_key,
                            value="planned_remediation",
                            confidence=100,
                            source="remediation_closure"
                        ))
                    print(f"[REMEDIATION CLOSURE] Updated {main_fact_key} to planned_remediation")
        
        db.commit()
    
    # 6. Reload facts as a dictionary
    db_facts = db.query(Fact).filter(Fact.project_id == project.id).all()
    fact_dict = {f.key: f.value for f in db_facts}
    
    # 6.5. Context-aware: which mandatory topic did the user just speak about? (for sequential gap handling)
    HIGH_RISK_MANDATORY_ORDER = ["human_oversight", "data_governance", "accuracy_robustness", "record_keeping"]
    last_updated_fact_key = None
    for key in HIGH_RISK_MANDATORY_ORDER:
        if key not in extracted_data:
            continue
        old_val = (facts_before.get(key) or "").strip().lower()
        new_val = (str(extracted_data.get(key, "")).strip().lower() if extracted_data.get(key) is not None else "")
        if old_val != new_val:
            last_updated_fact_key = key
            break
    if last_updated_fact_key is None:
        for key in HIGH_RISK_MANDATORY_ORDER:
            if key in extracted_data:
                last_updated_fact_key = key
                break
    
    # 7. STATE MACHINE: Determine current state
    current_state = InterviewState(project.interview_state or InterviewState.INIT.value)
    next_state = StateMachine.determine_state(fact_dict, current_state)
    
    # 8. Calculate confidence
    confidence = StateMachine.calculate_confidence(fact_dict)
    
    # 9. RUN DETERMINISTIC RULES (The Judge) - only if state requires it
    risk_level = project.risk_level or "Unknown"
    required_obligations = []
    warnings = []
    
    if StateMachine.should_run_deductions(next_state):
        risk_level, required_obligations, warnings = evaluate_compliance_state(fact_dict)
        
        # Update Project State
        project.risk_level = risk_level
        
        # For HIGH risk systems, prevent transition to ASSESSMENT if mandatory topics are missing
        if risk_level == "HIGH" and next_state == InterviewState.ASSESSMENT:
            if not can_complete_high_risk_assessment(fact_dict, required_obligations):
                # Force back to CHECKPOINT until all mandatory topics are covered
                next_state = InterviewState.CHECKPOINT
        
        # Save Obligations to DB (Avoid duplicates)
        # Handle both dict format and string format for obligations
        for ob in required_obligations:
            if isinstance(ob, dict):
                exists = db.query(Obligation).filter(
                    Obligation.project_id == project.id, 
                    Obligation.code == ob.get('code', '')
                ).first()
                if not exists:
                    db.add(Obligation(
                        project_id=project.id, 
                        code=ob.get('code', 'UNKNOWN'), 
                        title=ob.get('title', 'Unknown Obligation'), 
                        description=ob.get('desc', ob.get('description', '')),
                        status="PENDING"
                    ))
            elif isinstance(ob, str):
                # Handle string format obligations (e.g., "BANNED: ...")
                exists = db.query(Obligation).filter(
                    Obligation.project_id == project.id, 
                    Obligation.code == ob
                ).first()
                if not exists:
                    db.add(Obligation(
                        project_id=project.id, 
                        code=ob, 
                        title=ob, 
                        description=ob,
                        status="PENDING"
                    ))
    
    # 10. Update project state and confidence
    project.interview_state = next_state.value
    project.confidence_level = confidence.value
    project.updated_at = datetime.now()
    db.commit()

    # 11. Get missing facts for current state
    missing_facts = StateMachine.get_missing_facts(fact_dict, next_state)

    # 11.45. PROHIBITED PRACTICE (Article 5) – Close chat when user confirms prohibited use
    remediation_accepted = fact_dict.get("remediation_accepted", "").lower()
    human_oversight_state = fact_dict.get("human_oversight", "").lower()

    if risk_level == "UNACCEPTABLE":
        project.compliance_status = "TERMINATED"
        project.status = "Terminated - Prohibited Practice"
        project.interview_state = "TERMINATED"
        db.commit()

        blocked_msg = None
        for w in (warnings or []):
            if isinstance(w, str) and w.strip().upper().startswith("BLOCKED:"):
                blocked_msg = w.strip()
                break
        if not blocked_msg and warnings:
            blocked_msg = warnings[0] if isinstance(warnings[0], str) else "This use case is prohibited under Article 5 of the EU AI Act."
        if not blocked_msg:
            blocked_msg = "This use case is prohibited under Article 5 of the EU AI Act."

        bot_response = (
            blocked_msg.rstrip(".")
            + ". This chat has been closed until further notice. Please start a new chat for a different use case."
        )

        db.add(InterviewLog(
            project_id=request.project_id,
            workflow_id=request.workflow_id,
            sender="bot",
            message=bot_response
        ))
        db.commit()

        return {
            "response": bot_response,
            "risk_level": risk_level,
            "facts": fact_dict,
            "workflow_steps": _parse_workflow_steps(fact_dict),
            "obligations": [],
            "state": "TERMINATED",
            "confidence": confidence.value,
            "state_description": "Assessment Terminated - Prohibited Practice",
            "compliance_status": "TERMINATED",
            "terminated": True,
        }

    # 11.5. CHECK COMPLIANCE STATUS - Article 14 Guardrail
    # Check if user refused remediation (non-compliant)
    if risk_level == "HIGH" and human_oversight_state in ["absent", "no", "partial"] and remediation_accepted == "no":
        # User refused remediation - set compliance status to NON_COMPLIANT
        project.compliance_status = "NON_COMPLIANT"
        project.status = "Terminated - Non-Compliant"
        db.commit()
        
        # Generate termination response
        bot_response = "⛔ Assessment Terminated. You have confirmed that this High-Risk system will NOT have human oversight. This is a direct violation of Article 14 of the EU AI Act. This system cannot be legally deployed. I am generating your Non-Compliance Report now."
        
        # Log termination message
        db.add(InterviewLog(
            project_id=request.project_id,
            workflow_id=request.workflow_id,
            sender="bot",
            message=bot_response
        ))
        db.commit()
        
        # Return termination response (frontend should trigger report generation)
        return {
            "response": bot_response,
            "risk_level": risk_level,
            "facts": fact_dict,
            "workflow_steps": _parse_workflow_steps(fact_dict),
            "obligations": [],
            "state": "TERMINATED",
            "confidence": confidence.value,
            "state_description": "Assessment Terminated - Non-Compliant",
            "compliance_status": "NON_COMPLIANT",
            "terminated": True  # Flag for frontend to trigger report generation
        }
    
    # 11.75. UNIVERSAL REMEDIATION HANDLER - Update obligation status when remediation accepted
    # OPTIMIZATION: Use batch queries to avoid N+1 problem
    try:
        obligation_count = db.query(Obligation).filter(Obligation.project_id == project.id).count()
        if obligation_count > 0:
            db_obligations = db.query(Obligation).filter(Obligation.project_id == project.id).all()
            fact_to_ob_map = {
                "human_oversight": "ART_14_OVERSIGHT",
                "data_governance": "ART_10",
                "accuracy_robustness": "ART_15",
                "record_keeping": "ART_12",
                "transparency": "ART_50",
                "article_50_notice": "ART_50"
            }
            
            # Batch fetch facts to avoid N+1 queries
            fact_keys_to_check = list(fact_to_ob_map.keys())
            remediation_keys = [f"{k}_remediation" for k in fact_keys_to_check]
            all_relevant_facts = {f.key: f for f in db.query(Fact).filter(
                Fact.project_id == project.id,
                Fact.key.in_(fact_keys_to_check + remediation_keys)
            ).all()}
            
            for obligation in db_obligations:
                # Find corresponding fact key
                fact_key = None
                for fk, oc in fact_to_ob_map.items():
                    if oc == obligation.code:
                        fact_key = fk
                        break
                
                if fact_key:
                    # Check if remediation was accepted
                    remediation_key = f"{fact_key}_remediation"
                    remediation_fact = all_relevant_facts.get(remediation_key)
                    main_fact = all_relevant_facts.get(fact_key)
                    
                    if remediation_fact and remediation_fact.value.lower() == "yes":
                        # User accepted remediation - update obligation status
                        obligation.status = "planned_remediation"
                        # Also update main fact if needed
                        if main_fact and is_negative_value(main_fact.value):
                            main_fact.value = "planned_remediation"
            
            db.commit()
    except Exception as e:
        print(f"[WARNING] Error in universal remediation handler: {e}")
        import traceback
        print(f"[WARNING] Traceback: {traceback.format_exc()}")
        pass
    
    # 11.9. DIALOGUE MEMORY: count how many times we asked each topic; detect if user is stuck
    topic_ask_count = compute_topic_ask_count(logs)
    stuck_on_topic = compute_stuck_on_topic(topic_ask_count, fact_dict, risk_level)

    # 12. GENERATE RESPONSE (The Interviewer) - state-aware
    # For HIGH risk, pass ALL project obligations so engine sees full status (e.g. ART_14 planned_remediation)
    # and can transition to next obligation / completed state instead of looping
    obligations_with_status = []
    if risk_level == "HIGH":
        all_db_obligations = db.query(Obligation).filter(Obligation.project_id == project.id).all()
        obligations_with_status = [
            {"code": ob.code, "title": ob.title, "description": ob.description or ob.title, "status": ob.status or "PENDING"}
            for ob in all_db_obligations
        ]
    elif required_obligations:
        ob_codes = [ob.get('code', '') if isinstance(ob, dict) else str(ob) for ob in required_obligations]
        ob_codes = [c for c in ob_codes if c]
        db_obligations_map = {ob.code: ob.status for ob in db.query(Obligation).filter(
            Obligation.project_id == project.id,
            Obligation.code.in_(ob_codes)
        ).all()} if ob_codes else {}
        for ob in required_obligations:
            if isinstance(ob, dict):
                ob_code = ob.get('code', '')
                obligations_with_status.append({**ob, 'status': db_obligations_map.get(ob_code, "PENDING")})
            else:
                obligations_with_status.append({"code": ob, "title": ob, "description": ob, "status": db_obligations_map.get(str(ob), "PENDING")})
    
    bot_response = await engine.generate_next_question(
        fact_dict,
        risk_level,
        next_state,
        confidence,
        missing_facts,
        warnings,
        obligations_with_status,
        last_updated_fact_key=last_updated_fact_key,
        topic_ask_count=topic_ask_count,
        stuck_on_topic=stuck_on_topic,
    )
    
    # 13. Log Bot Response
    db.add(InterviewLog(project_id=request.project_id, sender="bot", message=bot_response))
    db.commit()
    
    # Format obligations for response - include status for frontend
    # Use the obligations_with_status we already built (optimization - avoid duplicate queries)
    obligation_list = obligations_with_status if obligations_with_status else []
    
    # Update compliance status if remediation was accepted
    if risk_level == "HIGH" and human_oversight_state == "planned" and remediation_accepted == "yes":
        if project.compliance_status != "NON_COMPLIANT":  # Don't override if already non-compliant
            project.compliance_status = "PENDING"  # Still pending until all requirements met
    db.commit()
    
    return {
        "response": bot_response,
        "risk_level": risk_level,
        "facts": fact_dict,
        "workflow_steps": _parse_workflow_steps(fact_dict),
        "obligations": obligation_list,  # Now returns full objects with status
        "state": next_state.value,
        "confidence": confidence.value,
        "state_description": StateMachine.get_state_description(next_state),
        "compliance_status": project.compliance_status or "PENDING",
        "terminated": False
    }

@router.get("/projects")
def list_projects(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """
    List all projects for the user.
    - If authenticated: returns user's projects + all anonymous projects (user_id is NULL)
    - If not authenticated: returns ALL anonymous projects (user_id is NULL or "anonymous")
    """
    user_id = get_user_id_optional(authorization)
    
    # CRITICAL: Always include anonymous projects (user_id is NULL or "anonymous")
    # If authenticated, also include user's own projects
    if user_id:
        # Authenticated: user's projects + all anonymous projects
        projects = db.query(Project).filter(
            or_(
                Project.user_id == user_id,
                Project.user_id == None,
                Project.user_id == "anonymous"
            )
        ).order_by(Project.updated_at.desc()).all()
        print(f"Found {len(projects)} projects for authenticated user {user_id} (including anonymous)")
    else:
        # Not authenticated: show ALL anonymous projects
        projects = db.query(Project).filter(
            or_(
                Project.user_id == None,
                Project.user_id == "anonymous"
            )
        ).order_by(Project.updated_at.desc()).all()
        print(f"Found {len(projects)} anonymous projects for unauthenticated user")
    
    return {
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "risk_level": p.risk_level,
                "status": p.status,
                "interview_state": p.interview_state,
                "confidence_level": p.confidence_level,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "message_count": db.query(InterviewLog).filter(InterviewLog.project_id == p.id).count()
            }
            for p in projects
        ]
    }

@router.get("/projects/{project_id}")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get a specific project with full chat history."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user owns this project (allow anonymous projects to be accessed by anyone)
    user_id = get_user_id_optional(authorization)
    # Only block if user is authenticated AND project belongs to a different user
    # Allow access to anonymous projects (user_id is None or "anonymous")
    if user_id and project.user_id and project.user_id not in [None, "anonymous"] and project.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    # Get all chat logs (ordered by timestamp ascending to show chronological order)
    logs = db.query(InterviewLog).filter(InterviewLog.project_id == project_id).order_by(InterviewLog.timestamp.asc()).all()
    
    # Get facts
    facts = db.query(Fact).filter(Fact.project_id == project_id).all()
    fact_dict = {f.key: f.value for f in facts}
    
    # Get obligations
    obligations = db.query(Obligation).filter(Obligation.project_id == project_id).all()
    
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "risk_level": project.risk_level,
            "status": project.status,
            "interview_state": project.interview_state,
            "confidence_level": project.confidence_level,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        },
        "messages": [
            {
                "sender": log.sender,
                "message": log.message,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            }
            for log in logs
        ],
        "facts": fact_dict,
        "workflow_steps": _parse_workflow_steps(fact_dict),
        "obligations": [
            {
                "code": ob.code,
                "title": ob.title,
                "description": ob.description,
                "status": ob.status
            }
            for ob in obligations
        ]
    }

@router.post("/projects/{project_id}/generate-report")
async def generate_report(
    project_id: int,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Generate PDF compliance report for a completed assessment."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user owns this project
    user_id = get_user_id_optional(authorization)
    if user_id and project.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    # Get all facts and obligations
    facts = db.query(Fact).filter(Fact.project_id == project_id).all()
    obligations = db.query(Obligation).filter(Obligation.project_id == project_id).all()
    
    # Build report data
    report_data = {
        "model_tested": project.name,
        "risk_level": project.risk_level,
        "compliance_score": 85 if project.risk_level == "LIMITED" else (75 if project.risk_level == "HIGH" else 90),
        "metric_breakdown": [
            {"name": "Risk Classification", "score": 100 if project.risk_level else 0},
            {"name": "State Machine Completion", "score": 100 if project.interview_state == "ASSESSMENT" else 50},
        ],
        "details": [],
        "obligations": [
            {
                "code": ob.code,
                "title": ob.title,
                "description": ob.description,
                "status": ob.status
            }
            for ob in obligations
        ],
        "facts": {f.key: f.value for f in facts}
    }
    
    try:
        # Check if report generation is available
        if create_compliance_cert is None:
            raise HTTPException(status_code=503, detail="Report generation not available. Please install reportlab: pip install reportlab")
        
        # Generate PDF
        pdf_bytes = create_compliance_cert(report_data)
        
        # Return as downloadable file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="compliance_report_{project.name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")