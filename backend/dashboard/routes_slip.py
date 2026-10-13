from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from databases.db import get_db
from databases.models import Visits
from .slip import build_slip

slip_router = APIRouter(tags=["slip"])


@slip_router.get("/slip/{slip_id}")
def get_public_slip(slip_id: str, response: Response, db: Session = Depends(get_db)):
    visit = db.query(Visits).filter(Visits.slip_id == slip_id).first()
    if visit is None:
        raise HTTPException(status_code=404, detail="Slip not found")
    response.headers["Cache-Control"] = "no-store"
    return build_slip(db, visit)