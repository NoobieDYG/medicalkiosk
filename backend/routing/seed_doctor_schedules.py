from datetime import time

from databases.db import SessionLocal
from databases.models import DoctorSchedules

SCHEDULE_SEED_DATA = [
    (1, 0, time(9, 0), time(17, 0)),
    (1, 1, time(9, 0), time(17, 0)),
    (1, 2, time(9, 0), time(17, 0)),
    (1, 3, time(9, 0), time(17, 0)),
    (1, 4, time(9, 0), time(17, 0)),
]


def seed():
    db = SessionLocal()
    db.query(DoctorSchedules).delete()
    for doctor_id, day_of_week, start_time, end_time in SCHEDULE_SEED_DATA:
        db.add(DoctorSchedules(doctor_id=doctor_id, day_of_week=day_of_week, start_time=start_time, end_time=end_time))
    db.commit()
    db.close()
    print(f"Seeded {len(SCHEDULE_SEED_DATA)} schedule rows.")


if __name__ == "__main__":
    seed()