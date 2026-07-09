from sqlalchemy.orm import Session

from databases.models import ICDCodes
from triage.embeddings import get_embedding

DEFAULT_DEPARTMENT = "General Medicine"
SIMILARITY_THRESHOLD = 0.6  # cosine distance — tune once you see real matches; lower = stricter


def map_symptom_to_department(db: Session, symptom: str, body_part: str = ""):
    """Returns (department, icd_code). icd_code is None if nothing matched closely enough."""
    query_text = f"{symptom} {body_part}".strip()
    if not query_text:
        return DEFAULT_DEPARTMENT, None

    embedding = get_embedding(query_text)
    result = (
        db.query(ICDCodes, ICDCodes.embedding.cosine_distance(embedding).label("distance"))
        .order_by("distance")
        .first()
    )
    if result is None:
        return DEFAULT_DEPARTMENT, None

    icd_row, distance = result
    if distance > SIMILARITY_THRESHOLD:
        return DEFAULT_DEPARTMENT, None
    return icd_row.department, icd_row.code