from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import the new router
from routers import interview 
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

# Register the new Interview/Governance Router
app.include_router(interview.router, prefix="/interview", tags=["Governance"])

@app.get("/")
def read_root():
    return {"status": "EU AI Act Governance System Active"}