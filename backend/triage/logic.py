import logging

from sqlalchemy.orm import Session

from doctor.doctors import get_available_doctors_by_department
from patient.patients import create_patient, get_patient_by_phone, update_patient_details
from routing.icd_routing import map_symptom_to_department
from triage.agent import (
    TriageTurnResult,
    answer_question,
    normalize_phone,
    resolve_doctor_choice,
    understand_turn,
)
from triage.prompts import extract_symptom_data, generate_ai_impression
from triage.stages import TriageStage

logger = logging.getLogger(__name__)

REQUIRED_SYMPTOM_FIELDS = ["symptom", "body_part", "duration", "severity"]
FOLLOW_UP_QUESTIONS = {
    "symptom": "Could you tell me what is bothering you today?",
    "body_part": "Which part of your body is affected?",
    "duration": "How long has this been going on?",
    "severity": "On a scale of 1 to 10, how bad is it?",
}
PATIENT_FIELD_QUESTIONS = {
    "phone": "Can I get your phone number to pull up your records?",
    "name": "I do not see that phone number in our records yet. What is your full name?",
    "age": "Thanks. What is your age?",
    "gender": "And your gender? You can say male, female, or other.",
}


def ensure_triage_state(state: dict) -> dict:
    patient_data = state.setdefault("patient_data", {})
    patient_data.setdefault("name", state.get("pending_name"))
    patient_data.setdefault("age", state.get("pending_age"))
    patient_data.setdefault("gender", None)
    patient_data.setdefault("phone", state.get("pending_phone"))
    patient_data.setdefault("is_existing", False)

    symptom_data = state.setdefault("symptom_data", {})
    for field in REQUIRED_SYMPTOM_FIELDS:
        symptom_data.setdefault(field, None)
    symptom_data.setdefault("red_flags", [])

    state.setdefault("messages", [])
    state.setdefault("doctor_options", [])
    state.setdefault("selected_doctor_id", None)
    state.setdefault("department", None)
    state.setdefault("icd_code", None)
    state.setdefault("ai_impression", None)
    state.setdefault("stage", TriageStage.GREETING.value)
    return state


def get_missing_fields(symptom_data: dict) -> list:
    return [field for field in REQUIRED_SYMPTOM_FIELDS if not symptom_data.get(field)]


def get_missing_patient_fields(state: dict) -> list:
    patient_data = state["patient_data"]
    if state.get("patient_id"):
        return []
    if not patient_data.get("phone"):
        return ["phone"]
    return [field for field in ("name", "age", "gender") if not patient_data.get(field)]


def build_triage_impression(symptom_data: dict) -> str:
    facts = ", ".join(f"{key}: {value}" for key, value in symptom_data.items() if value)
    if not facts:
        return "No symptom details were captured. For doctor review only - not a diagnosis."

    try:
        return generate_ai_impression(symptom_data)
    except Exception:
        logger.exception("AI impression generation failed; using deterministic fallback")
        return f"Patient reports {facts}. For doctor review only - not a diagnosis."


def _stage_for_missing_symptoms(missing: list) -> str:
    return TriageStage.COLLECTING_SYMPTOMS.value if missing else TriageStage.IDENTIFYING_PATIENT.value


def _set_patient_from_record(state: dict, patient) -> None:
    state["patient_id"] = patient.id
    state["patient_data"] = {
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "phone": patient.phone,
        "is_existing": True,
    }
    state["pending_phone"] = patient.phone
    state["pending_name"] = patient.name
    state["pending_age"] = patient.age


def _apply_patient_updates(db: Session, state: dict, updates: dict) -> list[str]:
    changed = []
    patient_data = state["patient_data"]
    current_patient_id = state.get("patient_id")

    phone = normalize_phone(updates.get("phone"))
    if phone and phone != normalize_phone(patient_data.get("phone")):
        patient_data["phone"] = phone
        state["pending_phone"] = phone
        changed.append("phone")

        patient = get_patient_by_phone(db, phone)
        if patient:
            _set_patient_from_record(state, patient)
            patient_data = state["patient_data"]
        elif not current_patient_id:
            state["patient_id"] = None
            patient_data["is_existing"] = False

    for field in ("name", "age", "gender"):
        value = updates.get(field)
        if value is None:
            continue
        if field == "age":
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
        if field == "gender":
            value = str(value).strip().lower()
        if field == "name":
            value = str(value).strip()
        if not value:
            continue

        if patient_data.get(field) != value:
            patient_data[field] = value
            changed.append(field)
            if field == "name":
                state["pending_name"] = value
            elif field == "age":
                state["pending_age"] = value

    if state.get("patient_id") and changed:
        updated_patient = update_patient_details(
            db,
            state["patient_id"],
            name=patient_data.get("name") if "name" in changed else None,
            age=patient_data.get("age") if "age" in changed else None,
            gender=patient_data.get("gender") if "gender" in changed else None,
            phone=patient_data.get("phone") if "phone" in changed else None,
        )
        if updated_patient is not None:
            _set_patient_from_record(state, updated_patient)

    return changed


def _apply_symptom_updates(state: dict, updates: dict) -> list[str]:
    changed = []
    symptom_data = state["symptom_data"]

    for field in REQUIRED_SYMPTOM_FIELDS:
        value = updates.get(field)
        if value is None or value == "":
            continue
        if field == "severity":
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
        if symptom_data.get(field) != value:
            symptom_data[field] = value
            changed.append(field)

    return changed


def _fill_symptoms_with_extractor(state: dict, user_message: str, analysis: dict) -> list[str]:
    if analysis.get("question") or analysis.get("doctor_selection_number"):
        return []

    missing_before = get_missing_fields(state["symptom_data"])
    if not missing_before:
        return []

    try:
        extracted = extract_symptom_data(user_message)
    except Exception:
        logger.exception("Symptom extraction failed; continuing with turn analysis only")
        return []

    return _apply_symptom_updates(state, extracted)


def _maybe_create_patient(db: Session, state: dict) -> bool:
    if state.get("patient_id"):
        return False

    patient_data = state["patient_data"]
    if get_missing_patient_fields(state):
        return False

    patient = create_patient(
        db,
        name=patient_data["name"],
        age=int(patient_data["age"]),
        gender=patient_data["gender"],
        phone=patient_data["phone"],
    )
    _set_patient_from_record(state, patient)
    state["patient_data"]["is_existing"] = False
    return True


def recommend_doctors(db: Session, state: dict):
    symptom = state["symptom_data"].get("symptom", "")
    body_part = state["symptom_data"].get("body_part", "")

    department, icd_code = map_symptom_to_department(db, symptom, body_part)
    state["department"] = department
    state["icd_code"] = icd_code
    state["ai_impression"] = build_triage_impression(state["symptom_data"])

    doctors = get_available_doctors_by_department(db, department)
    if not doctors:
        state["stage"] = TriageStage.RECOMMENDING_DOCTOR.value
        state["doctor_options"] = []
        return f"No {department} doctors are available right now. Please speak to the front desk.", []

    state["stage"] = TriageStage.AWAITING_DOCTOR_CHOICE.value
    state["doctor_options"] = [{"id": doctor.id, "name": doctor.name} for doctor in doctors]
    options_text = "\n".join(f"{index + 1}. Dr. {doctor.name}" for index, doctor in enumerate(doctors))
    reply = (
        f"Based on what you shared, I recommend {department}. "
        f"Here are the available doctors:\n{options_text}\nWhich one would you prefer?"
    )
    return reply, state["doctor_options"]


def _next_step(db: Session, state: dict) -> TriageTurnResult:
    missing_symptoms = get_missing_fields(state["symptom_data"])
    if missing_symptoms:
        state["stage"] = _stage_for_missing_symptoms(missing_symptoms)
        return TriageTurnResult(reply=FOLLOW_UP_QUESTIONS[missing_symptoms[0]])

    missing_patient = get_missing_patient_fields(state)
    if missing_patient:
        state["stage"] = TriageStage.IDENTIFYING_PATIENT.value
        return TriageTurnResult(reply=PATIENT_FIELD_QUESTIONS[missing_patient[0]])

    _maybe_create_patient(db, state)

    if state.get("selected_doctor_id"):
        state["stage"] = TriageStage.READY_TO_FINALIZE.value
        return TriageTurnResult(reply="Great. Confirm when you are ready and I will issue your token.")

    if not state.get("doctor_options"):
        reply, doctor_options = recommend_doctors(db, state)
        return TriageTurnResult(reply=reply, doctor_options=doctor_options)

    state["stage"] = TriageStage.AWAITING_DOCTOR_CHOICE.value
    return TriageTurnResult(
        reply="Which doctor would you prefer from the list?",
        doctor_options=state["doctor_options"],
    )


def _select_doctor(state: dict, doctor: dict) -> TriageTurnResult:
    state["selected_doctor_id"] = doctor["id"]
    state["stage"] = TriageStage.READY_TO_FINALIZE.value
    return TriageTurnResult(
        reply=f"Great, Dr. {doctor['name']} is selected. Confirm when you are ready and I will issue your token."
    )


def process_turn(db: Session, state: dict, user_message: str) -> TriageTurnResult:
    ensure_triage_state(state)
    analysis = understand_turn(user_message, state)

    _apply_patient_updates(db, state, analysis.get("patient_updates") or {})
    symptom_changes = _apply_symptom_updates(state, analysis.get("symptom_updates") or {})
    symptom_changes.extend(_fill_symptoms_with_extractor(state, user_message, analysis))

    if symptom_changes:
        # A new complaint or body area can change routing. Details such as
        # duration and severity refresh the impression but retain the choice.
        routing_changed = any(field in {"symptom", "body_part"} for field in symptom_changes)
        if routing_changed:
            state["doctor_options"] = []
            state["selected_doctor_id"] = None
            state["department"] = None
            state["icd_code"] = None
        state["ai_impression"] = None

    doctor_choice = resolve_doctor_choice(analysis, user_message, state.get("doctor_options"))

    if analysis.get("needs_urgent_attention"):
        state["stage"] = TriageStage.COLLECTING_SYMPTOMS.value
        return TriageTurnResult(
            reply=(
                "Some of what you described may need urgent attention. "
                "Please ask the nearest staff member for immediate help. "
                "I can continue the kiosk intake if you are safe to do so."
            )
        )

    if analysis.get("wants_doctor_change"):
        state["selected_doctor_id"] = None
        if doctor_choice:
            return _select_doctor(state, doctor_choice)
        if state.get("doctor_options"):
            state["stage"] = TriageStage.AWAITING_DOCTOR_CHOICE.value
            return TriageTurnResult(
                reply="Of course. Which doctor would you like instead?",
                doctor_options=state["doctor_options"],
            )
        reply, doctor_options = recommend_doctors(db, state)
        return TriageTurnResult(reply=reply, doctor_options=doctor_options)

    if doctor_choice and state.get("doctor_options"):
        return _select_doctor(state, doctor_choice)

    if analysis.get("wants_finalize") and state.get("selected_doctor_id") and state.get("patient_id"):
        state["stage"] = TriageStage.READY_TO_FINALIZE.value
        return TriageTurnResult(reply="Done, I am issuing your token now.", finalize_requested=True)

    if analysis.get("question"):
        answer = answer_question(analysis["question"], state)
        next_step = _next_step(db, state)
        if state.get("selected_doctor_id"):
            return TriageTurnResult(
                reply=f"{answer} Your doctor selection is still saved. Say confirm when you are ready for your token.",
                doctor_options=next_step.doctor_options,
                finalize_requested=next_step.finalize_requested,
            )
        if next_step.reply:
            answer = f"{answer} {next_step.reply}"
        return TriageTurnResult(
            reply=answer,
            doctor_options=next_step.doctor_options,
            finalize_requested=next_step.finalize_requested,
        )

    return _next_step(db, state)


def process_message(db: Session, state: dict, user_message: str):
    result = process_turn(db, state, user_message)
    return result.reply, result.doctor_options
