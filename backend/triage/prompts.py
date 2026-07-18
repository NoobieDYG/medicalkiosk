import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parents[1]
for dotenv_path in (Path.cwd() / ".env", BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    load_dotenv(dotenv_path=dotenv_path)


API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment variables.")
client= genai.Client(api_key = API_KEY)


EXTRACTION_SYSTEM_PROMPT = """You are a medical intake assistant. You do not diagnose.
You only extract structured information from what the patient says, in
strict JSON, with no extra commentary. Fields: symptom, body_part,
duration, severity (an integer 1-10 if mentioned, else null).
If a field is missing or not mentioned, set it to null. Return JSON only,
no markdown fences."""

IMPRESSION_SYSTEM_PROMPT = """You are a clinical intake note-writer, not a diagnostician.
Write a 1-2 sentence note summarizing what the patient reported, for the
doctor's quick reference before they see the patient. Describe symptoms
factually. Do not suggest a diagnosis, treatment, or medication. End your
note with exactly: "For doctor review only — not a diagnosis." """


def _call_gemini(user_prompt: str, system_prompt: str, *, max_output_tokens: int) -> str:

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_output_tokens,
            temperature=0,
        ),
    )

    if getattr(response, "text", None):
        return response.text.strip()

    try:
        return response.candidates[0].content.parts[0].text.strip()
    except (AttributeError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {response}") from exc


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].lstrip()
    return cleaned.strip()


def extract_symptom_data(message: str) -> dict:
    text = _call_gemini(message, EXTRACTION_SYSTEM_PROMPT, max_output_tokens=300)
    return json.loads(_clean_json_text(text))


def generate_ai_impression(symptom_data: dict) -> str:
    facts = ", ".join(f"{k}: {v}" for k, v in symptom_data.items() if v)
    text = _call_gemini(facts, IMPRESSION_SYSTEM_PROMPT, max_output_tokens=150)
    return text.strip()