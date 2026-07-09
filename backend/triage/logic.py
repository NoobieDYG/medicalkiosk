from sqlalchemy.orm import Session

from doctor.doctors import get_available_doctors_by_department
from patient.patients import create_patient, get_patient_by_phone
from routing.icd_routing import map_symptom_to_department
from triage.prompts import extract_symptom_data, generate_ai_impression
from triage.stages import TriageStage

REQUIRED_SYMPTOM_FIELDS = ["symptom", "body_part", "duration", "severity"]
FOLLOW_UP_QUESTIONS = {
    "symptom": "Sorry, could you describe what's bothering you?",
    "body_part": "Which part of your body is affected?",
    "duration": "How long has this been going on?",
    "severity": "On a scale of 1 to 10, how bad is it?",
}


def get_missing_fields(symptom_data: dict) -> list:
    return [f for f in REQUIRED_SYMPTOM_FIELDS if not symptom_data.get(f)]


def recommend_doctors(db: Session, state: dict):
    symptom = state["symptom_data"].get("symptom", "")
    body_part = state["symptom_data"].get("body_part", "")

    department, icd_code = map_symptom_to_department(db, symptom, body_part)
    state["department"] = department
    state["icd_code"] = icd_code
    state["ai_impression"] = generate_ai_impression(state["symptom_data"])

    doctors = get_available_doctors_by_department(db, department)
    if not doctors:
        state["stage"] = TriageStage.RECOMMENDING_DOCTOR.value
        return f"No {department} doctors are available right now. Please speak to the front desk.", []

    state["stage"] = TriageStage.AWAITING_DOCTOR_CHOICE.value
    state["doctor_options"] = [{"id": d.id, "name": d.name} for d in doctors]
    options_text = "\n".join(f"{i + 1}. Dr. {d.name}" for i, d in enumerate(doctors))
    reply = (
        f"Based on your symptoms, I'd recommend {department}. "
        f"Here are available doctors:\n{options_text}\nWhich one would you like?"
    )
    return reply, state["doctor_options"]


def process_message(db: Session, state: dict, user_message: str):
    stage = state["stage"]
    doctor_options = None

    if stage in (TriageStage.GREETING.value, TriageStage.COLLECTING_SYMPTOMS.value):
        extracted = extract_symptom_data(user_message)
        for key, value in extracted.items():
            if value is not None:
                state["symptom_data"][key] = value

        missing = get_missing_fields(state["symptom_data"])
        if missing:
            state["stage"] = TriageStage.COLLECTING_SYMPTOMS.value
            reply = FOLLOW_UP_QUESTIONS[missing[0]]
        else:
            state["stage"] = TriageStage.IDENTIFYING_PATIENT.value
            reply = "Thanks. Can I get your phone number to pull up your records?"

    elif stage == TriageStage.IDENTIFYING_PATIENT.value:
        phone = user_message.strip()
        patient = get_patient_by_phone(db, phone)
        if patient:
            state["patient_id"] = patient.id
            reply, doctor_options = recommend_doctors(db, state)
        else:
            state["pending_phone"] = phone
            state["stage"] = TriageStage.COLLECTING_NEW_PATIENT_NAME.value
            reply = "I don't see you in our records yet. What's your full name?"

    elif stage == TriageStage.COLLECTING_NEW_PATIENT_NAME.value:
        state["pending_name"] = user_message.strip()
        state["stage"] = TriageStage.COLLECTING_NEW_PATIENT_AGE.value
        reply = "Got it. What's your age?"

    elif stage == TriageStage.COLLECTING_NEW_PATIENT_AGE.value:
        try:
            state["pending_age"] = int(user_message.strip())
        except ValueError:
            return "Please enter your age as a number.", None
        state["stage"] = TriageStage.COLLECTING_NEW_PATIENT_GENDER.value
        reply = "And your gender? (male / female / other)"

    elif stage == TriageStage.COLLECTING_NEW_PATIENT_GENDER.value:
        patient = create_patient(
            db,
            name=state["pending_name"],
            age=state["pending_age"],
            gender=user_message.strip(),
            phone=state["pending_phone"],
        )
        state["patient_id"] = patient.id
        reply, doctor_options = recommend_doctors(db, state)

    elif stage == TriageStage.AWAITING_DOCTOR_CHOICE.value:
        try:
            choice_index = int(user_message.strip()) - 1
            chosen = state["doctor_options"][choice_index]
        except (ValueError, IndexError):
            return "Please reply with the number of the doctor you'd like to see.", state["doctor_options"]
        state["selected_doctor_id"] = chosen["id"]
        state["stage"] = TriageStage.READY_TO_FINALIZE.value
        reply = f"Great, Dr. {chosen['name']} it is. Tap confirm to get your token."

    else:
        reply = "Sorry, I didn't quite catch that."

    return reply, doctor_options