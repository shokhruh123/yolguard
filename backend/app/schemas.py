"""DTO with validation. All inputs validated before DB."""
from pydantic import BaseModel, Field
from typing import Optional

class RegisterIn(BaseModel):
    phone: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=6, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)

class LoginIn(BaseModel):
    phone: str
    password: str

class VehicleIn(BaseModel):
    plate: str = Field(min_length=3, max_length=20)
    make: str = Field(min_length=2, max_length=60)
    model: str = Field(min_length=1, max_length=60)
    year: int = Field(ge=1980, le=2030)

class IncidentCreate(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None

class TriageIn(BaseModel):
    has_injury: bool = False
    has_pedestrian: bool = False
    vehicle_count: int = 2
    third_party_damage: bool = False
    responsibility_accepted: bool = False
    docs_valid: bool = False
    sober: bool = True
    damage_agreed: bool = False
    impact_part: str = Field(default="", max_length=120)   # по какой части удар
    driver_comment: str = Field(default="", max_length=1000)  # коммент водителя
    injured_count: int = Field(default=0, ge=0, le=50)     # число пострадавших

class EvidenceIn(BaseModel):
    kind: str
    file_path: str = Field(min_length=1, max_length=255)

class DiagramIn(BaseModel):
    label_a: str = "A"
    label_b: str = "B"

class ReviewIn(BaseModel):
    verdict: str  # approved|needs_field|rejected
    comment: Optional[str] = None

class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
