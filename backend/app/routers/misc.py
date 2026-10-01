from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from .deps import current_user, need_role

router = APIRouter(tags=["misc"])

@router.post("/vehicles", status_code=201)
def add_vehicle(body: schemas.VehicleIn, db: Session = Depends(get_db),
                u: models.User = Depends(current_user)):
    if db.query(models.Vehicle).filter_by(plate=body.plate).first():
        raise HTTPException(409, "Plate exists")
    v = models.Vehicle(owner_id=u.id, **body.model_dump())
    db.add(v); db.commit(); db.refresh(v)
    return {"id": v.id, "plate": v.plate}

@router.post("/incidents/{iid}/confirm")
def confirm(iid: int, db: Session = Depends(get_db), u: models.User = Depends(current_user)):
    p = db.query(models.Participant).filter_by(incident_id=iid, user_id=u.id).first()
    if not p: raise HTTPException(404, "Not a participant")
    p.confirmed = 1; db.commit()
    return {"confirmed": True}

@router.get("/reviews/queue")
def queue(db: Session = Depends(get_db), _s: models.User = Depends(need_role("specialist"))):
    rows = db.query(models.ReviewCase).filter_by(verdict="pending").all()
    return [{"id": r.id, "incident_id": r.incident_id} for r in rows]

@router.post("/reviews/{rid}")
def verdict(rid: int, body: schemas.ReviewIn, db: Session = Depends(get_db),
            s: models.User = Depends(need_role("specialist"))):
    r = db.get(models.ReviewCase, rid)
    if not r: raise HTTPException(404, "Not found")
    if body.verdict not in ("approved", "needs_field", "rejected"):
        raise HTTPException(400, "Bad verdict")
    r.verdict, r.comment, r.assignee_id = body.verdict, body.comment, s.id
    # Две кнопки сотрудника сразу уходят пользователю текстом
    texts = {
        "approved": "Зарегистрировано успешно. К вам едут агенты, ждите.",
        "needs_field": "К вам едут агенты, ждите.",
        "rejected": f"Заявка отклонена: {body.comment or 'обратитесь в ГАИ'}.",
    }
    db.add(models.Message(incident_id=r.incident_id, sender_id=s.id,
                          sender_role=s.role, text=texts[body.verdict]))
    db.commit()
    return {"verdict": r.verdict, "sent_to_user": texts[body.verdict]}
