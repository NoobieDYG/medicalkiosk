import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from databases.db import get_db
from triage.logic import process_turn
from triage.router import finalize_triage
from triage.session import create_session, delete_session, get_session, save_session
from triage.stages import TriageStage
from triage.voice import synthesize_speech, transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(tags=["triage-ws"])


async def send_assistant_reply(
    websocket: WebSocket,
    state: dict,
    reply: str,
    doctor_options=None,
    *,
    send_confirmation_prompt: bool = True,
):
    await websocket.send_json({"type": "assistant_text", "text": reply, "stage": state["stage"]})

    if doctor_options:
        await websocket.send_json({"type": "structured_data", "kind": "doctor_list", "items": doctor_options})

    if send_confirmation_prompt and state["stage"] == TriageStage.READY_TO_FINALIZE.value:
        await websocket.send_json({"type": "awaiting_confirmation", "stage": state["stage"]})

    try:
        audio_bytes = synthesize_speech(reply)
        await websocket.send_bytes(audio_bytes)
    except Exception:
        logger.exception("TTS synthesis failed, continuing with text-only reply")


async def send_token(websocket: WebSocket, db: Session, session_id: str, state: dict) -> None:
    result = finalize_triage(db, session_id, state)
    await websocket.send_json(
        {
            "type": "token_issued",
            "token": {
                "token_number": result.token_number,
                "doctor_name": result.doctor_name,
                "department": result.department,
                "visit_id": result.visit_id,
                "slip_id": result.slip_id,
            },
        }
    )


async def handle_patient_turn(websocket: WebSocket, db: Session, session_id: str, state: dict, text: str) -> bool:
    state["messages"].append({"role": "patient", "text": text})
    result = process_turn(db, state, text)
    state["messages"].append({"role": "assistant", "text": result.reply})
    save_session(session_id, state)

    await send_assistant_reply(
        websocket,
        state,
        result.reply,
        result.doctor_options,
        send_confirmation_prompt=not result.finalize_requested,
    )

    if not result.finalize_requested:
        return False

    try:
        await send_token(websocket, db, session_id, state)
        return True
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "detail": exc.detail})
        return False


@router.websocket("/ws/kiosk/{hospital_id}/{kiosk_id}")
async def triage_ws(hospital_id: int, kiosk_id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()

    session_id = create_session(hospital_id=hospital_id, kiosk_id=kiosk_id)
    greeting = "Hi, I'm here to help. What's bothering you today?"

    await websocket.send_json(
        {"type": "assistant_text", "session_id": session_id, "text": greeting, "stage": TriageStage.GREETING.value}
    )
    try:
        await websocket.send_bytes(synthesize_speech(greeting))
    except Exception:
        logger.exception("TTS synthesis failed for greeting, continuing with text-only")

    try:
        while True:
            raw = await websocket.receive()

            if raw["type"] == "websocket.disconnect":
                raise WebSocketDisconnect()

            state = get_session(session_id)
            if state is None:
                await websocket.send_json({"type": "error", "detail": "Session expired. Please reconnect."})
                break

            # Binary frame: one recorded mic utterance.
            if raw.get("bytes") is not None:
                text = transcribe_audio(raw["bytes"])

                if not text:
                    await websocket.send_json({"type": "error", "detail": "I did not catch that. Please try again."})
                    continue

                finalized = await handle_patient_turn(websocket, db, session_id, state, text)
                if finalized:
                    break
                continue

            # Text frame: JSON control message.
            if raw.get("text") is None:
                continue

            payload = json.loads(raw["text"])
            msg_type = payload.get("type")

            if msg_type == "message":
                text = payload.get("text", "")
                finalized = await handle_patient_turn(websocket, db, session_id, state, text)
                if finalized:
                    break

            elif msg_type == "selection":
                doctor_id = payload.get("id")
                match = next((doctor for doctor in state["doctor_options"] if doctor.get("id") == doctor_id), None)

                if match is None:
                    await websocket.send_json(
                        {"type": "error", "detail": "That doctor is not in the current list. Please pick again."}
                    )
                    continue

                state["selected_doctor_id"] = doctor_id
                state["stage"] = TriageStage.READY_TO_FINALIZE.value
                reply = f"Great - you are booked with Dr. {match.get('name', 'the selected doctor')}. Confirm to get your token."
                state["messages"].append({"role": "assistant", "text": reply})
                save_session(session_id, state)

                await send_assistant_reply(websocket, state, reply, doctor_options=None)

            elif msg_type == "end":
                try:
                    await send_token(websocket, db, session_id, state)
                except HTTPException as exc:
                    await websocket.send_json({"type": "error", "detail": exc.detail})
                    continue
                break

            else:
                await websocket.send_json({"type": "error", "detail": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        logger.info("Client disconnected from triage session %s", session_id)
        delete_session(session_id)
    except Exception:
        logger.exception("Unexpected error in triage session %s", session_id)
        delete_session(session_id)
        try:
            await websocket.send_json({"type": "error", "detail": "Internal server error."})
        except RuntimeError:
            pass
