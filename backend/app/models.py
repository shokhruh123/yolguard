"""Tables. 3NF: vehicle/incident/evidence facts separated, no transitive deps."""
from sqlalchemy import (Column, Integer, String, DateTime, Date, Numeric, Text,
                        ForeignKey, UniqueConstraint, CheckConstraint, Index, func)
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False, default="driver")  # driver|specialist|admin|insurer
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    __table_args__ = (CheckConstraint("role IN ('driver','specialist','admin','insurer')"),)

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plate = Column(String(20), unique=True, nullable=False)
    make = Column(String(60), nullable=False)
    model = Column(String(60), nullable=False)
    year = Column(Integer, nullable=False)
    vin = Column(String(32))
    insurance_policy = Column(String(60))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    code = Column(String(12), unique=True, nullable=False)  # short join code for 2nd driver
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="triage")
    # triage|evidence|diagram|review|ready|escalated|closed
    has_injury = Column(Integer, nullable=False, default=0)
    has_pedestrian = Column(Integer, nullable=False, default=0)
    vehicle_count = Column(Integer, nullable=False, default=2)
    third_party_damage = Column(Integer, nullable=False, default=0)
    responsibility_accepted = Column(Integer, nullable=False, default=0)
    docs_valid = Column(Integer, nullable=False, default=0)
    sober = Column(Integer, nullable=False, default=0)
    damage_agreed = Column(Integer, nullable=False, default=0)
    impact_part = Column(String(120))      # по какой части пришёлся удар (со слов водителя)
    driver_comment = Column(Text)          # свободный комментарий водителя
    injured_count = Column(Integer, nullable=False, default=0)  # число пострадавших (только из triage)
    eligibility = Column(String(10), nullable=False, default="unknown")  # green|yellow|red
    eligibility_reason = Column(Text)
    lat = Column(Numeric(9, 6))
    lon = Column(Numeric(9, 6))
    occurred_at = Column(DateTime, server_default=func.now(), nullable=False)
    cleared_lane_at = Column(DateTime)  # north-star metric source

class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    side = Column(String(1), nullable=False)  # A|B
    confirmed = Column(Integer, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("incident_id", "side"), UniqueConstraint("incident_id", "user_id"))

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(30), nullable=False)
    # scene_overview|both_vehicles|plate_a|plate_b|road_marking|damage_close|doc_photo|other
    file_path = Column(String(255), nullable=False)
    sha256 = Column(String(64), nullable=False)
    taken_at = Column(DateTime, server_default=func.now(), nullable=False)
    quality = Column(String(10), nullable=False, default="unknown")  # ok|retake|unknown
    note = Column(Text)
    gps_lat = Column(Numeric(9, 6))  # from photo EXIF, if present
    gps_lon = Column(Numeric(9, 6))
    mime = Column(String(20))  # validated content type: image/jpeg|png|webp
    size_bytes = Column(Integer)  # processed file size on disk
    status = Column(String(16), nullable=False, default="stored")  # stored|processing|ready|failed
    storage = Column(String(16), nullable=False, default="local")  # local|s3|...

class Diagram(Base):
    __tablename__ = "diagrams"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
    svg = Column(Text, nullable=False)  # draft only, NOT legal fact
    approved_a = Column(Integer, nullable=False, default=0)
    approved_b = Column(Integer, nullable=False, default=0)

class ClaimPackage(Base):
    __tablename__ = "claim_packages"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
    payload_json = Column(Text, nullable=False)
    package_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class ReviewCase(Base):
    __tablename__ = "review_cases"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
    assignee_id = Column(Integer, ForeignKey("users.id"))
    verdict = Column(String(20), nullable=False, default="pending")  # pending|approved|needs_field|rejected
    comment = Column(Text)

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
    source = Column(String(40), nullable=False, default="heuristic")  # gemini|heuristic
    description = Column(Text, nullable=False, default="")
    casualties_note = Column(Text, nullable=False, default="")
    actions_json = Column(Text, nullable=False, default="[]")
    svg = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class Message(Base):
    """Переписка водитель <-> сотрудник по инциденту."""
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_role = Column(String(20), nullable=False, default="driver")
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class PushSubscription(Base):
    """Web Push подписки (браузер/SW). По одной строке на endpoint."""
    __tablename__ = "push_subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

Index("ix_evidence_incident_kind", Evidence.incident_id, Evidence.kind)
