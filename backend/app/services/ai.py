"""AI-анализ ДТП. Прод: Gemini API. Без ключа — честный эвристический fallback.
ВАЖНО: число пострадавших ИИ НЕ выдумывает — берёт из triage водителя.
Схема — черновик для человека, не юридический факт."""
import asyncio
import base64
import html
import json
import logging
import time
import httpx
from ..config import settings

log = logging.getLogger("yolguard.ai")

# Model fallback chain: first that answers wins. Guards against a model being
# retired (404), overloaded (503) or rate-limited (429) — exactly what broke
# the old hard-coded gemini-2.5-flash. Override with GEMINI_MODEL in .env.
_DEFAULT_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3-flash-preview"]
_override = (getattr(settings, "GEMINI_MODEL", "") or "").strip()
GEMINI_MODELS = [_override] if _override else _DEFAULT_MODELS

def _model_url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def heuristic_svg(label_a: str = "A", label_b: str = "B", impact: str = "") -> str:
    """Дорожная сцена сверху: асфальт, разметка, два авто, стрелка движения,
    звезда контакта. Точка контакта и подпись зависят от слов водителя
    (impact_part), поэтому схема НЕ одинаковая для всех случаев."""
    la, lb = html.escape(label_a[:12]), html.escape(label_b[:12])
    seed = sum(ord(ch) for ch in (impact or "")) % 110
    cx = 155 + seed  # звезда контакта гуляет вдоль дороги
    cap = html.escape((impact or "").strip()[:40])
    cap_svg = (f'<text x="200" y="248" fill="#9aa7bd" font-size="12" text-anchor="middle">{cap}</text>'
               if cap else "")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="260" viewBox="0 0 400 260">'
        '<rect width="400" height="260" fill="#22252d"/>'
        '<rect y="0" width="400" height="46" fill="#243020"/>'
        '<rect y="214" width="400" height="46" fill="#243020"/>'
        '<rect y="46" width="400" height="168" fill="#414754"/>'
        '<rect y="50" width="400" height="4" fill="#d8dce3"/>'
        '<rect y="206" width="400" height="4" fill="#d8dce3"/>'
        '<line x1="0" y1="130" x2="400" y2="130" stroke="#f5a524" stroke-width="3" stroke-dasharray="16 12"/>'
        # авто A: вид сверху
        '<g transform="translate(115,98) rotate(-8)">'
        '<rect x="-14" y="-24" width="10" height="8" rx="2" fill="#14161b"/>'
        '<rect x="-14" y="16" width="10" height="8" rx="2" fill="#14161b"/>'
        '<rect x="36" y="-24" width="10" height="8" rx="2" fill="#14161b"/>'
        '<rect x="36" y="16" width="10" height="8" rx="2" fill="#14161b"/>'
        '<rect x="-46" y="-17" width="92" height="34" rx="9" fill="#2b60a0"/>'
        '<rect x="6" y="-13" width="26" height="26" rx="4" fill="#1b3a63"/>'
        '<rect x="-40" y="-13" width="8" height="7" rx="2" fill="#ffe9a8"/>'
        '<rect x="-40" y="6" width="8" height="7" rx="2" fill="#ffe9a8"/>'
        f'<text x="0" y="6" fill="#fff" font-size="15" font-weight="bold" text-anchor="middle">{la}</text>'
        '</g>'
        # авто B: вид сверху
        '<g transform="translate(265,158) rotate(6)">'
        '<rect x="-14" y="-24" width="10" height="8" rx="2" fill="#14161b"/>'
        '<rect x="-14" y="16" width="10" height="8" rx="2" fill="#14161b"/>'
        '<rect x="36" y="-24" width="10" height="8" rx="2" fill="#14161b"/>'
        '<rect x="36" y="16" width="10" height="8" rx="2" fill="#14161b"/>'
        '<rect x="-46" y="-17" width="92" height="34" rx="9" fill="#c0392b"/>'
        '<rect x="-32" y="-13" width="26" height="26" rx="4" fill="#7c241a"/>'
        '<rect x="38" y="-13" width="8" height="7" rx="2" fill="#ffe9a8"/>'
        '<rect x="38" y="6" width="8" height="7" rx="2" fill="#ffe9a8"/>'
        f'<text x="0" y="6" fill="#fff" font-size="15" font-weight="bold" text-anchor="middle">{lb}</text>'
        '</g>'
        # стрелка движения B
        '<line x1="350" y1="192" x2="292" y2="172" stroke="#e74c3c" stroke-width="5" marker-end="url(#ah2)"/>'
        '<defs><marker id="ah2" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">'
        '<path d="M0,0 L9,4.5 L0,9" fill="none" stroke="#e74c3c" stroke-width="2.5"/></marker></defs>'
        # звезда контакта
        f'<polygon points="{cx},{108} {cx+5},{121} {cx+18},{121} {cx+8},{129} {cx+12},{142} {cx},{134} {cx-12},{142} {cx-8},{129} {cx-18},{121} {cx-5},{121}" fill="#f5a524"/>'
        f'<text x="{cx}" y="100" fill="#f5a524" font-size="11" text-anchor="middle">удар</text>'
        '<text x="200" y="30" fill="#9aa7bd" font-size="12" text-anchor="middle">вид сверху · черновик, не юридический факт</text>'
        f'{cap_svg}'
        "</svg>"
    )


def _sanitize_svg(svg: str) -> str:
    """Strip active content from LLM-produced SVG (script tags, event handlers,
    javascript: URLs). Keeps shapes/text. Falls back to heuristic on garbage."""
    import re
    if not svg or "<svg" not in svg.lower():
        return heuristic_svg()
    clean = re.sub(r"(?is)<script.*?</script\s*>", "", svg)
    clean = re.sub(r"(?i)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", clean)
    clean = re.sub(r"(?i)(href|xlink:href)\s*=\s*([\"']?)\s*javascript:[^\"'>]*\2", r"\1=\2#\2", clean)
    return clean[:50000]


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
        "plates": {"a": "", "b": ""},
        "damage_severity": "unknown",  # light|medium|heavy|unknown
    }


PROMPT = (
    "Ты — ассистент разбора ДТП для Европротокола (Узбекистан), помогаешь сотруднику ГАИ. "
    "Внимательно изучи фото повреждений и данные водителя. Ответь СТРОГО JSON без markdown:\n"
    '{"description": "подробный разбор 3-6 предложений: какие ТС участвовали (марка/цвет если видно на фото), '
    "по какой части пришёлся удар у каждого авто, характер и примерная сила повреждений, "
    'и наиболее вероятный сценарий столкновения (кто куда двигался) — с оговоркой «предположительно»", '
    '"impact_summary": "одной строкой: куда пришёлся удар (напр. «передний бампер — левое крыло»)", '
    '"plates": {"a": "госномер авто A если читается на фото, иначе \\"\\"", '
    '"b": "госномер авто B если читается, иначе \\"\\""}, '
    '"damage_severity": "light|medium|heavy|unknown — общая тяжесть видимых повреждений", '
    '"actions": ["практичный шаг 1", "шаг 2", "..."], '
    '"svg": "<svg ...>вид сверху: дорога, авто A и B в вероятных позициях, стрелки движения, точка контакта</svg>"}.\n'
    "ПРАВИЛА: число/наличие пострадавших НЕ выдумывай — бери только из переданного флага has_injury. "
    "Не утверждай вину — используй «предположительно/вероятно». Схема — черновик для человека, не юридический факт. "
    "Если на фото чего-то не видно — честно скажи «на фото не видно». Язык ответа — русский."
)


async def analyze(triage: dict, kinds: list[str], images: list[bytes]) -> dict:
    """Возвращает {source, description, casualties_note, actions, svg, plates, damage_severity}."""
    base = heuristic_reason(triage, kinds)
    impact = str(triage.get("impact_part", "") or "")
    key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    if not key:
        return {"source": "heuristic (нет GEMINI_API_KEY)", **base,
                "svg": heuristic_svg(impact=impact)}
    parts: list[dict] = [{"text": PROMPT + f"\nДанные: {json.dumps(triage, ensure_ascii=False)}, фото: {kinds}"}]
    for img in images[:3]:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(img).decode()}})
    payload = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.2}}

    last_err = "no model answered"
    t_start = time.monotonic()
    async with httpx.AsyncClient(timeout=20) as client:
        for model in GEMINI_MODELS:
            try:
                r = await client.post(f"{_model_url(model)}?key={key}", json=payload)
                if r.status_code in (429, 503):  # overloaded -> next model
                    last_err = f"{model}: {r.status_code}"
                    log.warning("ai %s overloaded (%s), next model", model, r.status_code)
                    continue
                if r.status_code == 404:  # model retired -> next model
                    last_err = f"{model}: 404"
                    log.warning("ai %s retired (404), next model", model)
                    continue
                r.raise_for_status()
                try:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError, TypeError, ValueError):
                    # safety-block / unexpected shape — treat as model failure
                    last_err = f"{model}: bad_response"
                    log.warning("ai %s bad response shape", model)
                    continue
                start, end = text.find("{"), text.rfind("}")
                data = json.loads(text[start:end + 1]) if start >= 0 else {}
                desc = str(data.get("description", base["description"]))
                impact = str(data.get("impact_summary", "")).strip()
                if impact:
                    desc = f"{desc}\n\n🅰️🅱️ Удар: {impact}"
                # SVG от LLM — чужой контент: убираем script/on* перед сохранением
                svg_raw = str(data.get("svg") or heuristic_svg(impact=impact))
                plates = data.get("plates") or {}
                sev = str(data.get("damage_severity", "unknown")).lower()
                if sev not in ("light", "medium", "heavy"):
                    sev = "unknown"
                log.info("ai answered via %s in %.1fs", model, time.monotonic() - t_start)
                return {
                    "source": f"gemini:{model}",
                    "description": desc,
                    "casualties_note": base["casualties_note"],
                    "actions": list(data.get("actions", base["actions"])),
                    "svg": _sanitize_svg(svg_raw),
                    "plates": {"a": str(plates.get("a", ""))[:20],
                               "b": str(plates.get("b", ""))[:20]},
                    "damage_severity": sev,
                }
            except Exception as e:
                last_err = f"{model}: {type(e).__name__}"
                log.warning("ai %s failed: %s", model, type(e).__name__)
                continue
    log.warning("ai fallback to heuristic: %s", last_err)
    return {"source": f"heuristic (Gemini недоступен: {last_err})", **base,
            "svg": heuristic_svg(impact=impact)}
