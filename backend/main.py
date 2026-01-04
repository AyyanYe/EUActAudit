from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import audit, compliance

app = FastAPI(title="EU AI Act Auditor API")

# Allow your React Frontend (Port 5173) to hit this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit.router)
app.include_router(compliance.router)

@app.get("/")
def health_check():
    return {"status": "Audit Engine Online", "version": "1.0"}