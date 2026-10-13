import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from databases.models import Doctors, Patients, Queue, Visits


def get_owned_visit(db: Session, visit_id: int, doctor: Doctors) -> Visits:
    visit = (
        db.query(Visits)
        .filter(
            Visits.id == visit_id,
            Visits.doctor_id == doctor.id,
            Visits.hospital_id == doctor.hospital_id,
        )
        .first()
    )
    if visit is None:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit


def build_slip(db: Session, visit: Visits) -> dict:

    patient = db.get(Patients, visit.patient_id)
    doctor = db.get(Doctors, visit.doctor_id)
    queue = db.query(Queue).filter(Queue.visit_id == visit.id).first()

    return {
        "clinic": {
            "name": os.getenv("CLINIC_NAME", ""),
            "address": os.getenv("CLINIC_ADDRESS", ""),
            "phone": os.getenv("CLINIC_PHONE", ""),
        },
        "token_number": queue.token_number if queue else None,
        "issued_at": visit.created_at.isoformat() + "Z" if visit.created_at else None,
        "patient": {
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
        },
        "doctor": {
            "name": doctor.name,
            "department": doctor.department,
        },
        "diagnosis": visit.diagnosis,
        "follow_ups": visit.follow_ups,
        "prescription": visit.prescription,
        "status": "completed" if visit.completed_at else "open",
    }