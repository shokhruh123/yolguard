"""Incident flow: create -> triage -> evidence -> diagram -> claim package."""
import hashlib, html, json, os, re, secrets, time
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..config import settings
from ..db import get_db
from .. import models, schemas
from .. import mongo
from ..services.rules import Triage, evaluate, completeness, REQUIRED_EVIDENCE
from ..services import ai as ai_svc
from ..services import images as img_svc
from .deps import current_user, need_role, user_from_token

router = APIRouter(prefix="/incidents", tags=["incidents"])

# kind значений фото: только известные + other. Защита от path traversal
# (kind раньше вставлялся в имя файла без sanitize) и от мусорных видов.
# kind значений: фото из REQUIRED_EVIDENCE + документы/прочее + медиа.
# Фото влияют на completeness; видео/аудио — дополнительные материалы.
MEDIA_KINDS = {"video_scene", "voice_note"}
ALLOWED_KINDS = set(REQUIRED_EVIDENCE) | {"doc_photo", "other"} | MEDIA_KINDS

def _check_kind(kind: str) -> str:
    k = (kind or "").strip()
    if k not in ALLOWED_KINDS or not re.fullmatch(r"[a-z_]+", k):
        raise HTTPException(400, f"Bad kind. Allowed: {sorted(ALLOWED_KINDS)}")
    return k

async def _run_ai(db: Session, inc: models.Incident) -> dict:
    """Запускает ИИ по фото+triage, сохраняет результат, возвращает его."""
    ev = db.query(models.Evidence).filter_by(incident_id=inc.id).all()
    # в ИИ уходят только фото (mime image/* или legacy-строки без mime);
    # видео/аудио в модель не отправляем. Читаем не более 3 файлов.
    images: list[bytes] = []
    for e in ev:
        if len(images) >= 3:
            break
        if e.mime and not e.mime.startswith("image/"):
            continue
        p = e.file_path[1:] if e.file_path.startswith("/") else e.file_path
        if os.path.exists(p):
            with open(p, "rb") as f: images.append(f.read())
    triage = {"has_injury": bool(inc.has_injury), "has_pedestrian": bool(inc.has_pedestrian),
              "vehicle_count": inc.vehicle_count, "eligibility": inc.eligibility,
              "injured_count": inc.injured_count or 0,
              "impact_part": inc.impact_part or "", "driver_comment": inc.driver_comment or ""}
    res = await ai_svc.analyze(triage, [e.kind for e in ev], images)
    row = db.query(models.AIAnalysis).filter_by(incident_id=inc.id).first()
    if row:
        row.source, row.description = res["source"], res["description"]
        row.casualties_note, row.svg = res["casualties_note"], res["svg"]
        row.actions_json = json.dumps(res["actions"], ensure_ascii=False)
    else:
        row = models.AIAnalysis(incident_id=inc.id, source=res["source"], description=res["description"],
                                casualties_note=res["casualties_note"],
                                actions_json=json.dumps(res["actions"], ensure_ascii=False), svg=res["svg"])
        db.add(row)
    db.commit()
    # Document store: полная история запусков ИИ + аудит-событие (SQL хранит итог).
    try:
        mongo.store_ai_analysis(inc.id, {"source": res["source"], "description": res["description"],
                                         "casualties_note": res["casualties_note"],
                                         "actions": res["actions"], "svg": res["svg"]},
                                {"kinds": [e.kind for e in ev], "images_sent": len(images),
                                 "plates": res.get("plates", {"a": "", "b": ""}),
                                 "damage_severity": res.get("damage_severity", "unknown")})
        mongo.log_event(inc.id, "ai_analysis", f"source={res['source']}")
    except Exception:
        pass
    return {"source": res["source"], "description": res["description"],
            "casualties_note": res["casualties_note"], "actions": res["actions"], "svg": res["svg"],
            "plates": res.get("plates", {"a": "", "b": ""}),
            "damage_severity": res.get("damage_severity", "unknown")}

@router.post("", status_code=201)
def create_incident(body: schemas.IncidentCreate, db: Session = Depends(get_db),
                    u: models.User = Depends(current_user)):
    code = secrets.token_hex(3).upper()
    inc = models.Incident(code=code, creator_id=u.id, lat=body.lat, lon=body.lon)
    db.add(inc); db.commit(); db.refresh(inc)
    db.add(models.Participant(incident_id=inc.id, user_id=u.id, side="A"))
    db.commit()
    return {"id": inc.id, "code": code, "status": inc.status}

@router.post("/{iid}/join", status_code=201)
def join_incident(iid: int, code: str, db: Session = Depends(get_db),
                  u: models.User = Depends(current_user)):
    inc = db.get(models.Incident, iid)
    if not inc or inc.code != code: raise HTTPException(404, "Incident/code not found")
    if db.query(models.Participant).filter_by(incident_id=iid, user_id=u.id).first():
        raise HTTPException(409, "Already joined")
    if db.query(models.Participant).filter_by(incident_id=iid).count() >= 2:
        raise HTTPException(409, "Session full (2 drivers max)")
    db.add(models.Participant(incident_id=iid, user_id=u.id, side="B")); db.commit()
    return {"joined": True, "side": "B"}

@router.post("/{iid}/triage")
def triage(iid: int, body: schemas.TriageIn, db: Session = Depends(get_db),
           u: models.User = Depends(current_user)):
    inc = db.get(models.Incident, iid)
    if not inc: raise HTTPException(404, "Not found")
    # число пострадавших > 0 всегда означает наличие пострадавших (ИИ это НЕ выдумывает)
    data = body.model_dump()
    if data.get("injured_count", 0) > 0:
        data["has_injury"] = True
    for f, val in data.items():
        setattr(inc, f, int(val) if isinstance(val, bool) else val)
    # в правила eligibility передаём только поля, которые знает Triage
    rules_fields = {k: data[k] for k in Triage.__dataclass_fields__ if k in data}
    color, reason = evaluate(Triage(**rules_fields))
    inc.eligibility, inc.eligibility_reason = color, reason
    inc.status = "escalated" if color == "red" else "evidence"
    if color in ("yellow", "red") and not db.query(models.ReviewCase).filter_by(incident_id=iid).first():
        db.add(models.ReviewCase(incident_id=iid))
    db.commit()
    return {"eligibility": color, "reason": reason, "status": inc.status}

@router.post("/{iid}/evidence", status_code=201)
def add_evidence(iid: int, body: schemas.EvidenceIn, db: Session = Depends(get_db),
                 u: models.User = Depends(current_user)):
    inc = db.get(models.Incident, iid)
    if not inc or inc.status == "escalated": raise HTTPException(400, "Incident not in evidence stage")
    kind = _check_kind(body.kind)
    h = hashlib.sha256(f"{iid}:{kind}:{body.file_path}".encode()).hexdigest()
    db.add(models.Evidence(incident_id=iid, kind=kind, file_path=body.file_path, sha256=h))
    db.commit()
    kinds = [e.kind for e in db.query(models.Evidence).filter_by(incident_id=iid).all()]
    comp = completeness(kinds)
    if comp["percent"] == 100 and inc.status == "evidence":
        inc.status = "diagram"; db.commit()
    return {"saved": True, "sha256": h, "completeness": comp}

@router.post("/{iid}/diagram")
def make_diagram(iid: int, body: schemas.DiagramIn, db: Session = Depends(get_db),
                 u: models.User = Depends(current_user)):
    inc = db.get(models.Incident, iid)
    if not inc: raise HTTPException(404, "Not found")
    # метки — пользовательский ввод: экранируем перед вставкой в SVG (stored XSS)
    la, lb = html.escape(body.label_a), html.escape(body.label_b)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">'
           f'<rect width="400" height="200" fill="#eef"/><line x1="0" y1="100" x2="400" y2="100" stroke="#333" stroke-dasharray="8 6"/>'
           f'<rect x="90" y="60" width="80" height="36" fill="#2b60a0"/><text x="130" y="83" fill="#fff" text-anchor="middle">{la}</text>'
           f'<rect x="230" y="104" width="80" height="36" fill="#c0392b"/><text x="270" y="127" fill="#fff" text-anchor="middle">{lb}</text>'
           f'<circle cx="180" cy="100" r="5" fill="#f39c12"/></svg>')
    d = db.query(models.Diagram).filter_by(incident_id=iid).first()
    if d: d.svg = svg
    else: db.add(models.Diagram(incident_id=iid, svg=svg))
    db.commit()
    return {"svg": svg, "disclaimer": "Черновик. Юридический факт подтверждают водители и специалист."}

@router.post("/{iid}/claim-package", status_code=201)
def claim_package(iid: int, db: Session = Depends(get_db),
                  _s: models.User = Depends(need_role("specialist"))):
    inc = db.get(models.Incident, iid)
    if not inc: raise HTTPException(404, "Not found")
    ev = db.query(models.Evidence).filter_by(incident_id=iid).all()
    parts = db.query(models.Participant).filter_by(incident_id=iid).all()
    # Процесс не тянем: достаточно подтверждения создателя случая (сторона A).
    # Второй водитель может подключиться по коду, но его подтверждение не требуется.
    if not any(p.side == "A" and p.confirmed for p in parts):
        raise HTTPException(400, "Создатель случая должен подтвердить схему/данные")
    payload = {"incident_id": iid, "eligibility": [inc.eligibility, inc.eligibility_reason],
               "evidence": [{"kind": e.kind, "sha256": e.sha256} for e in ev]}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256(blob.encode()).hexdigest()
    if not db.query(models.ClaimPackage).filter_by(incident_id=iid).first():
        db.add(models.ClaimPackage(incident_id=iid, payload_json=blob, package_hash=h))
        inc.status = "ready"; db.commit()
    return {"package_hash": h, "payload": payload}

@router.get("/{iid}/claim-package")
def read_claim_package(iid: int, db: Session = Depends(get_db),
                       u: models.User = Depends(current_user)):
    """Чтение claim-пакета: участники + specialist/admin + insurer (read-only)."""
    if u.role not in ("specialist", "admin", "insurer"):
        _can_read(iid, u, db)
    elif not db.get(models.Incident, iid):
        raise HTTPException(404, "Not found")
    claim = db.query(models.ClaimPackage).filter_by(incident_id=iid).first()
    if not claim: raise HTTPException(404, "No claim package yet")
    return {"package_hash": claim.package_hash,
            "payload": json.loads(claim.payload_json)}

@router.post("/{iid}/evidence-upload", status_code=201)
async def evidence_upload(iid: int, kind: str = Form(...), file: UploadFile = File(...),
                          db: Session = Depends(get_db),
                          u: models.User = Depends(current_user)):
    """Загрузка файла: фото (magic bytes, 10 МБ, ресайз 1600px, EXIF GPS),
    видео MP4/WEBM (до 50 МБ), аудио MP3/OGG/WAV/FLAC (до 10 МБ).
    Доступ только участникам инцидента."""
    inc = db.get(models.Incident, iid)
    if not inc or inc.status == "escalated":
        raise HTTPException(400, "Incident not in evidence stage")
    if u.role not in ("specialist", "admin") and \
            not db.query(models.Participant).filter_by(incident_id=iid, user_id=u.id).first():
        raise HTTPException(403, "Not your incident")
    kind = _check_kind(kind)
    if db.query(models.Evidence).filter_by(incident_id=iid).count() >= settings.MAX_UPLOADS_PER_INCIDENT:
        raise HTTPException(409, "Too many uploads for this incident")
    raw = await file.read()
    try:
        proc = img_svc.process_media(raw) if kind in MEDIA_KINDS else img_svc.process_upload(raw)
    except img_svc.UploadError as e:
        raise HTTPException(400, str(e))
    data = proc["bytes"]
    h = hashlib.sha256(data).hexdigest()
    name = f"{iid}_{kind}_{int(time.time())}_{secrets.token_hex(2)}{proc['ext']}"
    updir = settings.UPLOAD_DIR
    os.makedirs(updir, exist_ok=True)
    with open(os.path.join(updir, name), "wb") as f:
        f.write(data)
    ev_row = models.Evidence(incident_id=iid, kind=kind, file_path=f"{updir}/{name}",
                             sha256=h, mime=proc["mime"], size_bytes=len(data),
                             status="processing", storage="local",
                             gps_lat=proc["gps_lat"], gps_lon=proc["gps_lon"])
    db.add(ev_row)
    db.commit(); db.refresh(ev_row)
    try:
        mongo.store_evidence_meta(ev_row.id, iid, {"kind": kind, "mime": proc["mime"],
            "size_bytes": len(data), "sha256": h,
            "gps": [proc["gps_lat"], proc["gps_lon"]]})
        mongo.log_event(iid, "upload", f"kind={kind} size={len(data)}", actor_id=u.id)
    except Exception:
        pass
    kinds = [e.kind for e in db.query(models.Evidence).filter_by(incident_id=iid).all()]
    comp = completeness(kinds)
    if comp["percent"] == 100 and inc.status == "evidence":
        inc.status = "diagram"; db.commit()
    # ИИ — главный: сразу анализирует фото и готовит ответ
    ai_res = await _run_ai(db, inc)
    ev_row.status = "ready"; db.commit()
    ev = db.query(models.Evidence).filter_by(incident_id=iid).order_by(models.Evidence.id.desc()).first()
    return {"saved": True, "sha256": h, "evidence_id": ev.id,
            "url": f"/api/v1/incidents/{iid}/evidence/{ev.id}/file",
            "gps": [proc["gps_lat"], proc["gps_lon"]],
            "completeness": comp, "ai": ai_res}


@router.get("/{iid}/evidence/{eid}/file")
def get_evidence_file(iid: int, eid: int,
                      authorization: str = Header(""),
                      token: str = Query("", description="JWT for <img> tags that cannot send headers"),
                      db: Session = Depends(get_db)):
    """Отдаёт фото ТОЛЬКО по JWT и только участникам инцидента + specialist/admin.
    Токен принимается в заголовке Authorization или в ?token= (для тегов <img>)."""
    raw = authorization[7:] if authorization.startswith("Bearer ") else token
    if not raw:
        raise HTTPException(401, "Missing token")
    u = user_from_token(raw, db)
    _can_read(iid, u, db)  # 403 if not participant / specialist / admin
    ev = db.query(models.Evidence).filter_by(id=eid, incident_id=iid).first()
    if not ev:
        raise HTTPException(404, "Evidence not found")
    # constrain to upload dir — never trust the stored path for traversal
    path = os.path.join(settings.UPLOAD_DIR, os.path.basename(ev.file_path))
    if not os.path.exists(path):
        raise HTTPException(404, "File missing")
    return FileResponse(path, media_type=ev.mime or "application/octet-stream")

@router.post("/{iid}/ai-analysis")
async def ai_analysis(iid: int, db: Session = Depends(get_db),
                      u: models.User = Depends(current_user)):
    """ИИ смотрит фото + triage, рисует схему и даёт довод. Сначала водителю, потом в админку."""
    inc = db.get(models.Incident, iid)
    if not inc: raise HTTPException(404, "Not found")
    return await _run_ai(db, inc)

@router.get("/{iid}/ai-history")
def ai_history(iid: int, limit: int = Query(20, ge=1, le=100),
               db: Session = Depends(get_db),
               u: models.User = Depends(current_user)):
    """История запусков ИИ + события обработки (MongoDB). SQL всегда хранит
    последний итог; здесь — полная хронология. Без Mongo: enabled=false."""
    _can_read(iid, u, db)
    return {"enabled": mongo.mongo_enabled(),
            "items": mongo.get_ai_history(iid, limit),
            "events": mongo.get_events(iid, limit)}

def _can_read(iid: int, u: models.User, db: Session) -> models.Incident:
    inc = db.get(models.Incident, iid)
    if not inc: raise HTTPException(404, "Not found")
    if u.role in ("specialist", "admin"): return inc
    if db.query(models.Participant).filter_by(incident_id=iid, user_id=u.id).first(): return inc
    raise HTTPException(403, "Not your incident")

@router.get("/{iid}/messages")
def get_messages(iid: int, db: Session = Depends(get_db),
                 u: models.User = Depends(current_user)):
    _can_read(iid, u, db)
    rows = db.query(models.Message).filter_by(incident_id=iid).order_by(models.Message.id).all()
    users = {x.id: x.full_name for x in db.query(models.User).all()}
    return [{"id": m.id, "from": users.get(m.sender_id, "?"), "role": m.sender_role,
             "text": m.text, "at": str(m.created_at)} for m in rows]

@router.post("/{iid}/messages", status_code=201)
def post_message(iid: int, body: schemas.MessageIn, db: Session = Depends(get_db),
                 u: models.User = Depends(current_user)):
    """Водитель жмёт кнопку-ответ («Понял, жду») — текст уходит сотруднику, и наоборот."""
    inc = _can_read(iid, u, db)
    if not body.text.strip(): raise HTTPException(400, "Пустое сообщение")
    m = models.Message(incident_id=iid, sender_id=u.id, sender_role=u.role, text=body.text.strip()[:1000])
    db.add(m); db.commit(); db.refresh(m)
    try:
        from ..services import push as push_svc
        push_svc.notify_participants(db, iid, u.id, "Yo'l Guard: новое сообщение",
                                     body.text.strip()[:120])
    except Exception:
        pass
    return {"id": m.id, "at": str(m.created_at)}
