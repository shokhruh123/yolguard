"""Deterministic Europrotocol eligibility. LLM must NEVER override this."""
from dataclasses import dataclass

@dataclass
class Triage:
    has_injury: bool = False
    has_pedestrian: bool = False
    vehicle_count: int = 2
    third_party_damage: bool = False
    responsibility_accepted: bool = False
    docs_valid: bool = False
    sober: bool = False
    damage_agreed: bool = False

def evaluate(t: Triage) -> tuple[str, str]:
    """Returns (green|yellow|red, reason). Red = stop simplified flow."""
    if t.has_injury: return "red", "Есть пострадавшие — вызовите 102/103, упрощённый процесс запрещён."
    if t.has_pedestrian: return "red", "Участвует пешеход — только официальный процесс."
    if t.vehicle_count != 2: return "red", "Нужно ровно 2 ТС для Европротокола."
    if t.third_party_damage: return "red", "Повреждено чужое имущество/инфраструктура — к ГАИ."
    if not t.sober: return "red", "Признаки опьянения — упрощённый процесс запрещён."
    if not t.responsibility_accepted: return "red", "Нет признания вины одним водителем."
    if not t.damage_agreed: return "yellow", "Нет согласия по перечню повреждений — нужен специалист."
    if not t.docs_valid: return "yellow", "Проверьте страховку/документы обоих водителей."
    return "green", "Предварительно подходит под Европротокол. Итог подтверждает специалист/страховщик."

REQUIRED_EVIDENCE = ["scene_overview", "both_vehicles", "plate_a", "plate_b",
                     "road_marking", "damage_close"]

def completeness(have: list[str]) -> dict:
    missing = [k for k in REQUIRED_EVIDENCE if k not in have]
    pct = round((len(REQUIRED_EVIDENCE) - len(missing)) / len(REQUIRED_EVIDENCE) * 100)
    return {"percent": pct, "missing": missing,
            "hint": ("Сфотографируйте: " + ", ".join(missing)) if missing else "Комплект полный"}
