from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import routers
from routers import interview, audit, workflow, dashboard
from database import init_db

# Initialize DB on startup
init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(interview.router, prefix="/interview", tags=["Governance"])
app.include_router(audit.router, prefix="/audit", tags=["Audit"])
app.include_router(workflow.router, prefix="/interview", tags=["Workflows"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

@app.get("/")
def read_root():
    return {"status": "EU AI Act Governance System Active"}