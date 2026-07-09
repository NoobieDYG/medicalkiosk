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