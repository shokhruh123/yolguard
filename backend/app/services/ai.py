"""AI-анализ ДТП. Прод: Gemini API. Без ключа — честный эвристический fallback.
ВАЖНО: число пострадавших ИИ НЕ выдумывает — берёт из triage водителя.
Схема — черновик для человека, не юридический факт."""
import asyncio
import base64
import json
import httpx
from ..config import settings

# Model fallback chain: first that answers wins. Guards against a model being
# retired (404), overloaded (503) or rate-limited (429) — exactly what broke
# the old hard-coded gemini-2.5-flash. Override with GEMINI_MODEL in .env.
_DEFAULT_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3-flash-preview"]
_override = (getattr(settings, "GEMINI_MODEL", "") or "").strip()
GEMINI_MODELS = [_override] if _override else _DEFAULT_MODELS

def _model_url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def heuristic_svg(label_a: str = "A", label_b: str = "B") -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="220" viewBox="0 0 400 220">'
        '<rect width="400" height="220" fill="#0e1626"/>'
        '<rect y="70" width="400" height="80" fill="#1a2540"/>'
        '<line x1="0" y1="110" x2="400" y2="110" stroke="#f5a524" stroke-width="2" stroke-dasharray="12 8"/>'
        '<rect x="10" y="20" width="26" height="26" fill="#24314d"/><text x="23" y="38" fill="#9aa7bd" font-size="16" text-anchor="middle">P</text>'
        f'<rect x="80" y="76" width="86" height="30" rx="6" fill="#2b60a0"/><text x="123" y="96" fill="#fff" font-size="14" text-anchor="middle">{label_a}</text>'
        '<line x1="166" y1="91" x2="206" y2="91" stroke="#22c07a" stroke-width="3" marker-end="url(#ah)"/>'
        f'<rect x="228" y="104" width="86" height="30" rx="6" fill="#c0392b"/><text x="271" y="124" fill="#fff" font-size="14" text-anchor="middle">{label_b}</text>'
        '<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
        '<path d="M0,0 L8,4 L0,8" fill="none" stroke="#22c07a" stroke-width="2"/></marker></defs>'
        '<circle cx="212" cy="100" r="9" fill="none" stroke="#f5a524" stroke-width="3"/>'
        '<circle cx="212" cy="100" r="3" fill="#f5a524"/>'
        '<text x="212" y="160" fill="#9aa7bd" font-size="12" text-anchor="middle">предполагаемая точка контакта</text>'
        "</svg>"
    )


def heuristic_reason(triage: dict, kinds: list[str]) -> dict:
    has_injury = bool(triage.get("has_injury"))
    actions = []
    if has_injury:
        actions += ["Вызвать скорую (103) и ГАИ (102)", "Не перемещать пострадавших", "Оказать первую помощь"]
    elif triage.get("eligibility") == "red":
        actions += ["Вызвать ГАИ (102)", "Не убирать авто с полосы до разрешения"]
    else:
        actions += ["Завершить фотофиксацию", "Оба водителя подтверждают схему",
                    "Освободить полосу после подтверждения", "Дождаться claim-пакета"]
    return {
        "description": ("Эвристическая оценка: столкновение двух ТС, точка контакта — по фото повреждений. "
                        f"Получено фото: {len(kinds)}/6. Точную картину подтверждает специалист."),
        "casualties_note": ("Водитель отметил пострадавших — приоритет: скорая и ГАИ."
                            if has_injury else "По словам водителя, пострадавших нет."),
        "actions": actions,
    }


PROMPT = (
    "Ты — ассистент разбора ДТП для Европротокола (Узбекистан), помогаешь сотруднику ГАИ. "
    "Внимательно изучи фото повреждений и данные водителя. Ответь СТРОГО JSON без markdown:\n"
    '{"description": "подробный разбор 3-6 предложений: какие ТС участвовали (марка/цвет если видно на фото), '
    "по какой части пришёлся удар у каждого авто, характер и примерная сила повреждений, "
    'и наиболее вероятный сценарий столкновения (кто куда двигался) — с оговоркой «предположительно»", '
    '"impact_summary": "одной строкой: куда пришёлся удар (напр. «передний бампер — левое крыло»)", '
    '"actions": ["практичный шаг 1", "шаг 2", "..."], '
    '"svg": "<svg ...>вид сверху: дорога, авто A и B в вероятных позициях, стрелки движения, точка контакта</svg>"}.\n'
    "ПРАВИЛА: число/наличие пострадавших НЕ выдумывай — бери только из переданного флага has_injury. "
    "Не утверждай вину — используй «предположительно/вероятно». Схема — черновик для человека, не юридический факт. "
    "Если на фото чего-то не видно — честно скажи «на фото не видно». Язык ответа — русский."
)


async def analyze(triage: dict, kinds: list[str], images: list[bytes]) -> dict:
    """Возвращает {source, description, casualties_note, actions, svg}."""
    base = heuristic_reason(triage, kinds)
    key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    if not key:
        return {"source": "heuristic (нет GEMINI_API_KEY)", **base, "svg": heuristic_svg()}

    parts: list[dict] = [{"text": PROMPT + f"\nДанные: {json.dumps(triage, ensure_ascii=False)}, фото: {kinds}"}]
    for img in images[:3]:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(img).decode()}})
    payload = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.2}}

    last_err = "no model answered"
    async with httpx.AsyncClient(timeout=60) as client:
        for model in GEMINI_MODELS:
            for _attempt in range(2):  # one retry on transient overload
                try:
                    r = await client.post(f"{_model_url(model)}?key={key}", json=payload)
                    if r.status_code in (429, 503):  # overloaded -> retry, then next model
                        last_err = f"{model}: {r.status_code}"
                        await asyncio.sleep(1.5)
                        continue
                    if r.status_code == 404:  # model retired -> next model
                        last_err = f"{model}: 404"
                        break
                    r.raise_for_status()
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    start, end = text.find("{"), text.rfind("}")
                    data = json.loads(text[start:end + 1]) if start >= 0 else {}
                    desc = str(data.get("description", base["description"]))
                    impact = str(data.get("impact_summary", "")).strip()
                    if impact:
                        desc = f"{desc}\n\n🅰️🅱️ Удар: {impact}"
                    return {
                        "source": f"gemini:{model}",
                        "description": desc,
                        "casualties_note": base["casualties_note"],
                        "actions": list(data.get("actions", base["actions"])),
                        "svg": str(data.get("svg") or heuristic_svg()),
                    }
                except Exception as e:
                    last_err = f"{model}: {type(e).__name__}"
                    break
    return {"source": f"heuristic (Gemini недоступен: {last_err})", **base, "svg": heuristic_svg()}
