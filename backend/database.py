# backend/database.py
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# New DB file to avoid conflicts with the old one
DATABASE_URL = "sqlite:///./eu_ai_act_2025.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Project(Base):
    """
    Represents one AI System being assessed.
    This is the 'Profile' that persists over time.
    """
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Untitled AI Project")
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    # The 'State' of the system
    risk_level = Column(String, default="Unknown") # e.g. "HIGH", "LIMITED", "UNACCEPTABLE"
    status = Column(String, default="Draft")       # e.g. "Assessment In Progress"
    
    # Relationships
    facts = relationship("Fact", back_populates="project", cascade="all, delete-orphan")
    obligations = relationship("Obligation", back_populates="project", cascade="all, delete-orphan")
    logs = relationship("InterviewLog", back_populates="project")

class Fact(Base):
    """
    A specific piece of knowledge extracted from the chat.
    We separate 'what user said' (Value) from 'how sure we are' (Confidence).
    """
    __tablename__ = "facts"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    key = Column(String, index=True)    # e.g., "domain", "role", "uses_personal_data"
    value = Column(String)              # e.g., "recruitment", "provider"
    confidence = Column(Integer)        # 1-100 (Low confidence triggers clarification questions)
    source = Column(String)             # "user_input" or "inference"
    
    project = relationship("Project", back_populates="facts")

class Obligation(Base):
    """
    A specific legal requirement triggered by the Rules Engine.
    """
    __tablename__ = "obligations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    code = Column(String)               # e.g. "ART_16", "ART_50"
    title = Column(String)
    description = Column(Text)
    status = Column(String, default="PENDING") # "MET", "UNMET", "PENDING"
    
    project = relationship("Project", back_populates="obligations")

class InterviewLog(Base):
    """Stores the raw chat history for context."""
    __tablename__ = "interview_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    sender = Column(String) # "user" or "bot"
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    
    project = relationship("Project", back_populates="logs")

# Initialization Logic
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()