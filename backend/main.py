from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import audit, compliance 

load_dotenv()

# Initialize the Database (if not exists)
import database
database.init_db()

app = FastAPI()

# Enable CORS (Allows Frontend to talk to Backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REGISTER ROUTERS ---
# This connects your "audit.py" and "compliance.py" to the web server
app.include_router(audit.router, prefix="/audit", tags=["Audit"])
app.include_router(compliance.router)

@app.get("/")
def read_root():
    return {"status": "AuditGenius Backend is Running"}