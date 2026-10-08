"""Yo'l Guard — панель сотрудника (desktop EXE). Тот же backend API.
Вход специалистом -> список (красные сверху) -> досье: triage, фото-ссылки,
чертёж ИИ, довод, пострадавшие, действия, переписка -> 2 кнопки пользователю."""
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.error
import json
import io
import os
import re
import tempfile
import webbrowser

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except Exception:
    HAS_PIL = False

API = "http://127.0.0.1:8002/api/v1"
TOKEN = ""
CASES = {}
IDS = []  # incident ids parallel to Listbox rows (no fragile string parsing)
CURRENT = None
THUMBS = []          # keep PhotoImage refs alive (tkinter GCs otherwise)
LAST_SVG = ""        # AI schema SVG for "open in browser"
LAST_SCHEMA_PATH = ""


def _sanitize_svg(svg):
    """Strip active content from server/AI SVG before opening in a browser."""
    if not svg or "<svg" not in svg.lower():
        return ""
    clean = re.sub(r"(?is)<script.*?</script\s*>", "", svg)
    clean = re.sub(r"(?i)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", clean)
    clean = re.sub(r"(?i)(href|xlink:href)\s*=\s*([\"']?)\s*javascript:[^\"'>]*\2", r"\1=\2#\2", clean)
    return clean[:50000]


def call(method, path, body=None, raw=False):
    req = urllib.request.Request(API + path, method=method,
                                 headers={"Authorization": f"Bearer {TOKEN}",
                                          "Content-Type": "application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=20) as r:
            out = r.read().decode()
            return out if raw else json.loads(out or "null")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:200]}")


def fetch_bytes(path):
    """GET binary (photo) with the auth header. `path` already starts with /api/v1."""
    base = API.rsplit("/api/v1", 1)[0]
    req = urllib.request.Request(base + path, method="GET",
                                 headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def do_login():
    global TOKEN
    try:
        j = call("POST", "/auth/login", {"phone": e_phone.get(), "password": e_pw.get()})
        TOKEN = j["access"]
        lbl_user.config(text="Вход: " + j["user"]["full_name"] + " (" + j["user"]["role"] + ")")
        refresh_list()
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))


def refresh_list():
    try:
        data = call("GET", "/admin/incidents?limit=200")
        rows = data.get("items", []) if isinstance(data, dict) else data
        total = data.get("total", len(rows)) if isinstance(data, dict) else len(rows)
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))
        return
    try:
        st = call("GET", "/admin/stats")
        lbl_stats.config(text=(f'ДТП: {st.get("incidents_total", "?")} | '
                               f'на проверке: {st.get("reviews_pending", "?")} | '
                               f'пользователи: {st.get("users_total", "?")} | '
                               f'фото: {st.get("evidence_total", "?")}'))
    except Exception:
        pass
    order = {"red": 0, "yellow": 1, "green": 2}
    rows.sort(key=lambda x: order.get(x["eligibility"], 3))
    CASES.clear()
    IDS.clear()
    lst.delete(0, tk.END)
    for x in rows:
        CASES[x["id"]] = x
        IDS.append(x["id"])
        flag = " [ПОСТРАДАВШИЕ]" if x["has_injury"] else ""
        lst.insert(tk.END, f'#{x["id"]} [{x["eligibility"]}] {x["code"]} {x["status"]}{flag}')
    lbl_count.config(text=f"Всего: {total}, показано: {len(rows)}")


def open_case(_ev=None):
    global CURRENT, LAST_SVG
    sel = lst.curselection()
    if not sel or sel[0] >= len(IDS):
        return
    iid = IDS[sel[0]]
    CURRENT = iid
    try:
        d = call("GET", f"/admin/incidents/{iid}")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))
        return
    LAST_SVG = (d.get("ai") or {}).get("svg", "")
    txt.config(state="normal")
    txt.delete("1.0", tk.END)
    t = d["triage"]
    txt.insert(tk.END, f'Случай #{d["incident"]["id"]} {d["incident"]["code"]} '
                       f'[{d["incident"]["eligibility"]}] {d["incident"]["status"]}\n')
    inj = f'ПОСТРАДАВШИХ: {t.get("injured_count", 0)}' if t.get("injured_count") else "пострадавших нет"
    txt.insert(tk.END, f'Данные водителя: {inj}'
                       f'{" | удар: " + t["impact_part"] if t.get("impact_part") else ""}'
                       f' | пешеход={t["has_pedestrian"]} вина={t["responsibility_accepted"]} '
                       f'доки={t["docs_valid"]} трезв={t["sober"]} согласие={t["damage_agreed"]}\n')
    if t.get("driver_comment"):
        txt.insert(tk.END, f'Комментарий водителя: {t["driver_comment"]}\n')
    txt.insert(tk.END, "Участники: " + ", ".join(
        f'{p["side"]}:{p["user"]}{" ✓" if p["confirmed"] else " …"}' for p in d["participants"]) + "\n")
    if d["ai"]:
        txt.insert(tk.END, f'\n--- Разбор ИИ ({d["ai"]["source"]}) ---\n{d["ai"]["description"]}\n')
        txt.insert(tk.END, f'Пострадавшие (из triage, ИИ не выдумывает): {d["ai"]["casualties_note"]}\n')
        pl = (d["ai"] or {}).get("plates") or {}
        if pl.get("a") or pl.get("b"):
            txt.insert(tk.END, f'Номера с фото: A={pl.get("a") or "—"} B={pl.get("b") or "—"}\n')
        sev = (d["ai"] or {}).get("damage_severity", "unknown")
        if sev and sev != "unknown":
            txt.insert(tk.END, f'Тяжесть ущерба: {sev}\n')
        txt.insert(tk.END, "Схема ИИ: черновик, см. кнопку «Открыть схему ИИ».\nЧто делать:\n")
        for a in d["ai"]["actions"]:
            txt.insert(tk.END, f"  - {a}\n")
    txt.insert(tk.END, f'\nВердикт: {(d["review"] or {}).get("verdict", "—")}\n--- Переписка ---\n')
    for m in d["messages"]:
        txt.insert(tk.END, f'[{m["from_role"]}] {m["text"]}\n')
    txt.config(state="disabled")
    _show_photos(d.get("evidence", []))


def _show_photos(evidence):
    """Фото-превью внутри панели (не ссылки). Требует Pillow."""
    global THUMBS
    for w in photos_frame.winfo_children():
        w.destroy()
    THUMBS = []
    if not evidence:
        ttk.Label(photos_frame, text="Фото нет").pack(side="left")
        return
    if not HAS_PIL:
        ttk.Label(photos_frame, text="(для превью нужен Pillow)").pack(side="left")
        return
    for e in evidence:
        try:
            raw = fetch_bytes(e["url"])
            im = Image.open(io.BytesIO(raw)); im.thumbnail((120, 120))
            ph = ImageTk.PhotoImage(im)
            THUMBS.append(ph)
            cell = ttk.Frame(photos_frame)
            cell.pack(side="left", padx=4)
            tk.Label(cell, image=ph).pack()
            ttk.Label(cell, text=e["kind"], font=("", 7)).pack()
        except Exception:
            ttk.Label(photos_frame, text=f'{e["kind"]}: ошибка').pack(side="left", padx=4)


def open_schema():
    global LAST_SCHEMA_PATH
    svg = _sanitize_svg(LAST_SVG)
    if not svg:
        messagebox.showinfo("Схема", "Схема ИИ ещё не готова.")
        return
    if LAST_SCHEMA_PATH and os.path.exists(LAST_SCHEMA_PATH):
        try: os.unlink(LAST_SCHEMA_PATH)
        except OSError: pass
    html = ("<!doctype html><meta charset='utf-8'>"
            "<body style='margin:0;background:#0b1220'>" + svg + "</body>")
    fd, path = tempfile.mkstemp(prefix="yolguard_schema_", suffix=".html")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(html)
    LAST_SCHEMA_PATH = path
    webbrowser.open("file:///" + path.replace("\\", "/"))


def send_msg():
    if CURRENT is None:
        return
    text = e_msg.get().strip()
    if not text:
        messagebox.showinfo("Инфо", "Пустое сообщение.")
        return
    try:
        call("POST", f"/admin/incidents/{CURRENT}/message", {"text": text[:1000]})
        e_msg.delete(0, tk.END)
        open_case()
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))


def verdict(v):
    if CURRENT is None:
        return
    # одно текстовое окно на всё: и сообщение водителю, и комментарий к вердикту
    comment = e_msg.get().strip()
    try:
        d = call("GET", f"/admin/incidents/{CURRENT}")
        rid = (d["review"] or {}).get("id")
        if not rid:
            messagebox.showinfo("Инфо", "Ревью-кейс не создан (green-случай). Напишите текст вручную.")
            return
        j = call("POST", f"/reviews/{rid}", {"verdict": v, "comment": comment})
        messagebox.showinfo("Отправлено", j.get("sent_to_user", v))
        open_case()
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))


def rerun_ai():
    """Перезапустить ИИ-анализ по фото случая (когда разбор слабый/пустой)."""
    if CURRENT is None:
        return
    try:
        j = call("POST", f"/incidents/{CURRENT}/ai-analysis")
        messagebox.showinfo("ИИ", f'Готово ({j.get("source", "?")}). Схема обновлена.')
        open_case()
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))


def build_claim():
    """Собрать страховой пакет (нужно подтверждение создателя случая)."""
    if CURRENT is None:
        return
    try:
        j = call("POST", f"/incidents/{CURRENT}/claim-package")
        messagebox.showinfo("Пакет собран", "package_hash:\n" + j.get("package_hash", "?"))
        open_case()
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))


root = tk.Tk()
root.title("Yo'l Guard — панель сотрудника")
root.geometry("760x640")

top = ttk.Frame(root, padding=8)
top.pack(fill="x")
ttk.Label(top, text="API:").pack(side="left")
e_api = ttk.Entry(top, width=32)
e_api.insert(0, API)
e_api.pack(side="left", padx=4)


def save_api():
    global API
    API = e_api.get().strip().rstrip("/")
    messagebox.showinfo("API", "Адрес: " + API)


ttk.Button(top, text="ОК", command=save_api).pack(side="left")
e_phone = ttk.Entry(top, width=16)
e_phone.pack(side="left", padx=4)
e_pw = ttk.Entry(top, width=10, show="*")
e_pw.pack(side="left")
ttk.Button(top, text="Войти", command=do_login).pack(side="left", padx=4)
lbl_user = ttk.Label(top, text="Не вошли")
lbl_user.pack(side="left", padx=6)

statsbar = ttk.Frame(root, padding=(8, 0))
statsbar.pack(fill="x")
lbl_stats = ttk.Label(statsbar, text="Статистика: обновите список")
lbl_stats.pack(side="left")
lbl_count = ttk.Label(statsbar, text="")
lbl_count.pack(side="right")

mid = ttk.Frame(root, padding=8)
mid.pack(fill="both", expand=True)
ttk.Button(mid, text="Обновить список", command=refresh_list).pack(anchor="w")
lst = tk.Listbox(mid, height=8)
lst.pack(fill="x", pady=4)
lst.bind("<Double-Button-1>", open_case)
ttk.Button(mid, text="Открыть досье", command=lambda: open_case()).pack(anchor="w")
txt = tk.Text(mid, height=16, state="disabled", wrap="word")
txt.pack(fill="both", expand=True, pady=4)
ttk.Label(mid, text="Фото водителя:").pack(anchor="w")
photos_frame = ttk.Frame(mid)
photos_frame.pack(fill="x", pady=4)
ttk.Button(mid, text="Открыть схему ИИ", command=open_schema).pack(anchor="w")

bot = ttk.Frame(root, padding=8)
bot.pack(fill="x")
ttk.Label(bot, text="Текст водителю:").pack(side="left")
e_msg = ttk.Entry(bot, width=45)
e_msg.pack(side="left", padx=4)
ttk.Button(bot, text="Отправить текст", command=send_msg).pack(side="left")
ttk.Button(bot, text="🔄 ИИ заново", command=rerun_ai).pack(side="left", padx=4)
ttk.Button(bot, text="🚓 Выезжаем", command=lambda: verdict("needs_field")).pack(side="left")
ttk.Button(bot, text="✅ Зарегистрировано успешно", command=lambda: verdict("approved")).pack(side="left", padx=4)
ttk.Button(bot, text="📦 Собрать пакет", command=build_claim).pack(side="left")

root.mainloop()
