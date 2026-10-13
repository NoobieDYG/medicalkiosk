import json
import time
import uuid

from redis.exceptions import RedisError

from databases.redis_client import redis_client

SESSION_TTL_SECONDS = 1800
SESSION_KEY_PREFIX = "triage_session:"
_memory_sessions: dict[str, tuple[float, dict]] = {}
_redis_available: bool | None = None


def _get_memory_session(session_id: str):
    entry = _memory_sessions.get(session_id)
    if entry is None:
        return None

    expires_at, state = entry
    if expires_at <= time.monotonic():
        _memory_sessions.pop(session_id, None)
        return None
    return state


def create_session(hospital_id: int | None = None, kiosk_id: int | None = None) -> str:
    session_id = str(uuid.uuid4())
    state = {
        "stage": "greeting",
        "messages": [],
        "patient_data": {
            "name": None,
            "age": None,
            "gender": None,
            "phone": None,
            "is_existing": False,
        },
        "symptom_data": {
            "symptom": None,
            "body_part": None,
            "duration": None,
            "severity": None,
            "red_flags": [],
        },
        "patient_id": None,
        "department": None,
        "icd_code": None,
        "ai_impression": None,
        "doctor_options": [],
        "selected_doctor_id": None,
        "hospital_id": hospital_id,
        "kiosk_id": kiosk_id,
    }
    save_session(session_id, state)
    return session_id


def get_session(session_id: str):
    global _redis_available
    if _redis_available is False:
        return _get_memory_session(session_id)
    try:
        raw = redis_client.get(f"{SESSION_KEY_PREFIX}{session_id}")
        _redis_available = True
        if raw:
            return json.loads(raw)
    except RedisError:
        _redis_available = False
    return _get_memory_session(session_id)


def save_session(session_id: str, state: dict) -> None:
    global _redis_available
    if _redis_available is False:
        _memory_sessions[session_id] = (time.monotonic() + SESSION_TTL_SECONDS, state)
        return
    try:
        redis_client.setex(f"{SESSION_KEY_PREFIX}{session_id}", SESSION_TTL_SECONDS, json.dumps(state))
        _redis_available = True
        _memory_sessions.pop(session_id, None)
    except RedisError:
        _redis_available = False
        _memory_sessions[session_id] = (time.monotonic() + SESSION_TTL_SECONDS, state)


def delete_session(session_id: str) -> None:
    global _redis_available
    _memory_sessions.pop(session_id, None)
    if _redis_available is False:
        return
    try:
        redis_client.delete(f"{SESSION_KEY_PREFIX}{session_id}")
    except RedisError:
        _redis_available = False
