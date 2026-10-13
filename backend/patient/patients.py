from sqlalchemy.orm import Session

from databases.models import Patients


def get_patient_by_phone(db: Session, phone: str):
    return db.query(Patients).filter(Patients.phone == phone).first()


def create_patient(db: Session, name: str, age: int, gender: str, phone: str) -> Patients:
    patient = Patients(name=name, age=age, gender=gender, phone=phone)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update_patient_details(
    db: Session,
    patient_id: int,
    *,
    name: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    phone: str | None = None,
) -> Patients | None:
    patient = db.query(Patients).filter(Patients.id == patient_id).first()
    if patient is None:
        return None

    if name is not None:
        patient.name = name
    if age is not None:
        patient.age = age
    if gender is not None:
        patient.gender = gender
    if phone is not None:
        patient.phone = phone

    db.commit()
    db.refresh(patient)
    return patient
