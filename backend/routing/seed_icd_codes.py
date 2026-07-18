from databases.db import SessionLocal
from databases.models import ICDCodes
from triage.embeddings import get_embedding

ICD_SEED_DATA = [
    ("M25.561", "Pain in right knee", "Orthopedics"),
    ("M25.562", "Pain in left knee", "Orthopedics"),
    ("M54.5", "Low back pain", "Orthopedics"),
    ("M19.90", "Joint pain, unspecified", "Orthopedics"),
    ("I20.9", "Chest pain, angina suspected", "Cardiology"),
    ("R07.9", "Chest pain, unspecified", "Cardiology"),
    ("I10", "High blood pressure, hypertension", "Cardiology"),
    ("R00.2", "Palpitations, irregular heartbeat", "Cardiology"),
    ("R50.9", "Fever, unspecified", "General Medicine"),
    ("R05", "Cough", "General Medicine"),
    ("J00", "Common cold, runny nose", "General Medicine"),
    ("R53.83", "Fatigue, tiredness, weakness", "General Medicine"),
    ("K59.1", "Diarrhea", "General Medicine"),
    ("R51.9", "Headache", "Neurology"),
    ("G43.9", "Migraine", "Neurology"),
    ("R42", "Dizziness, vertigo", "Neurology"),
    ("L30.9", "Skin rash, itching", "Dermatology"),
    ("L70.9", "Acne", "Dermatology"),
    ("H66.9", "Ear pain, ear infection", "ENT"),
    ("J02.9", "Sore throat", "ENT"),
    ("K30", "Indigestion, stomach pain", "Gastroenterology"),
    ("K21.9", "Acid reflux, heartburn", "Gastroenterology"),
    ("N39.0", "Urinary tract infection symptoms", "Urology"),
    ("H57.1", "Eye pain", "Ophthalmology"),
]


def seed():
    db = SessionLocal()
    db.query(ICDCodes).delete()
    for code, description, department in ICD_SEED_DATA:
        db.add(ICDCodes(code=code, description=description, department=department, embedding=get_embedding(description)))
    db.commit()
    db.close()
    print(f"Seeded {len(ICD_SEED_DATA)} ICD codes.")


if __name__ == "__main__":
    seed()