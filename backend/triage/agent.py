import logging
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher

from triage.prompts import analyze_patient_turn, answer_patient_question

logger = logging.getLogger(__name__)
LLM_RETRY_COOLDOWN_SECONDS = 60
_llm_retry_after = 0.0

PATIENT_UPDATE_KEYS = ("name", "age", "gender", "phone")
SYMPTOM_UPDATE_KEYS = ("symptom", "body_part", "duration", "severity")

ORDINAL_NUMBERS = {
    "first": 1,
    "one": 1,
    "second": 2,
    "two": 2,
    "third": 3,
    "three": 3,
    "fourth": 4,
    "four": 4,
    "fifth": 5,
    "five": 5,
}

QUESTION_STARTERS = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "can",
    "could",
    "should",
    "do",
    "does",
    "is",
    "are",
    "will",
)

CHANGE_WORDS = ("change", "switch", "different", "another", "someone else", "other doctor")
FINALIZE_WORDS = ("confirm", "book", "token", "done", "yes", "okay", "ok", "go ahead")
URGENT_PATTERNS = (
    "can't breathe",
    "cannot breathe",
    "chest pain",
    "fainted",
    "fainting",
    "heavy bleeding",
    "stroke",
    "slurred speech",
    "face drooping",
    "severe allergic",
)

SYMPTOM_KEYWORDS = (
    "headache",
    "fever",
    "cough",
    "cold",
    "sore throat",
    "stomach pain",
    "abdominal pain",
    "back pain",
    "knee pain",
    "joint pain",
    "rash",
    "dizziness",
    "nausea",
    "vomiting",
    "diarrhea",
    "pain",
)

BODY_PART_KEYWORDS = (
    "head",
    "eye",
    "ear",
    "throat",
    "chest",
    "stomach",
    "abdomen",
    "back",
    "shoulder",
    "arm",
    "hand",
    "leg",
    "knee",
    "foot",
    "skin",
)


@dataclass
class TriageTurnResult:
    reply: str
    doctor_options: list | None = None
    finalize_requested: bool = False


def default_turn_analysis() -> dict:
    return {
        "patient_updates": {"name": None, "age": None, "gender": None, "phone": None},
        "symptom_updates": {"symptom": None, "body_part": None, "duration": None, "severity": None},
        "doctor_selection_number": None,
        "doctor_selection_name": None,
        "wants_doctor_change": False,
        "wants_finalize": False,
        "question": None,
        "question_type": None,
        "needs_urgent_attention": False,
    }


def compact_state_snapshot(state: dict) -> dict:
    return {
        "stage": state.get("stage"),
        "patient_id": state.get("patient_id"),
        "patient": state.get("patient_data", {}),
        "symptoms": state.get("symptom_data", {}),
        "department": state.get("department"),
        "doctor_options": state.get("doctor_options", []),
        "selected_doctor_id": state.get("selected_doctor_id"),
        "ready_to_finalize": bool(state.get("selected_doctor_id") and state.get("patient_id")),
        "recent_messages": state.get("messages", [])[-6:],
    }


def normalize_phone(raw: str | None) -> str | None:
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw))
    return digits or None


def normalize_analysis(raw_analysis: dict | None) -> dict:
    analysis = default_turn_analysis()
    if not isinstance(raw_analysis, dict):
        return analysis

    patient_updates = raw_analysis.get("patient_updates") or {}
    symptom_updates = raw_analysis.get("symptom_updates") or {}

    for key in PATIENT_UPDATE_KEYS:
        value = patient_updates.get(key)
        analysis["patient_updates"][key] = value if value not in ("", "null") else None

    for key in SYMPTOM_UPDATE_KEYS:
        value = symptom_updates.get(key)
        analysis["symptom_updates"][key] = value if value not in ("", "null") else None

    for key in (
        "doctor_selection_number",
        "doctor_selection_name",
        "wants_doctor_change",
        "wants_finalize",
        "question",
        "question_type",
        "needs_urgent_attention",
    ):
        value = raw_analysis.get(key)
        analysis[key] = value if value not in ("", "null") else None

    analysis["patient_updates"]["phone"] = normalize_phone(analysis["patient_updates"]["phone"])
    analysis["wants_doctor_change"] = bool(analysis["wants_doctor_change"])
    analysis["wants_finalize"] = bool(analysis["wants_finalize"])
    analysis["needs_urgent_attention"] = bool(analysis["needs_urgent_attention"])
    return analysis


def fallback_turn_analysis(message: str, state: dict) -> dict:
    analysis = default_turn_analysis()
    text = message.strip()
    lower = text.lower()

    phone_match = re.search(r"(?:\+?\d[\d\s().-]{6,}\d)", text)
    if phone_match:
        analysis["patient_updates"]["phone"] = normalize_phone(phone_match.group(0))

    age_match = re.search(r"\b(?:age is|i am|i'm|im)\s+(\d{1,3})\b", lower)
    if age_match:
        analysis["patient_updates"]["age"] = int(age_match.group(1))

    if lower in ("male", "female", "other") or lower.startswith(("male ", "female ", "other ")):
        analysis["patient_updates"]["gender"] = lower.split()[0]

    name_match = re.search(r"\b(?:my name is|i am|i'm|im)\s+([a-z][a-z .'-]{1,80})$", lower)
    if name_match and not age_match:
        analysis["patient_updates"]["name"] = name_match.group(1).title()

    if state.get("doctor_options"):
        number_match = re.search(r"\b(?:doctor\s*)?(\d{1,2})\b", lower)
        if number_match:
            analysis["doctor_selection_number"] = int(number_match.group(1))
        else:
            for word, number in ORDINAL_NUMBERS.items():
                if re.search(rf"\b{word}\b", lower):
                    analysis["doctor_selection_number"] = number
                    break

    for symptom in SYMPTOM_KEYWORDS:
        if symptom in lower:
            analysis["symptom_updates"]["symptom"] = symptom
            break

    for body_part in BODY_PART_KEYWORDS:
        if body_part in lower:
            analysis["symptom_updates"]["body_part"] = body_part
            break

    duration_match = re.search(
        r"\b(?:for|since)\s+([a-z0-9 -]+?(?:minutes?|hours?|days?|weeks?|months?)|yesterday|today)\b",
        lower,
    )
    if duration_match:
        analysis["symptom_updates"]["duration"] = duration_match.group(0).strip()

    severity_match = re.search(r"\b(10|[1-9])\s*(?:/|out of|on (?:a )?scale of)\s*10\b", lower)
    if severity_match:
        analysis["symptom_updates"]["severity"] = int(severity_match.group(1))
    elif "mild" in lower:
        analysis["symptom_updates"]["severity"] = 3
    elif "moderate" in lower:
        analysis["symptom_updates"]["severity"] = 5
    elif "severe" in lower:
        analysis["symptom_updates"]["severity"] = 8

    analysis["wants_doctor_change"] = any(word in lower for word in CHANGE_WORDS) and "doctor" in lower
    analysis["wants_finalize"] = any(word in lower for word in FINALIZE_WORDS)
    analysis["needs_urgent_attention"] = any(pattern in lower for pattern in URGENT_PATTERNS)

    if "?" in text or lower.startswith(QUESTION_STARTERS):
        analysis["question"] = text
        analysis["question_type"] = "general"

    return analysis


def understand_turn(message: str, state: dict) -> dict:
    global _llm_retry_after
    if time.monotonic() < _llm_retry_after:
        return fallback_turn_analysis(message, state)
    try:
        return normalize_analysis(analyze_patient_turn(message, compact_state_snapshot(state)))
    except Exception:
        _llm_retry_after = time.monotonic() + LLM_RETRY_COOLDOWN_SECONDS
        logger.warning("LLM turn analysis failed; using local fallback for this conversation")
        return fallback_turn_analysis(message, state)


def fallback_question_answer(question: str) -> str:
    lower = question.lower()
    if "cardiology" in lower:
        return "Cardiology looks after heart and blood-vessel conditions."
    if "general medicine" in lower or "general physician" in lower:
        return "General Medicine evaluates common adult health concerns and can coordinate specialist care when needed."
    if "hospital" in lower or "visiting" in lower or "hours" in lower:
        return "For hospital policies and visiting hours, the front desk can give you the current details."
    return (
        "I can give general guidance, but I cannot diagnose from the kiosk. "
        "The doctor will review your symptoms and confirm the right next step."
    )


def answer_question(question: str, state: dict) -> str:
    global _llm_retry_after
    if time.monotonic() < _llm_retry_after:
        return fallback_question_answer(question)
    try:
        return answer_patient_question(question, compact_state_snapshot(state))
    except Exception:
        _llm_retry_after = time.monotonic() + LLM_RETRY_COOLDOWN_SECONDS
        logger.warning("LLM question answer failed; using local fallback for this conversation")
        return fallback_question_answer(question)


def resolve_doctor_choice(analysis: dict, message: str, doctor_options: list | None) -> dict | None:
    if not doctor_options:
        return None

    number = analysis.get("doctor_selection_number")
    if isinstance(number, int) and 1 <= number <= len(doctor_options):
        return doctor_options[number - 1]

    name = analysis.get("doctor_selection_name") or message
    name = str(name).lower().replace("dr.", "").replace("doctor", "").strip()
    if not name:
        return None

    best_match = None
    best_score = 0
    for doctor in doctor_options:
        doctor_name = str(doctor.get("name", "")).lower()
        score = SequenceMatcher(None, name, doctor_name).ratio()
        if name in doctor_name:
            score = max(score, 0.9)
        if score > best_score:
            best_score = score
            best_match = doctor

    return best_match if best_score >= 0.72 else None
