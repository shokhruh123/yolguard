/* Yo'l Guard mobile client. Same /api/v1 backend.
   Web + Android WebView share this file. IDs used here must exist in index.html. */
let API = localStorage.getItem("yg_api") || "http://127.0.0.1:8002/api/v1";
let TOKEN = localStorage.getItem("yg_token") || "";
let INC = JSON.parse(localStorage.getItem("yg_inc") || "null");
const $ = (id) => document.getElementById(id);
const hdr = () => ({"Content-Type": "application/json", Authorization: "Bearer " + TOKEN});
const KINDS = ["scene_overview", "both_vehicles", "plate_a", "plate_b", "road_marking", "damage_close"];
const KIND_RU = {scene_overview: "Общий план", both_vehicles: "Оба авто", plate_a: "Номер A",
  plate_b: "Номер B", road_marking: "Разметка", damage_close: "Повреждение"};
let HAVE = [];
try { HAVE = JSON.parse(localStorage.getItem("yg_have_" + (INC && INC.id)) || "[]"); } catch { HAVE = []; }
function saveHave() {
  try {
    if (INC) localStorage.setItem("yg_have_" + INC.id, JSON.stringify(HAVE));
  } catch {}
}

/* ---------- helpers ---------- */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}
let toastTimer = 0;
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 3200);
}
/* fetch wrapper: never throws raw to UI, returns {ok, status, json} */
async function api(path, opts) {
  opts = opts || {};
  opts.headers = opts.headers || hdr();
  try {
    const r = await fetch(API + path, opts);
    let j = null;
    try { j = await r.json(); } catch { j = null; }
    if (!r.ok) {
      const detail = (j && (j.detail || j.msg)) || ("HTTP " + r.status);
      return {ok: false, status: r.status, json: j, error: detail};
    }
    return {ok: true, status: r.status, json: j};
  } catch (e) {
    return {ok: false, status: 0, json: null, error: "Нет связи с сервером"};
  }
}
function busy(btn, on) {
  if (!btn) return;
  btn.disabled = !!on;
  btn.classList.toggle("busy", !!on);
}
function needInc() {
  if (!INC) { toast("Сначала нажмите «Я попал в ДТП» на главном экране"); go("scr-home"); return false; }
  return true;
}

/* tabs */
function paintTabs(id) {
  document.querySelectorAll(".tab").forEach((x) => {
    const on = x.dataset.s === id;
    x.classList.toggle("active", on);
    x.setAttribute("aria-selected", on ? "true" : "false");
  });
  document.querySelectorAll(".screen").forEach((x) => x.classList.toggle("active", x.id === id));
}
document.querySelectorAll(".tab").forEach((b) =>
  b.addEventListener("click", () => paintTabs(b.dataset.s)));
function go(id) { paintTabs(id); }

/* wizard pager */
let WP = 1;
function showW(n) {
  WP = Math.min(4, Math.max(1, n));
  [1, 2, 3, 4].forEach((i) => $("w" + i).classList.toggle("active", i === WP));
  $("wStep").textContent = WP;
  $("wTitle").textContent = ["Проверка eligibility", "Фотофиксация", "Ответ ИИ", "Ответ сотрудника"][WP - 1];
  if (WP === 3) loadAI();
  if (WP === 4) loadMsgs();
}
$("wPrev").onclick = () => showW(WP - 1);
$("wNext").onclick = () => showW(WP + 1);

$("gApi").value = API;
$("btnApi").onclick = () => {
  API = $("gApi").value.trim().replace(/\/$/, "");
  localStorage.setItem("yg_api", API);
  ping(); toast("API: " + API);
};
async function ping() {
  try {
    const r = await fetch(API.replace("/api/v1", "") + "/health");
    const dot = $("netDot");
    dot.classList.toggle("on", r.ok);
    dot.setAttribute("aria-label", r.ok ? "Сервер на связи" : "Нет связи с сервером");
  } catch { $("netDot").classList.remove("on"); }
}
setInterval(() => { if (!document.hidden) ping(); }, 8000); ping();

function paint() {
  $("stCode").textContent = INC ? INC.code : "—";
  $("stStatus").textContent = INC ? INC.status : "—";
  $("stComp").textContent = HAVE.length + "/6";
  const bar = $("evBar");
  bar.style.width = (HAVE.length / 6) * 100 + "%";
  bar.parentElement.setAttribute("aria-valuenow", HAVE.length);
  $("evHint").textContent = HAVE.length >= 6 ? "Комплект полный"
    : "Осталось: " + KINDS.filter((k) => !HAVE.includes(k)).map((k) => KIND_RU[k]).join(", ");
  $("evChips").innerHTML = KINDS.map((k) =>
    `<span class="chip${HAVE.includes(k) ? " done" : ""}">${esc(KIND_RU[k])}</span>`).join("");
}
paint();
if (INC) { $("stCode").textContent = INC.code; $("stStatus").textContent = INC.status; }

$("btnLogin").onclick = async (e) => {
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/auth/login", {method: "POST",
    body: JSON.stringify({phone: $("gPhone").value.trim(), password: $("gPw").value})});
  busy(btn, false);
  if (res.ok && res.json.access) {
    TOKEN = res.json.access; localStorage.setItem("yg_token", TOKEN);
    toast("Вход выполнен"); go("scr-home");
  } else toast("Ошибка входа: " + (res.error || "проверьте данные"));
};

$("btnSos").onclick = async (e) => {
  if (!TOKEN) { toast("Сначала войдите во вкладке Гараж"); go("scr-garage"); return; }
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents", {method: "POST", body: "{}"});
  busy(btn, false);
  if (!res.ok) { toast("Не удалось создать случай: " + res.error); return; }
  INC = res.json; localStorage.setItem("yg_inc", JSON.stringify(INC));
  HAVE = []; saveHave(); paint(); go("scr-case"); showW(1);
};

/* Второй участник подключается по коду сессии с главного экрана */
$("btnJoin").onclick = async (e) => {
  if (!TOKEN) { toast("Сначала войдите во вкладке Гараж"); go("scr-garage"); return; }
  const iid = parseInt(($("joinId").value || "").trim(), 10);
  const code = ($("joinCode").value || "").trim().toUpperCase();
  if (!iid || !code) { toast("Введите ID случая и код сессии"); return; }
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents/" + iid + "/join?code=" + encodeURIComponent(code), {method: "POST"});
  busy(btn, false);
  if (!res.ok) { toast("Не удалось подключиться: " + res.error); return; }
  INC = {id: iid, code: code, status: "evidence"};
  localStorage.setItem("yg_inc", JSON.stringify(INC));
  HAVE = []; saveHave(); paint();
  toast("Вы подключены как сторона B");
  go("scr-case"); showW(2);
};

$("cInjCount").addEventListener("input", () => {
  let v = Math.max(0, Math.min(50, parseInt($("cInjCount").value || "0", 10) || 0));
  $("cInjCount").value = v;
  if (v > 0) $("cInj").checked = true;
});

$("btnTriage").onclick = async (e) => {
  if (!needInc()) return;
  const body = {has_injury: $("cInj").checked, has_pedestrian: $("cPed").checked,
    responsibility_accepted: $("cResp").checked, docs_valid: $("cDocs").checked,
    sober: $("cSober").checked, damage_agreed: $("cAgreed").checked,
    vehicle_count: 2, third_party_damage: false,
    injured_count: Math.max(0, Math.min(50, parseInt($("cInjCount").value || "0", 10) || 0)),
    impact_part: $("cImpact").value || "", driver_comment: $("cComment").value.trim()};
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents/" + INC.id + "/triage", {method: "POST", body: JSON.stringify(body)});
  busy(btn, false);
  if (!res.ok) { toast("Проверка не удалась: " + res.error); return; }
  const j = res.json;
  const box = $("triageOut");
  box.className = "verdict " + (j.eligibility === "green" ? "green" : j.eligibility === "red" ? "red" : "yellow");
  box.textContent = j.eligibility + ": " + j.reason;
  INC.status = j.status;
  localStorage.setItem("yg_inc", JSON.stringify(INC)); paint();
  if (j.eligibility === "red") toast("Красный сценарий: следуйте официальному процессу (102).");
  else showW(2);
};

/* Демо-метка без фото (для десктопа без камеры). Настоящие фото — через «Сфотографировать». */
$("btnEv").onclick = async (e) => {
  if (!needInc()) return;
  const kind = $("evKind").value;
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents/" + INC.id + "/evidence",
    {method: "POST", body: JSON.stringify({kind, file_path: kind + "_" + Date.now() + ".jpg"})});
  busy(btn, false);
  if (!res.ok) { toast("Не удалось: " + res.error); return; }
  HAVE = [...new Set([...HAVE, kind])]; saveHave(); paint();
  if (res.json.completeness && res.json.completeness.percent === 100) showW(3);
};

$("btnDiagram").onclick = async (e) => {
  if (!needInc()) return;
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents/" + INC.id + "/diagram", {method: "POST", body: "{}"});
  busy(btn, false);
  if (!res.ok) { toast("Схема не собралась: " + res.error); return; }
  $("svgBox").innerHTML = res.json.svg || "";
};

$("btnConfirm").onclick = async (e) => {
  if (!needInc()) return;
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents/" + INC.id + "/confirm", {method: "POST"});
  busy(btn, false);
  toast(res.ok ? "Подтверждено. Второй водитель подтверждает со своего телефона." : "Ошибка: " + res.error);
};

/* Камера: реальное фото -> evidence-upload */
$("camInput").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  e.target.value = "";
  if (!f || !needInc()) return;
  const kind = $("evKind").value;
  const url = URL.createObjectURL(f);
  const img = document.createElement("img");
  img.alt = KIND_RU[kind] || kind;
  img.onload = () => URL.revokeObjectURL(url);
  img.src = url;
  $("thumbs").appendChild(img);
  const fd = new FormData();
  fd.append("kind", kind);
  fd.append("file", f, f.name || "photo.jpg");
  toast("Загружаем фото…");
  let res;
  try {
    const r = await fetch(API + "/incidents/" + INC.id + "/evidence-upload", {
      method: "POST", headers: {Authorization: "Bearer " + TOKEN}, body: fd});
    res = {ok: r.ok, json: await r.json().catch(() => null)};
    if (!r.ok) res.error = (res.json && res.json.detail) || ("HTTP " + r.status);
  } catch { res = {ok: false, error: "Нет связи с сервером"}; }
  if (res.ok && res.json && res.json.saved) {
    HAVE = [...new Set([...HAVE, kind])]; saveHave(); paint();
    toast("Фото сохранено");
    if (res.json.completeness && res.json.completeness.percent === 100) showW(3);
  } else toast("Ошибка загрузки: " + (res.error || "неизвестная"));
});

/* ИИ — главный: анализирует сам, без кнопки. Показывает схему + текст + фото-ответ */
let aiLoadedFor = 0;
async function loadAI() {
  if (!INC || aiLoadedFor === INC.id) return;
  aiLoadedFor = INC.id;
  $("aiBox").textContent = "ИИ анализирует фото...";
  $("aiRetry").style.display = "none";
  const res = await api("/incidents/" + INC.id + "/ai-analysis", {method: "POST"});
  if (!res.ok) {
    $("aiBox").textContent = "ИИ недоступен, попробуйте позже";
    $("aiRetry").style.display = "";
    aiLoadedFor = 0;
    return;
  }
  const j = res.json;
  $("aiBox").innerHTML = j.svg || "";
  const t = $("aiText");
  t.style.display = "block";
  t.innerHTML = `<b>ИИ (${esc(j.source)})</b><br/>${esc(j.description).replace(/\n/g, "<br/>")}`
    + `<br/><br/><b>Пострадавшие:</b> ${esc(j.casualties_note)}`
    + `<br/><b>Что делать:</b><ul class="ai-actions">`
    + `${(j.actions || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul>`;
}
$("aiRetry").onclick = () => { aiLoadedFor = 0; loadAI(); };

$("btnClaim").onclick = async (e) => {
  if (!needInc()) return;
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents/" + INC.id + "/claim-package", {method: "POST"});
  busy(btn, false);
  $("claimOut").textContent = JSON.stringify(res.json, null, 2);
  if (!res.ok && res.status === 403)
    toast("Пакет собирает сотрудник. Войдите специалистом во вкладке Гараж.");
  else if (!res.ok) toast("Пакет не собран: " + res.error);
};

/* Быстрый вход специалистом: берёт логин/пароль из вкладки Гараж (по умолчанию — демо) */
$("btnSpecLogin").onclick = async (e) => {
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/auth/login", {method: "POST",
    body: JSON.stringify({phone: $("gPhone").value.trim() || "+998900000002",
      password: $("gPw").value || "spec1234"})});
  busy(btn, false);
  if (res.ok && res.json.access) {
    TOKEN = res.json.access; localStorage.setItem("yg_token", TOKEN);
    toast("Вы вошли как специалист. Жмите «Пакет для страховой».");
  } else toast("Ошибка: " + (res.error || "проверьте данные"));
};

/* ---------- Админ-панель сотрудника ---------- */
let admSkip = 0; const admLimit = 20;
function admFilters() {
  return {status: $("fltStatus").value, eligibility: $("fltElig").value,
    q: $("fltSearch").value.trim().toLowerCase()};
}
$("btnAdminReload").onclick = () => { admSkip = 0; loadAdmin(); };
$("fltStatus").onchange = () => { admSkip = 0; loadAdmin(); };
$("fltElig").onchange = () => { admSkip = 0; loadAdmin(); };
$("fltSearch").oninput = () => { admSkip = 0; loadAdmin(); };
$("adminPrev").onclick = () => { admSkip = Math.max(0, admSkip - admLimit); loadAdmin(); };
$("adminNext").onclick = () => { admSkip += admLimit; loadAdmin(); };
async function loadAdmin() {
  const box = $("adminList");
  box.innerHTML = "<div class='skel'></div><div class='skel'></div><div class='skel'></div>";
  const stats = await api("/admin/stats");
  if (stats.ok) {
    const s = stats.json;
    $("adminStats").innerHTML =
      `<div class="stat"><b>${s.incidents_total}</b><span>ДТП всего</span></div>`
      + `<div class="stat"><b>${s.reviews_pending}</b><span>на проверке</span></div>`
      + `<div class="stat"><b>${s.users_total}</b><span>пользователи</span></div>`
      + `<div class="stat"><b>${s.evidence_total}</b><span>фото</span></div>`
      + `<div class="stat"><b>${(s.by_eligibility && s.by_eligibility.red) || 0}</b><span>красные</span></div>`
      + `<div class="stat"><b>${s.mongo_enabled ? "вкл" : "выкл"}</b><span>MongoDB</span></div>`;
  }
  const f = admFilters();
  let path = `/admin/incidents?skip=${admSkip}&limit=${admLimit}`;
  if (f.status) path += "&status=" + encodeURIComponent(f.status);
  if (f.eligibility) path += "&eligibility=" + encodeURIComponent(f.eligibility);
  const res = await api(path);
  if (!res.ok) {
    box.innerHTML = res.status === 403
      ? "<p class='hint'>Нет доступа: войдите специалистом во вкладке Гараж.</p>"
      : "<p class='hint'>Ошибка сети. Проверьте, запущен ли backend, и повторите.</p>";
    $("adminCount").textContent = "";
    return;
  }
  let items = res.json.items || [];
  const total = res.json.total || 0;
  if (f.q) items = items.filter((x) => String(x.code || "").toLowerCase().includes(f.q)
    || String(x.id).includes(f.q));
  const order = {red: 0, yellow: 1, green: 2};
  items.sort((a, b) => (order[a.eligibility] ?? 3) - (order[b.eligibility] ?? 3));
  $("adminCount").textContent = total ? `Показано ${admSkip + 1}–${admSkip + items.length} из ${total}` : "Случаев пока нет";
  $("adminPrev").disabled = admSkip === 0;
  $("adminNext").disabled = admSkip + items.length >= total;
  box.innerHTML = items.map((x) =>
    `<button class="arow" data-id="${x.id}"><span class="badge ${esc(x.eligibility || "unknown")}">${esc(x.eligibility || "?")}</span>`
    + `#${x.id} · ${esc(x.code)} · ${esc(x.status)}${x.has_injury ? " · <b>ПОСТРАДАВШИЕ</b>" : ""}<br/>`
    + `<small>${esc(x.reason || "")}</small></button>`).join("") || "<p class='hint'>Случаев пока нет</p>";
  box.querySelectorAll(".arow").forEach((b) => b.addEventListener("click", () => adminDetail(b.dataset.id)));
}
/* Фото через Authorization-заголовок (токен не светится в URL), fallback — ?token= */
async function photoURL(base, url) {
  try {
    const r = await fetch(base + url, {headers: {Authorization: "Bearer " + TOKEN}});
    if (!r.ok) throw new Error("http " + r.status);
    return URL.createObjectURL(await r.blob());
  } catch { return base + url + "?token=" + encodeURIComponent(TOKEN); }
}
async function adminDetail(id) {
  const box = $("adminDetail");
  box.style.display = "block";
  box.innerHTML = "<p class='hint'>Загрузка досье…</p>";
  box.scrollIntoView({block: "nearest"});
  const res = await api("/admin/incidents/" + id);
  if (!res.ok || !res.json || !res.json.incident) {
    box.innerHTML = "<p class='hint'>Не удалось загрузить досье. Повторите.</p>";
    return;
  }
  const d = res.json;
  const base = API.replace("/api/v1", "");
  const ev = await Promise.all((d.evidence || []).map(async (e) => {
    const src = await photoURL(base, e.url);
    return `<a href="${esc(src)}" target="_blank" rel="noopener" title="${esc(e.kind)}">`
      + `<img src="${esc(src)}" alt="${esc(e.kind)}" loading="lazy"/></a>`;
  }));
  const t = d.triage || {};
  const inj = t.injured_count > 0 ? `<b style="color:#f5a524">пострадавших: ${t.injured_count}</b>` : "пострадавших нет";
  box.innerHTML = `<h3>Случай #${d.incident.id} · ${esc(d.incident.code)}</h3>`
    + `<p><span class="badge ${esc(d.incident.eligibility || "")}">${esc(d.incident.eligibility || "?")}</span> ${esc(d.incident.status)}</p>`
    + `<p><b>Данные водителя:</b> ${inj}`
    + (t.impact_part ? ` · удар: <b>${esc(t.impact_part)}</b>` : "")
    + ` · пешеход=${!!t.has_pedestrian} · вина=${!!t.responsibility_accepted} · доки=${!!t.docs_valid} · трезв=${!!t.sober} · согласие=${!!t.damage_agreed}</p>`
    + (t.driver_comment ? `<p><b>Комментарий:</b> ${esc(t.driver_comment)}</p>` : "")
    + `<p><b>Участники:</b> ${esc((d.participants || []).map((p) => p.side + ":" + p.user + (p.confirmed ? " ✓" : " …")).join(", "))}</p>`
    + `<h3>Фото водителя</h3><div class="thumbs">${ev.join("") || "<span class='hint'>нет фото</span>"}</div>`
    + (d.ai ? `<h3>Схема ИИ <small>(${esc(d.ai.source)})</small></h3><div class="ai-svg">${d.ai.svg}</div>`
      + `<p class="ai-desc">${esc(d.ai.description || "")}</p>`
      + `<p><b>Пострадавшие (из triage, ИИ не выдумывает):</b> ${esc(d.ai.casualties_note)}</p>`
      + `<p class="hint">⚠️ Разбор ИИ — черновик, не юридический факт.</p>`
      + `<ul class="ai-actions">${(d.ai.actions || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul>`
      : "<p class='hint'>ИИ-анализ ещё не запускался</p>")
    + `<p><b>Вердикт:</b> ${esc((d.review && d.review.verdict) || "pending")}`
    + (d.review && d.review.comment ? ` · ${esc(d.review.comment)}` : "") + `</p>`
    + `<h3>Переписка</h3><div>${(d.messages || []).map((m) =>
      `<div class="msg"><small>${esc(m.from_role)} · ${esc(m.at)}</small><br/>${esc(m.text)}</div>`).join("") || "<span class='hint'>пусто</span>"}</div>`
    + `<div class="frow"><input id="admMsg" placeholder="Текст пользователю..." maxlength="1000"/>`
    + `<button class="ghost" id="admSend">Отправить</button></div>`
    + `<div class="frow" style="margin-top:8px"><input id="admComment" placeholder="Комментарий к вердикту (обязателен для отклонения)..." maxlength="500"/></div>`
    + `<div class="frow verdict-row">`
    + `<button class="primary" data-v="approved">✅ Регистрация завершена</button>`
    + `<button class="primary alt" data-v="needs_field">🚓 Выезжаем для проверки</button>`
    + `<button class="ghost small" data-v="rejected">Отклонить</button></div>`;
  $("admSend").onclick = async (e) => {
    const v = $("admMsg").value.trim();
    if (!v) { toast("Пустое сообщение"); return; }
    busy(e.currentTarget, true);
    const r = await api("/admin/incidents/" + id + "/message",
      {method: "POST", body: JSON.stringify({text: v})});
    busy(e.currentTarget, false);
    if (!r.ok) { toast("Не отправлено: " + r.error); return; }
    adminDetail(id);
  };
  box.querySelectorAll("[data-v]").forEach((b) => b.addEventListener("click", async () => {
    if (!d.review) { toast("Ревью-кейс не создан (случай green без замечаний)."); return; }
    const v = b.dataset.v;
    const comment = $("admComment").value.trim();
    if (v === "rejected" && !comment) { toast("Для отклонения нужен комментарий"); return; }
    busy(b, true);
    const rr = await api("/reviews/" + d.review.id,
      {method: "POST", body: JSON.stringify({verdict: v, comment: comment || "из панели"})});
    busy(b, false);
    toast("Вердикт: " + (rr.ok ? rr.json.verdict : rr.error));
    adminDetail(id);
  }));
}

$("btnVehicle").onclick = async (e) => {
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/vehicles", {method: "POST",
    body: JSON.stringify({plate: $("gPlate").value.trim(), make: $("gMake").value.trim() || "Chevrolet",
      model: $("gModel").value.trim() || "Cobalt", year: 2020})});
  busy(btn, false);
  $("vehOut").textContent = JSON.stringify(res.json, null, 2);
  if (!res.ok) toast("Не сохранено: " + res.error);
};

/* Переписка: сотрудник пишет — водитель видит; водитель жмёт кнопку — сотрудник видит */
async function loadMsgs() {
  if (!INC || !TOKEN) return;
  const res = await api("/incidents/" + INC.id + "/messages");
  if (!res.ok || !Array.isArray(res.json)) return;
  const j = res.json;
  $("msgList").innerHTML = j.length ? j.map((m) =>
    `<div class="msg${m.role === "driver" ? "" : " mine"}"><small>${esc(m.from)} · ${esc(m.at)}</small><br/>${esc(m.text)}</div>`
  ).join("") : "<p class='hint'>Пока тихо. Ответ появится здесь.</p>";
}
async function sendQuick(text) {
  if (!INC) return;
  await api("/incidents/" + INC.id + "/messages", {method: "POST", body: JSON.stringify({text})});
  loadMsgs();
}
$("btnAck").onclick = () => sendQuick("Понял, жду");
$("btnHelp").onclick = () => sendQuick("Нужна помощь!");
setInterval(() => {
  if (!document.hidden && INC && $("scr-case").classList.contains("active")) loadMsgs();
}, 8000);
