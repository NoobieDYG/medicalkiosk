import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    get_current_doctor,
    hash_password,
    verify_password,
)
from databases.db import get_db
from databases.models import Doctors, Patients, Queue, Visits
from .slip import build_slip, get_owned_visit

auth_router = APIRouter(prefix="/auth", tags=["auth"])
doctor_router = APIRouter(prefix="/doctor", tags=["doctor"])




class LoginRequest(BaseModel):
    email: str
    password: str = Field(max_length=72)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=15)


class PasswordChange(BaseModel):
    old_password: str = Field(max_length=72)
    new_password: str = Field(min_length=8, max_length=72)


class SlipUpdate(BaseModel):
    diagnosis: str | None = Field(default=None, max_length=5000)
    follow_ups: str | None = Field(default=None, max_length=5000)
    prescription: str | None = Field(default=None, max_length=5000)


def doctor_to_dict(doctor: Doctors) -> dict:
    return {
        "id": doctor.id,
        "name": doctor.name,
        "department": doctor.department,
        "phone": doctor.phone,
        "email": doctor.email,
    }


# ---------- auth ----------

@auth_router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    doctor = (
        db.query(Doctors)
        .filter(func.lower(Doctors.email) == body.email.strip().lower())
        .first()
    )
    # Same message for "no such email" and "wrong password" on purpose.
    if (
        doctor is None
        or not doctor.password_hash
        or not verify_password(body.password, doctor.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "access_token": create_access_token(doctor.id),
        "token_type": "bearer",
        "doctor": doctor_to_dict(doctor),
    }


# ---------- profile ----------

@doctor_router.get("/me")
def get_me(doctor: Doctors = Depends(get_current_doctor)):
    return doctor_to_dict(doctor)


@doctor_router.patch("/me")
def update_me(
    body: ProfileUpdate,
    doctor: Doctors = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    data = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="Nothing to update")
    for field, value in data.items():
        setattr(doctor, field, value.strip())
    db.commit()
    db.refresh(doctor)
    return doctor_to_dict(doctor)


@doctor_router.post("/me/password")
def change_password(
    body: PasswordChange,
    doctor: Doctors = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    if not doctor.password_hash or not verify_password(body.old_password, doctor.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    doctor.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}


# ---------- token lists ----------

@doctor_router.get("/tokens")
def list_tokens(
    scope: Literal["current", "past"] = "current",
    doctor: Doctors = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Queue, Visits, Patients)
        .join(Visits, Queue.visit_id == Visits.id)
        .join(Patients, Visits.patient_id == Patients.id)
        .filter(
            Visits.doctor_id == doctor.id,
            Visits.hospital_id == doctor.hospital_id,
        )
    )
    if scope == "current":
        q = q.filter(Queue.status != "completed").order_by(Queue.token_number.asc())
    else:
        q = (
            q.filter(Queue.status == "completed")
            .order_by(Visits.completed_at.desc())
            .limit(50)
        )

    return [
        {
            "visit_id": visit.id,
            "token_number": queue.token_number,
            "patient_name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "department": visit.department,
            "status": queue.status,
            "created_at": visit.created_at.isoformat() if visit.created_at else None,
            "completed_at": visit.completed_at.isoformat() if visit.completed_at else None,
        }
        for queue, visit, patient in q.all()
    ]


# ---------- visit detail ----------

def visit_detail(db: Session, visit: Visits) -> dict:
    patient = db.get(Patients, visit.patient_id)
    return {
        "visit_id": visit.id,
        "patient": {
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "phone": patient.phone,
        },
        "department": visit.department,
        "symptom_summary": visit.symptom_summary,
        "ai_impression": visit.ai_impression,
        "icd_code": visit.icd_code,
        "slip": build_slip(db, visit),
    }


@doctor_router.get("/visits/{visit_id}")
def get_visit(
    visit_id: int,
    doctor: Doctors = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    visit = get_owned_visit(db, visit_id, doctor)
    return visit_detail(db, visit)


# ---------- saving slip sections / completing ----------

@doctor_router.patch("/visits/{visit_id}/slip")
def save_slip_section(
    visit_id: int,
    body: SlipUpdate,
    doctor: Doctors = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    visit = get_owned_visit(db, visit_id, doctor)
    if visit.completed_at is not None:
        raise HTTPException(status_code=409, detail="Visit is completed and can no longer be edited")

    data = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="Nothing to save")

    for field, value in data.items():
        setattr(visit, field, value.strip())
    db.commit()
    db.refresh(visit)
    return build_slip(db, visit)


@doctor_router.post("/visits/{visit_id}/complete")
def complete_visit(
    visit_id: int,
    doctor: Doctors = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    visit = get_owned_visit(db, visit_id, doctor)
    if visit.completed_at is None:
        visit.completed_at = datetime.datetime.now(datetime.UTC)
        visit.status = "completed"
        queue = db.query(Queue).filter(Queue.visit_id == visit.id).first()
        if queue is not None:
            queue.status = "completed"
        db.commit()
        db.refresh(visit)
    return visit_detail(db, visit)