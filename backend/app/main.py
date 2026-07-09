from fastapi import FastAPI
from triage.router import router as triage_router
app= FastAPI()
app.include_router(triage_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

