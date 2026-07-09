from datetime import datetime

from sqlalchemy.orm import Session

from databases.models import Doctors, DoctorSchedules


def get_available_doctors_by_department(db: Session, department: str):
    now = datetime.now()
    today = now.weekday()  # Monday=0 ... Sunday=6
    current_time = now.time()

    return (
        db.query(Doctors)
        .join(DoctorSchedules, DoctorSchedules.doctor_id == Doctors.id)
        .filter(
            Doctors.department == department,
            Doctors.available == True,  # noqa: E712 -- manual override (sick/leave), separate from the weekly schedule
            DoctorSchedules.day_of_week == today,
            DoctorSchedules.start_time <= current_time,
            DoctorSchedules.end_time >= current_time,
        )
        .distinct()
        .all()
    )


def get_doctor_by_id(db: Session, doctor_id: int):
    return db.query(Doctors).filter(Doctors.id == doctor_id).first()