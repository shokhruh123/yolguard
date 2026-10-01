/* Yo'l Guard mobile client. Same /api/v1 backend. */
let API = localStorage.getItem("yg_api") || "http://127.0.0.1:8001/api/v1";
let TOKEN = localStorage.getItem("yg_token") || "";
let INC = JSON.parse(localStorage.getItem("yg_inc") || "null");
const $ = (id) => document.getElementById(id);
const hdr = () => ({"Content-Type": "application/json", Authorization: "Bearer " + TOKEN});
const KINDS = ["scene_overview", "both_vehicles", "plate_a", "plate_b", "road_marking", "damage_close"];
let HAVE = [];

/* tabs */
document.querySelectorAll(".tab").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".screen").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    $(b.dataset.s).classList.add("active");
  })
);
function go(id) {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x.dataset.s === id));
  document.querySelectorAll(".screen").forEach((x) => x.classList.toggle("active", x.id === id));
}

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
  ping(); alert("API: " + API);
};
async function ping() {
  try {
    const r = await fetch(API.replace("/api/v1", "") + "/health");
    $("netDot").classList.toggle("on", r.ok);
  } catch { $("netDot").classList.remove("on"); }
}
setInterval(ping, 5000); ping();

function paint() {
  $("stCode").textContent = INC ? INC.code : "—";
  $("stStatus").textContent = INC ? INC.status : "—";
  $("stComp").textContent = HAVE.length + "/6";
  $("evBar").style.width = (HAVE.length / 6) * 100 + "%";
  $("evHint").textContent = HAVE.length === 6 ? "Комплект полный" : "Осталось: " + KINDS.filter((k) => !HAVE.includes(k)).join(", ");
  $("evChips").innerHTML = KINDS.map((k) => `<span class="chip${HAVE.includes(k) ? " done" : ""}">${k}</span>`).join("");
}
paint();
if (INC) { $("stCode").textContent = INC.code; $("stStatus").textContent = INC.status; }

$("btnLogin").onclick = async () => {
  const r = await fetch(API + "/auth/login", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({phone: $("gPhone").value, password: $("gPw").value})});
  const j = await r.json();
  if (j.access) { TOKEN = j.access; localStorage.setItem("yg_token", TOKEN); alert("Вход выполнен"); go("scr-home"); }
  else alert("Ошибка входа: " + JSON.stringify(j));
};

$("btnSos").onclick = async () => {
  if (!TOKEN) { alert("Сначала войдите во вкладке Гараж"); go("scr-garage"); return; }
  const r = await fetch(API + "/incidents", {method: "POST", headers: hdr(), body: "{}"});
  const j = await r.json();
  INC = j; localStorage.setItem("yg_inc", JSON.stringify(j));
  HAVE = []; paint(); go("scr-case"); showW(1);
};

$("btnTriage").onclick = async () => {
  const body = {has_injury: $("cInj").checked, has_pedestrian: $("cPed").checked,
    responsibility_accepted: $("cResp").checked, docs_valid: $("cDocs").checked,
    sober: $("cSober").checked, damage_agreed: $("cAgreed").checked,
    vehicle_count: 2, third_party_damage: false,
    injured_count: Math.max(0, parseInt($("cInjCount").value || "0", 10)),
    impact_part: $("cImpact").value || "", driver_comment: $("cComment").value.trim()};
  const r = await fetch(API + "/incidents/" + INC.id + "/triage", {method: "POST", headers: hdr(), body: JSON.stringify(body)});
  const j = await r.json();
  const box = $("triageOut");
  box.className = "verdict " + (j.eligibility === "green" ? "green" : j.eligibility === "red" ? "red" : "");
  box.textContent = j.eligibility + ": " + j.reason;
  INC.status = j.status; paint();
  if (j.eligibility === "red") alert("Красный сценарий: следуйте официальному процессу (102).");
  else showW(2);
};

$("btnEv").onclick = async () => {
  const kind = $("evKind").value;
  const r = await fetch(API + "/incidents/" + INC.id + "/evidence", {method: "POST", headers: hdr(),
    body: JSON.stringify({kind, file_path: kind + "_" + Date.now() + ".jpg"})});
  const j = await r.json();
  HAVE = [...new Set([...HAVE, kind])]; paint();
  if (j.completeness && j.completeness.percent === 100) showW(3);
};

$("btnDiagram").onclick = async () => {
  const r = await fetch(API + "/incidents/" + INC.id + "/diagram", {method: "POST", headers: hdr(), body: "{}"});
  const j = await r.json();
  $("svgBox").innerHTML = j.svg || "";
};

$("btnConfirm").onclick = async () => {
  await fetch(API + "/incidents/" + INC.id + "/confirm", {method: "POST", headers: hdr()});
  alert("Подтверждено. Второй водитель подтверждает со своего телефона.");
};

/* Камера: реальное фото -> evidence-upload */
$("camInput").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  if (!f || !INC) return;
  $("thumbs").innerHTML += `<img src="${URL.createObjectURL(f)}"/>`;
  const fd = new FormData();
  fd.append("kind", $("evKind").value);
  fd.append("file", f, f.name || "photo.jpg");
  const r = await fetch(API + "/incidents/" + INC.id + "/evidence-upload", {
    method: "POST", headers: {Authorization: "Bearer " + TOKEN}, body: fd});
  const j = await r.json();
  if (j.saved) {
    HAVE = [...new Set([...HAVE, $("evKind").value])]; paint();
    if (j.completeness && j.completeness.percent === 100) showW(3);
  } else alert("Ошибка загрузки: " + JSON.stringify(j));
  e.target.value = "";
});

/* ИИ — главный: анализирует сам, без кнопки. Показывает схему + текст + фото-ответ */
let aiLoadedFor = 0;
async function loadAI() {
  if (!INC || aiLoadedFor === INC.id) return;
  aiLoadedFor = INC.id;
  $("aiBox").textContent = "ИИ анализирует фото...";
  try {
    const r = await fetch(API + "/incidents/" + INC.id + "/ai-analysis", {method: "POST", headers: hdr()});
    const j = await r.json();
    $("aiBox").innerHTML = j.svg || "";
    const t = $("aiText");
    t.style.display = "block";
    t.innerHTML = `<b>ИИ (${j.source})</b><br/>${j.description}<br/><br/><b>Пострадавшие:</b> ${j.casualties_note}`
      + `<br/><b>Что делать:</b><ul class="ai-actions">${(j.actions || []).map((a) => `<li>${a}</li>`).join("")}</ul>`;
  } catch { $("aiBox").textContent = "ИИ недоступен, попробуйте позже"; aiLoadedFor = 0; }
}

$("btnClaim").onclick = async () => {
  const r = await fetch(API + "/incidents/" + INC.id + "/claim-package", {method: "POST", headers: hdr()});
  const j = await r.json();
  $("claimOut").textContent = JSON.stringify(j, null, 2);
  if (j.detail && String(j.detail).includes("Forbidden"))
    alert("Пакет собирает сотрудник. Нажмите «Войти специалистом» (+998900000002 / spec1234).");
};

/* Быстрый вход специалистом для шага 4 */
$("btnSpecLogin").onclick = async () => {
  const r = await fetch(API + "/auth/login", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({phone: "+998900000002", password: "spec1234"})});
  const j = await r.json();
  if (j.access) { TOKEN = j.access; localStorage.setItem("yg_token", TOKEN); alert("Вы вошли как специалист. Жмите «Пакет для страховой»."); }
  else alert("Ошибка: " + JSON.stringify(j));
};

/* Админ-панель сотрудника */
$("btnAdminReload").onclick = loadAdmin;
async function loadAdmin() {
  $("adminList").innerHTML = "<p class='hint'>Загрузка…</p>";
  let j;
  try {
    const r = await fetch(API + "/admin/incidents", {headers: hdr()});
    j = await r.json();
  } catch (e) {
    $("adminList").innerHTML = "<p class='hint'>Ошибка сети. Проверьте, запущен ли backend, и повторите.</p>";
    return;
  }
  if (!Array.isArray(j)) { $("adminList").innerHTML = "Нет доступа: войдите специалистом в Гараже."; return; }
  const order = {red: 0, yellow: 1, green: 2};
  j.sort((a, b) => (order[a.eligibility] ?? 3) - (order[b.eligibility] ?? 3));
  $("adminList").innerHTML = j.map((x) =>
    `<button class="arow" data-id="${x.id}"><span class="badge ${x.eligibility}">${x.eligibility}</span>`
    + `#${x.id} · ${x.code} · ${x.status}${x.has_injury ? " · <b>ПОСТРАДАВШИЕ</b>" : ""}<br/>`
    + `<small>${x.reason || ""}</small></button>`).join("") || "<p class='hint'>Случаев пока нет</p>";
  document.querySelectorAll(".arow").forEach((b) => b.addEventListener("click", () => adminDetail(b.dataset.id)));
}
async function adminDetail(id) {
  const box = $("adminDetail");
  box.style.display = "block";
  box.innerHTML = "<p class='hint'>Загрузка досье…</p>";
  let d;
  try {
    const r = await fetch(API + "/admin/incidents/" + id, {headers: hdr()});
    d = await r.json();
    if (!d || !d.incident) throw new Error("bad");
  } catch (e) {
    box.innerHTML = "<p class='hint'>Не удалось загрузить досье. Повторите.</p>";
    return;
  }
  const base = API.replace("/api/v1", "");
  const ev = (d.evidence || []).map((e) =>
    `<a href="${base}${e.url}?token=${TOKEN}" target="_blank" title="${e.kind}">`
    + `<img src="${base}${e.url}?token=${TOKEN}" alt="${e.kind}" loading="lazy"/></a>`).join("");
  const t = d.triage || {};
  const inj = t.injured_count > 0 ? `<b style="color:#f5a524">пострадавших: ${t.injured_count}</b>` : "пострадавших нет";
  box.innerHTML = `<h3>Случай #${d.incident.id} · ${d.incident.code}</h3>`
    + `<p><span class="badge ${d.incident.eligibility}">${d.incident.eligibility}</span> ${d.incident.status}</p>`
    + `<p><b>Данные водителя:</b> ${inj}`
    + (t.impact_part ? ` · удар: <b>${t.impact_part}</b>` : "")
    + ` · пешеход=${t.has_pedestrian} · вина=${t.responsibility_accepted} · доки=${t.docs_valid} · трезв=${t.sober} · согласие=${t.damage_agreed}</p>`
    + (t.driver_comment ? `<p><b>Комментарий:</b> ${t.driver_comment}</p>` : "")
    + `<p><b>Участники:</b> ${(d.participants || []).map((p) => p.side + ":" + p.user + (p.confirmed ? " ✓" : " …")).join(", ")}</p>`
    + `<h3>Фото водителя</h3><div class="thumbs">${ev || "<span class='hint'>нет фото</span>"}</div>`
    + (d.ai ? `<h3>Схема ИИ <small>(${d.ai.source})</small></h3><div class="ai-svg">${d.ai.svg}</div>`
      + `<p class="ai-desc">${(d.ai.description || "").replace(/\n/g, "<br/>")}</p>`
      + `<p><b>Пострадавшие (из triage, ИИ не выдумывает):</b> ${d.ai.casualties_note}</p>`
      + `<p class="hint">⚠️ Разбор ИИ — черновик, не юридический факт.</p>`
      + `<ul class="ai-actions">${d.ai.actions.map((a) => `<li>${a}</li>`).join("")}</ul>` : "<p class='hint'>ИИ-анализ ещё не запускался</p>")
    + `<p><b>Вердикт:</b> ${(d.review && d.review.verdict) || "pending"}</p>`
    + `<h3>Переписка</h3><div>${(d.messages || []).map((m) =>
      `<div class="msg"><small>${m.from_role} · ${m.at}</small><br/>${m.text}</div>`).join("") || "<span class='hint'>пусто</span>"}</div>`
    + `<div class="frow"><input id="admMsg" placeholder="Текст пользователю..."/>`
    + `<button class="ghost" id="admSend">Отправить</button></div>`
    + `<div class="frow verdict-row">`
    + `<button class="primary" data-v="approved">✅ Регистрация завершена</button>`
    + `<button class="primary alt" data-v="needs_field">🚓 Выезжаем для проверки</button>`
    + `<button class="ghost small" data-v="rejected">Отклонить</button></div>`;
  $("admSend").onclick = async () => {
    const t = $("admMsg").value.trim();
    if (!t) return;
    await fetch(API + "/admin/incidents/" + id + "/message", {method: "POST", headers: hdr(),
      body: JSON.stringify({text: t})});
    adminDetail(id);
  };
  box.querySelectorAll("[data-v]").forEach((b) => b.addEventListener("click", async () => {
    if (!d.review) { alert("Ревью-кейс не создан (случай green без замечаний)."); return; }
    const rr = await fetch(API + "/reviews/" + d.review.id, {method: "POST", headers: hdr(),
      body: JSON.stringify({verdict: b.dataset.v, comment: "из панели"})});
    const jj = await rr.json();
    alert("Вердикт: " + (jj.verdict || JSON.stringify(jj)));
    adminDetail(id);
  }));
  box.scrollIntoView();
}

$("btnVehicle").onclick = async () => {
  const r = await fetch(API + "/vehicles", {method: "POST", headers: hdr(),
    body: JSON.stringify({plate: $("gPlate").value, make: $("gMake").value || "Chevrolet", model: $("gModel").value || "Cobalt", year: 2020})});
  $("vehOut").textContent = JSON.stringify(await r.json(), null, 2);
};

/* Переписка: сотрудник пишет — водитель видит; водитель жмёт кнопку — сотрудник видит */
async function loadMsgs() {
  if (!INC || !TOKEN) return;
  try {
    const r = await fetch(API + "/incidents/" + INC.id + "/messages", {headers: hdr()});
    const j = await r.json();
    if (!Array.isArray(j)) return;
    $("msgList").innerHTML = j.length ? j.map((m) =>
      `<div class="msg${m.role === "driver" ? "" : " mine"}"><small>${m.from} · ${m.at}</small><br/>${m.text}</div>`
    ).join("") : "<p class='hint'>Пока тихо. Ответ появится здесь.</p>";
  } catch {}
}
async function sendQuick(text) {
  if (!INC) return;
  await fetch(API + "/incidents/" + INC.id + "/messages", {method: "POST", headers: hdr(),
    body: JSON.stringify({text})});
  loadMsgs();
}
$("btnAck").onclick = () => sendQuick("Понял, жду");
$("btnHelp").onclick = () => sendQuick("Нужна помощь!");
setInterval(() => { if (INC && $("scr-case").classList.contains("active")) loadMsgs(); }, 6000);
