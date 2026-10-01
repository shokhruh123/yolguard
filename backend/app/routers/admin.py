"""Админ-панель сотрудника: список инцидентов + полное досье.
Видит: triage, фото, чертёж ИИ, довод ИИ, пострадавших, рекомендации, схему, подтверждения."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from .deps import need_role

router = APIRouter(prefix="/admin", tags=["admin"])

def _brief(inc: models.Incident) -> dict:
    return {"id": inc.id, "code": inc.code, "status": inc.status,
            "eligibility": inc.eligibility, "reason": inc.eligibility_reason,
            "has_injury": bool(inc.has_injury), "occurred_at": str(inc.occurred_at)}

@router.get("/incidents")
def list_incidents(db: Session = Depends(get_db),
                   _s: models.User = Depends(need_role("specialist"))):
    rows = db.query(models.Incident).order_by(models.Incident.id.desc()).all()
    return [_brief(r) for r in rows]

@router.get("/incidents/{iid}")
def incident_detail(iid: int, db: Session = Depends(get_db),
                    _s: models.User = Depends(need_role("specialist"))):
    inc = db.get(models.Incident, iid)
    if not inc: raise HTTPException(404, "Not found")
    parts = db.query(models.Participant).filter_by(incident_id=iid).all()
    ev = db.query(models.Evidence).filter_by(incident_id=iid).all()
    dia = db.query(models.Diagram).filter_by(incident_id=iid).first()
    ai = db.query(models.AIAnalysis).filter_by(incident_id=iid).first()
    claim = db.query(models.ClaimPackage).filter_by(incident_id=iid).first()
    review = db.query(models.ReviewCase).filter_by(incident_id=iid).first()
    users = {u.id: u.full_name for u in db.query(models.User).all()}
    return {
        "incident": _brief(inc),
        "triage": {"has_injury": bool(inc.has_injury), "has_pedestrian": bool(inc.has_pedestrian),
                   "vehicle_count": inc.vehicle_count, "third_party_damage": bool(inc.third_party_damage),
                   "responsibility_accepted": bool(inc.responsibility_accepted),
                   "docs_valid": bool(inc.docs_valid), "sober": bool(inc.sober),
                   "damage_agreed": bool(inc.damage_agreed),
                   "injured_count": inc.injured_count or 0,
                   "impact_part": inc.impact_part or "", "driver_comment": inc.driver_comment or ""},
        "participants": [{"side": p.side, "user": users.get(p.user_id, "?"),
                          "vehicle_id": p.vehicle_id, "confirmed": bool(p.confirmed)} for p in parts],
        "evidence": [{"id": e.id, "kind": e.kind,
                      "url": f"/api/v1/incidents/{iid}/evidence/{e.id}/file",
                      "gps": [float(e.gps_lat) if e.gps_lat is not None else None,
                              float(e.gps_lon) if e.gps_lon is not None else None],
                      "sha256": e.sha256[:12]} for e in ev],
        "diagram": {"svg": dia.svg if dia else None,
                    "approved_a": bool(dia.approved_a) if dia else False,
                    "approved_b": bool(dia.approved_b) if dia else False},
        "ai": ({"source": ai.source, "description": ai.description,
                "casualties_note": ai.casualties_note,
                "actions": json.loads(ai.actions_json), "svg": ai.svg} if ai else None),
        "claim": {"package_hash": claim.package_hash} if claim else None,
        "review": {"id": review.id, "verdict": review.verdict, "comment": review.comment} if review else None,
        "messages": [{"from_role": m.sender_role, "text": m.text, "at": str(m.created_at)}
                     for m in db.query(models.Message).filter_by(incident_id=iid)
                     .order_by(models.Message.id).all()],
    }

@router.post("/incidents/{iid}/message", status_code=201)
def send_message(iid: int, body: schemas.MessageIn, db: Session = Depends(get_db),
                 s: models.User = Depends(need_role("specialist"))):
    """Сотрудник пишет пользователю произвольный текст."""
    if not db.get(models.Incident, iid): raise HTTPException(404, "Not found")
    m = models.Message(incident_id=iid, sender_id=s.id, sender_role=s.role, text=body.text.strip()[:1000])
    db.add(m); db.commit()
    return {"id": m.id}
