from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from ..services import push as push_svc
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
def queue(db: Session = Depends(get_db),
          limit: int = Query(200, ge=1, le=500),
          _s: models.User = Depends(need_role("specialist"))):
    rows = db.query(models.ReviewCase).filter_by(verdict="pending").limit(limit).all()
    return [{"id": r.id, "incident_id": r.incident_id} for r in rows]

@router.post("/reviews/{rid}")
def verdict(rid: int, body: schemas.ReviewIn, db: Session = Depends(get_db),
            s: models.User = Depends(need_role("specialist"))):
    r = db.get(models.ReviewCase, rid)
    if not r: raise HTTPException(404, "Not found")
    if r.verdict != "pending":
        raise HTTPException(409, f"Already decided: {r.verdict}")
    if body.verdict not in ("approved", "needs_field", "rejected"):
        raise HTTPException(400, "Bad verdict")
    if body.verdict == "rejected" and not (body.comment or "").strip():
        raise HTTPException(400, "Rejection needs a comment")
    r.verdict, r.comment, r.assignee_id = body.verdict, body.comment, s.id
    if body.verdict == "rejected":
        inc = db.get(models.Incident, r.incident_id)
        if inc: inc.status = "closed"
    # Две кнопки сотрудника сразу уходят пользователю текстом
    texts = {
        "approved": "Зарегистрировано успешно. К вам едут агенты, ждите.",
        "needs_field": "К вам едут агенты, ждите.",
        "rejected": f"Заявка отклонена: {body.comment or 'обратитесь в ГАИ'}.",
    }
    db.add(models.Message(incident_id=r.incident_id, sender_id=s.id,
                          sender_role=s.role, text=texts[body.verdict]))
    db.commit()
    # push участникам (best-effort, ошибки не роняют вердикт)
    try:
        push_svc.notify_participants(db, r.incident_id, s.id,
                                     "Yo'l Guard: решение по ДТП",
                                     texts[body.verdict])
    except Exception:
        pass
    return {"verdict": r.verdict, "sent_to_user": texts[body.verdict]}

@router.get("/insurer/incidents")
def insurer_incidents(db: Session = Depends(get_db),
                      limit: int = Query(200, ge=1, le=500),
                      _i: models.User = Depends(need_role("specialist", "insurer"))):
    """Страховая: инциденты с готовым claim-пакетом (read-only)."""
    rows = (db.query(models.Incident)
            .join(models.ClaimPackage,
                  models.ClaimPackage.incident_id == models.Incident.id)
            .order_by(models.Incident.id.desc()).limit(limit).all())
    out = []
    for inc in rows:
        claim = db.query(models.ClaimPackage).filter_by(incident_id=inc.id).first()
        out.append({"id": inc.id, "code": inc.code, "status": inc.status,
                    "eligibility": inc.eligibility,
                    "occurred_at": str(inc.occurred_at),
                    "package_hash": claim.package_hash if claim else None})
    return out
