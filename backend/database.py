# backend/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    JSON,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

load_dotenv()

# Database URL: use DATABASE_URL env var for Neon/PostgreSQL, fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./eu_ai_act_2025.db")

Base = declarative_base()

# SQLite requires check_same_thread=False; PostgreSQL does not need it
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # test connections before use (fixes Neon idle disconnects)
    pool_recycle=300,  # recycle connections every 5 minutes
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Project(Base):
    """
    Represents one AI System being assessed.
    This is the 'Profile' that persists over time.
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # Clerk user ID
    name = Column(String, default="Untitled AI Project")
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # The 'State' of the system
    risk_level = Column(
        String, default="Unknown"
    )  # e.g. "HIGH", "LIMITED", "UNACCEPTABLE"
    status = Column(String, default="Draft")  # e.g. "Assessment In Progress"
    interview_state = Column(
        String, default="INIT"
    )  # State machine state: INIT, INTAKE, DISCOVERY, CHECKPOINT, ASSESSMENT
    confidence_level = Column(String, default="LOW")  # Confidence: LOW, MEDIUM, HIGH
    compliance_status = Column(
        String, default="PENDING"
    )  # "PENDING", "COMPLIANT", "NON_COMPLIANT", "TERMINATED"

    # Relationships
    facts = relationship("Fact", back_populates="project", cascade="all, delete-orphan")
    obligations = relationship(
        "Obligation", back_populates="project", cascade="all, delete-orphan"
    )
    logs = relationship(
        "InterviewLog", back_populates="project", order_by="InterviewLog.timestamp"
    )
    workflows = relationship(
        "Workflow", back_populates="project", cascade="all, delete-orphan"
    )


class Fact(Base):
    """
    A specific piece of knowledge extracted from the chat.
    We separate 'what user said' (Value) from 'how sure we are' (Confidence).
    """

    __tablename__ = "facts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    key = Column(String, index=True)  # e.g., "domain", "role", "uses_personal_data"
    value = Column(String)  # e.g., "recruitment", "provider"
    confidence = Column(
        Integer
    )  # 1-100 (Low confidence triggers clarification questions)
    source = Column(String)  # "user_input" or "inference"

    project = relationship("Project", back_populates="facts")


class Obligation(Base):
    """
    A specific legal requirement triggered by the Rules Engine.
    """

    __tablename__ = "obligations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    code = Column(String)  # e.g. "ART_16", "ART_50"
    title = Column(String)
    description = Column(Text)
    status = Column(String, default="PENDING")  # "MET", "UNMET", "PENDING"

    project = relationship("Project", back_populates="obligations")


class Workflow(Base):
    """
    Represents a distinct workflow within a Project.
    Each workflow has its own chat history and can have its own risk assessment.
    """

    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    risk_level = Column(String, default="Unknown")
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    project = relationship("Project", back_populates="workflows")
    logs = relationship(
        "InterviewLog", back_populates="workflow", cascade="all, delete-orphan"
    )


class InterviewLog(Base):
    """Stores the raw chat history for context."""

    __tablename__ = "interview_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    workflow_id = Column(
        Integer, ForeignKey("workflows.id"), nullable=True
    )  # NULL = General/Default chat
    sender = Column(String)  # "user" or "bot"
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)

    project = relationship("Project", back_populates="logs")
    workflow = relationship("Workflow", back_populates="logs")


# ===== Audit tables (consolidated from separate audit_records.db) =====


class AuditRun(Base):
    """
    Records of bias/fairness audits run against AI models.
    Previously stored in a separate audit_records.db SQLite file.
    """

    __tablename__ = "audit_runs"

    id = Column(Integer, primary_key=True, index=True)
    model = Column(String)
    risk_level = Column(String)
    score = Column(Integer)
    details = Column(Text)  # JSON string
    user_id = Column(String, index=True, default="anonymous")
    system_prompt = Column(Text)
    timestamp = Column(String)  # ISO format string


# Initialization Logic
def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
