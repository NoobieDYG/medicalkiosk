from fastapi import FastAPI
from triage.router import router as triage_router
from triage.ws_router import router as ws_router
from dashboard.routes_slip import slip_router
from dashboard.routes_doctor import auth_router, doctor_router
from fastapi.middleware.cors import CORSMiddleware
app= FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://192.168.1.20:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(triage_router)
app.include_router(ws_router)
app.include_router(slip_router)
app.include_router(auth_router)
app.include_router(doctor_router)
@app.get("/health")
def health_check():
    return {"status": "ok"}

