import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parents[1]
for dotenv_path in (Path.cwd() / ".env", BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    load_dotenv(dotenv_path=dotenv_path)


API_KEY = os.getenv("GEMINI_API_KEY")
LLM_TIMEOUT_MS = max(10_000, int(os.getenv("TRIAGE_LLM_TIMEOUT_MS", "10000")))
LLM_RETRY_COOLDOWN_SECONDS = 60
_llm_retry_after = 0.0
client = None


def get_client():
    global client
    if client is None:
        if not API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set in environment variables.")
        client = genai.Client(
            api_key=API_KEY,
            http_options=types.HttpOptions(
                timeout=LLM_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
    return client


EXTRACTION_SYSTEM_PROMPT = """You are a medical intake assistant. You do not diagnose.
Extract structured information from what the patient says.
Set fields to null if not mentioned."""

IMPRESSION_SYSTEM_PROMPT = """You are a clinical intake note-writer, not a diagnostician.
Write a 1-2 sentence note summarizing what the patient reported, for the
doctor's quick reference before they see the patient. Describe symptoms
factually. Do not suggest a diagnosis, treatment, or medication. End your
note with exactly: "For doctor review only - not a diagnosis." """

TURN_ANALYSIS_SYSTEM_PROMPT = """You are the language-understanding layer for a hospital kiosk voice assistant.
Analyze the patient's latest message in the context of the current triage state.

Return structured JSON only. Do not diagnose. Your job is to identify intent,
extract corrections or new facts, and preserve flexibility when the patient goes
back and forth.

Rules:
- Treat corrections such as "actually", "change", "I meant", or "my number is"
  as updates even if the previous assistant question was about something else.
- Extract patient fields only when the user clearly provides them.
- Extract symptom fields only when they are patient-reported.
- If the user asks a general medical, hospital, appointment, privacy, or process
  question, put that exact question in "question".
- If the user chooses a doctor by number or name, fill the doctor selection fields.
- If the user says they want another doctor, set wants_doctor_change to true.
- If the user confirms booking or asks for their token, set wants_finalize to true.
- If the user reports emergency red flags, set needs_urgent_attention to true."""

QUESTION_ANSWER_SYSTEM_PROMPT = """You are a warm hospital kiosk voice assistant.
Answer the patient's question briefly and safely, then help them continue triage.

Rules:
- Do not diagnose, prescribe medicine, or claim certainty.
- For medical questions, give general information and encourage review by the doctor.
- For severe symptoms, breathing trouble, chest pain, fainting, heavy bleeding,
  stroke-like symptoms, or rapidly worsening symptoms, advise urgent staff help.
- For hospital/process questions, answer from the kiosk context when possible.
- If you do not know a hospital-specific policy, say the front desk can confirm."""

SYMPTOM_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "symptom": {"type": "STRING", "nullable": True},
        "body_part": {"type": "STRING", "nullable": True},
        "duration": {"type": "STRING", "nullable": True},
        "severity": {"type": "INTEGER", "nullable": True},
    },
    "required": ["symptom", "body_part", "duration", "severity"],
}

TURN_ANALYSIS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "patient_updates": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "nullable": True},
                "age": {"type": "INTEGER", "nullable": True},
                "gender": {"type": "STRING", "nullable": True},
                "phone": {"type": "STRING", "nullable": True},
            },
            "required": ["name", "age", "gender", "phone"],
        },
        "symptom_updates": SYMPTOM_SCHEMA,
        "doctor_selection_number": {"type": "INTEGER", "nullable": True},
        "doctor_selection_name": {"type": "STRING", "nullable": True},
        "wants_doctor_change": {"type": "BOOLEAN"},
        "wants_finalize": {"type": "BOOLEAN"},
        "question": {"type": "STRING", "nullable": True},
        "question_type": {"type": "STRING", "nullable": True},
        "needs_urgent_attention": {"type": "BOOLEAN"},
    },
    "required": [
        "patient_updates",
        "symptom_updates",
        "doctor_selection_number",
        "doctor_selection_name",
        "wants_doctor_change",
        "wants_finalize",
        "question",
        "question_type",
        "needs_urgent_attention",
    ],
}


def _call_gemini(
    user_prompt: str,
    system_prompt: str,
    *,
    max_output_tokens: int,
    response_schema: dict | None = None,
) -> str:
    global _llm_retry_after
    if time.monotonic() < _llm_retry_after:
        raise RuntimeError("Gemini is temporarily unavailable; using the local fallback.")

    config_kwargs = {
        "system_instruction": system_prompt,
        "max_output_tokens": max_output_tokens,
        "temperature": 0,
        "thinking_config": types.ThinkingConfig(thinking_level="minimal"),
    }

    if response_schema is not None:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = response_schema

    try:
        response = get_client().models.generate_content(
            model="gemini-3.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
    except Exception:
        _llm_retry_after = time.monotonic() + LLM_RETRY_COOLDOWN_SECONDS
        raise

    if getattr(response, "text", None):
        return response.text.strip()

    try:
        return response.candidates[0].content.parts[0].text.strip()
    except (AttributeError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {response}") from exc


def extract_symptom_data(message: str) -> dict:
    default_data = {"symptom": None, "body_part": None, "duration": None, "severity": None}

    try:
        text = _call_gemini(
            message,
            EXTRACTION_SYSTEM_PROMPT,
            max_output_tokens=500,
            response_schema=SYMPTOM_SCHEMA,
        )
        extracted = json.loads(text)
        return {**default_data, **extracted}
    except json.JSONDecodeError as e:
        print(f"WARNING: Failed to parse symptom JSON. Error: {e}")
        print(f"Raw LLM response: {text if 'text' in locals() else 'unknown'}")
        return default_data


def analyze_patient_turn(message: str, state_snapshot: dict) -> dict:
    default_analysis = {
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

    prompt = (
        "Current triage state:\n"
        f"{json.dumps(state_snapshot, ensure_ascii=True, default=str)}\n\n"
        "Latest patient message:\n"
        f"{message}"
    )

    try:
        text = _call_gemini(
            prompt,
            TURN_ANALYSIS_SYSTEM_PROMPT,
            max_output_tokens=700,
            response_schema=TURN_ANALYSIS_SCHEMA,
        )
        extracted = json.loads(text)
        return {**default_analysis, **extracted}
    except json.JSONDecodeError as e:
        print(f"WARNING: Failed to parse turn analysis JSON. Error: {e}")
        print(f"Raw LLM response: {text if 'text' in locals() else 'unknown'}")
        return default_analysis


def answer_patient_question(question: str, state_snapshot: dict) -> str:
    prompt = (
        "Current triage state:\n"
        f"{json.dumps(state_snapshot, ensure_ascii=True, default=str)}\n\n"
        "Patient question:\n"
        f"{question}"
    )
    return _call_gemini(prompt, QUESTION_ANSWER_SYSTEM_PROMPT, max_output_tokens=180)


def generate_ai_impression(symptom_data: dict) -> str:
    facts = ", ".join(f"{k}: {v}" for k, v in symptom_data.items() if v)
    text = _call_gemini(facts, IMPRESSION_SYSTEM_PROMPT, max_output_tokens=150)
    return text.strip()
