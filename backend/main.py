import os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("CRITICAL ERROR: OPENAI_API_KEY is missing from environment!")
else:
    print("OPENAI_API_KEY detected.")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 2. NOW import the routers (Safe because env vars are loaded)
from routers.audit import router as audit_router
from routers.compliance import router as compliance_router
from database import init_db

app = FastAPI(title="EU AI Act Auditor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit_router)
app.include_router(compliance_router)

@app.on_event("startup")
def startup_event():
    init_db()
    print("Database initialized (audit_records.db)")

@app.get("/")
def health_check():
    return {"status": "Audit Engine Online", "version": "1.0"}