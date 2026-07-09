import json

import httpx
from dotenv import load_dotenv

API_KEY = load_dotenv().get('ANTHROPIC_API_KEY')
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


def extract_symptom_data(message: str) -> dict:
    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 300,
            "system": EXTRACTION_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": message}],
        },
        timeout=15,
    )
    response.raise_for_status()
    text = response.json()["content"][0]["text"]
    return json.loads(text)


def generate_ai_impression(symptom_data: dict) -> str:
    facts = ", ".join(f"{k}: {v}" for k, v in symptom_data.items() if v)
    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 150,
            "system": IMPRESSION_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": facts}],
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["content"][0]["text"].strip()