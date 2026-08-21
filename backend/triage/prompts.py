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
Extract structured information from what the patient says.
Set fields to null if not mentioned."""

IMPRESSION_SYSTEM_PROMPT = """You are a clinical intake note-writer, not a diagnostician.
Write a 1-2 sentence note summarizing what the patient reported, for the
doctor's quick reference before they see the patient. Describe symptoms
factually. Do not suggest a diagnosis, treatment, or medication. End your
note with exactly: "For doctor review only — not a diagnosis." """

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


def _call_gemini(
    user_prompt: str,
    system_prompt: str,
    *,
    max_output_tokens: int,
    response_schema: dict | None = None,
) -> str:

    config_kwargs = {
        "system_instruction": system_prompt,
        "max_output_tokens": max_output_tokens,
        "temperature": 0,
        "thinking_config": types.ThinkingConfig(thinking_level="minimal"),
    }

    if response_schema is not None:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = response_schema

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    if getattr(response, "text", None):
        return response.text.strip()

    try:
        return response.candidates[0].content.parts[0].text.strip()
    except (AttributeError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {response}") from exc


def extract_symptom_data(message: str) -> dict:
    DEFAULT_DATA = {"symptom": None, "body_part": None, "duration": None, "severity": None}

    try:
        text = _call_gemini(
            message,
            EXTRACTION_SYSTEM_PROMPT,
            max_output_tokens=500,
            response_schema=SYMPTOM_SCHEMA,
        )
        extracted = json.loads(text)
        return {**DEFAULT_DATA, **extracted}
    except json.JSONDecodeError as e:
        print(f"WARNING: Failed to parse symptom JSON. Error: {e}")
        print(f"Raw LLM response: {text if 'text' in locals() else 'unknown'}")
        return DEFAULT_DATA


def generate_ai_impression(symptom_data: dict) -> str:
    facts = ", ".join(f"{k}: {v}" for k, v in symptom_data.items() if v)
    text = _call_gemini(facts, IMPRESSION_SYSTEM_PROMPT, max_output_tokens=150)
    return text.strip()