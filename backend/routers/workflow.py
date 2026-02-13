"""
Workflow Router: Handles CRUD operations for Workflows within Projects.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db, Project, Workflow, InterviewLog
from core.auth import get_user_id_optional

router = APIRouter()

class CreateWorkflowRequest(BaseModel):
    name: str
    description: Optional[str] = None

class UpdateWorkflowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    risk_level: Optional[str] = None

@router.post("/projects/{project_id}/workflows")
def create_workflow(
    project_id: int,
    request: CreateWorkflowRequest,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Create a new workflow for a project."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user owns this project (if authenticated)
    user_id = get_user_id_optional(authorization)
    if user_id and project.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    # Create workflow
    new_workflow = Workflow(
        project_id=project_id,
        name=request.name,
        description=request.description,
        risk_level="Unknown"
    )
    db.add(new_workflow)
    db.commit()
    db.refresh(new_workflow)
    
    return {
        "id": new_workflow.id,
        "project_id": new_workflow.project_id,
        "name": new_workflow.name,
        "description": new_workflow.description,
        "risk_level": new_workflow.risk_level,
        "created_at": new_workflow.created_at.isoformat() if new_workflow.created_at else None
    }

@router.get("/projects/{project_id}/workflows")
def list_workflows(
    project_id: int,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get all workflows for a project."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user owns this project (if authenticated)
    user_id = get_user_id_optional(authorization)
    if user_id and project.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    # Get all workflows
    workflows = db.query(Workflow).filter(Workflow.project_id == project_id).order_by(Workflow.created_at).all()
    
    return {
        "workflows": [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "risk_level": wf.risk_level,
                "created_at": wf.created_at.isoformat() if wf.created_at else None,
                "message_count": db.query(InterviewLog).filter(
                    InterviewLog.workflow_id == wf.id
                ).count()
            }
            for wf in workflows
        ]
    }

@router.get("/projects/{project_id}/workflows/{workflow_id}")
def get_workflow(
    project_id: int,
    workflow_id: int,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get a specific workflow and its messages."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user owns this project (if authenticated)
    user_id = get_user_id_optional(authorization)
    if user_id and project.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    # Get workflow
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.project_id == project_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Get messages for this workflow
    logs = db.query(InterviewLog).filter(
        InterviewLog.workflow_id == workflow_id
    ).order_by(InterviewLog.timestamp.asc()).all()
    
    return {
        "workflow": {
            "id": workflow.id,
            "project_id": workflow.project_id,
            "name": workflow.name,
            "description": workflow.description,
            "risk_level": workflow.risk_level,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None
        },
        "messages": [
            {
                "sender": log.sender,
                "message": log.message,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            }
            for log in logs
        ]
    }

@router.put("/projects/{project_id}/workflows/{workflow_id}")
def update_workflow(
    project_id: int,
    workflow_id: int,
    request: UpdateWorkflowRequest,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Update a workflow."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user owns this project (if authenticated)
    user_id = get_user_id_optional(authorization)
    if user_id and project.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    # Get workflow
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.project_id == project_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Update fields
    if request.name is not None:
        workflow.name = request.name
    if request.description is not None:
        workflow.description = request.description
    if request.risk_level is not None:
        workflow.risk_level = request.risk_level
    
    db.commit()
    db.refresh(workflow)
    
    return {
        "id": workflow.id,
        "project_id": workflow.project_id,
        "name": workflow.name,
        "description": workflow.description,
        "risk_level": workflow.risk_level,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None
    }

@router.delete("/projects/{project_id}/workflows/{workflow_id}")
def delete_workflow(
    project_id: int,
    workflow_id: int,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Delete a workflow (and all its messages)."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user owns this project (if authenticated)
    user_id = get_user_id_optional(authorization)
    if user_id and project.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    # Get workflow
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.project_id == project_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Delete workflow (cascade will delete messages)
    db.delete(workflow)
    db.commit()
    
    return {"message": "Workflow deleted successfully"}

