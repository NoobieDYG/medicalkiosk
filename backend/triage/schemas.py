from typing import Optional

from pydantic import BaseModel


class TriageStartResponse(BaseModel):
    session_id: str
    reply: str
    stage: str


class TriageMessageRequest(BaseModel):
    session_id: str
    message: str


class TriageMessageResponse(BaseModel):
    reply: str
    stage: str
    doctor_options: Optional[list] = None


class TriageEndRequest(BaseModel):
    session_id: str


class TriageEndResponse(BaseModel):
    token_number: int
    doctor_name: str
    department: str
    visit_id: int