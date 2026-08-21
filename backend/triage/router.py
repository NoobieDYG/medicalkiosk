from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from databases.db import get_db
from doctor.doctors import get_doctor_by_id
from databases.models import Queue, Triage, Visits
from triage.logic import process_message
from triage.schemas import (
    TriageEndRequest,
    TriageEndResponse,
    TriageMessageRequest,
    TriageMessageResponse,
    TriageStartResponse,
)
from triage.session import create_session, delete_session, get_session, save_session
from triage.stages import TriageStage

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/start", response_model=TriageStartResponse)
def start_triage():
    session_id = create_session()
    return TriageStartResponse(
        session_id=session_id,
        reply="Hi, I'm here to help. What's bothering you today?",
        stage=TriageStage.GREETING.value,
    )


@router.post("/message", response_model=TriageMessageResponse)
def send_message(payload: TriageMessageRequest, db: Session = Depends(get_db)):
    state = get_session(payload.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session expired or not found. Call /triage/start again.")

    state["messages"].append({"role": "patient", "text": payload.message})
    reply, doctor_options = process_message(db, state, payload.message)
    state["messages"].append({"role": "assistant", "text": reply})
    save_session(payload.session_id, state)

    return TriageMessageResponse(reply=reply, stage=state["stage"], doctor_options=doctor_options)


def finalize_triage(db: Session, session_id: str, state: dict) -> TriageEndResponse:
    """
    Shared finalize logic used by both the REST /triage/end endpoint and the
    WebSocket flow. Creates the Visit, Queue token, and Triage transcript
    record, then deletes the Redis session. Raises HTTPException if the
    session isn't actually ready to finalize.
    """
    if state["stage"] != TriageStage.READY_TO_FINALIZE.value:
        raise HTTPException(status_code=400, detail="Triage isn't finished yet — doctor hasn't been confirmed.")

    doctor = get_doctor_by_id(db, state["selected_doctor_id"])
    symptom_summary = ", ".join(f"{k}: {v}" for k, v in state["symptom_data"].items() if v)

    visit = Visits(
        patient_id=state["patient_id"],
        doctor_id=doctor.id,
        symptom_summary=symptom_summary,
        department=state["department"],
        icd_code=state.get("icd_code"),
        ai_impression=state.get("ai_impression"),
        status="waiting",
        hospital_id=state.get("hospital_id"),
        kiosk_id=state.get("kiosk_id"),
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)

    last_token = (
        db.query(Queue)
        .filter(Queue.status == "waiting")
        .order_by(Queue.token_number.desc())
        .first()
    )
    next_token = (last_token.token_number + 1) if last_token else 1

    db.add(Queue(visit_id=visit.id, token_number=next_token, status="waiting"))
    db.add(Triage(visit_id=visit.id, conversation_json=state["messages"]))
    db.commit()

    delete_session(session_id)

    return TriageEndResponse(
        token_number=next_token,
        doctor_name=doctor.name,
        department=state["department"],
        visit_id=visit.id,
    )


@router.post("/end", response_model=TriageEndResponse)
def end_triage(payload: TriageEndRequest, db: Session = Depends(get_db)):
    state = get_session(payload.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session expired or not found.")

    return finalize_triage(db, payload.session_id, state)