import json
import uuid

from databases.redis_client import redis_client  

SESSION_TTL_SECONDS = 1800  
SESSION_KEY_PREFIX = "triage_session:"


def create_session() -> str:
    session_id = str(uuid.uuid4())
    state = {
        "stage": "greeting",
        "messages": [],
        "symptom_data": {},
        "patient_id": None,
        "department": None,
        "icd_code": None,
        "ai_impression": None,
        "doctor_options": [],
        "selected_doctor_id": None,
    }
    save_session(session_id, state)
    return session_id


def get_session(session_id: str):
    raw = redis_client.get(f"{SESSION_KEY_PREFIX}{session_id}")
    return json.loads(raw) if raw else None


def save_session(session_id: str, state: dict) -> None:
    redis_client.setex(f"{SESSION_KEY_PREFIX}{session_id}", SESSION_TTL_SECONDS, json.dumps(state))


def delete_session(session_id: str) -> None:
    redis_client.delete(f"{SESSION_KEY_PREFIX}{session_id}")