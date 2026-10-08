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
function TT(k) { return (typeof T === "function") ? T(k) : k; }
function TTArr(k) { const v = TT(k); return Array.isArray(v) ? v : null; }
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
    return {ok: false, status: 0, json: null, error: TT("t_offline")};
  }
}
function busy(btn, on) {
  if (!btn) return;
  btn.disabled = !!on;
  btn.classList.toggle("busy", !!on);
}
function needInc() {
  if (!INC) { toast(TT("t_no_inc")); go("scr-home"); return false; }
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
  const steps = TTArr("w_steps");
  $("wTitle").textContent = (steps && steps[WP - 1]) || ["Проверка eligibility", "Фотофиксация", "Ответ ИИ", "Ответ сотрудника"][WP - 1];
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
    dot.setAttribute("aria-label", r.ok ? TT("t_online") : TT("t_offline"));
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
  const chipName = (k) => {
    const arr = TTArr("kinds");
    return (arr && arr[KINDS.indexOf(k)]) || k;
  };
  $("evHint").textContent = HAVE.length >= 6 ? TT("ev_hint_full")
    : TT("ev_left") + KINDS.filter((k) => !HAVE.includes(k)).map(chipName).join(", ");
  $("evChips").innerHTML = KINDS.map((k) =>
    `<span class="chip${HAVE.includes(k) ? " done" : ""}">${esc(chipName(k))}</span>`).join("");
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
    toast(TT("t_login_ok")); go("scr-home");
  } else toast(TT("t_login_err") + (res.error || ""));
};

$("btnSos").onclick = async (e) => {
  if (!TOKEN) { toast(TT("t_login_first")); go("scr-garage"); return; }
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents", {method: "POST", body: "{}"});
  busy(btn, false);
  if (!res.ok) { toast(TT("t_case_err") + res.error); return; }
  INC = res.json; localStorage.setItem("yg_inc", JSON.stringify(INC));
  HAVE = []; saveHave(); paint(); go("scr-case"); showW(1);
};

/* Второй участник подключается по коду сессии с главного экрана */
$("btnJoin").onclick = async (e) => {
  if (!TOKEN) { toast(TT("t_login_first")); go("scr-garage"); return; }
  const iid = parseInt(($("joinId").value || "").trim(), 10);
  const code = ($("joinCode").value || "").trim().toUpperCase();
  if (!iid || !code) { toast(TT("t_join_need")); return; }
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents/" + iid + "/join?code=" + encodeURIComponent(code), {method: "POST"});
  busy(btn, false);
  if (!res.ok) { toast(TT("t_join_err") + res.error); return; }
  INC = {id: iid, code: code, status: "evidence"};
  localStorage.setItem("yg_inc", JSON.stringify(INC));
  HAVE = []; saveHave(); paint();
  toast(TT("t_joined"));
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
  if (!res.ok) { toast(TT("t_triage_err") + res.error); return; }
  const j = res.json;
  const box = $("triageOut");
  box.className = "verdict " + (j.eligibility === "green" ? "green" : j.eligibility === "red" ? "red" : "yellow");
  box.textContent = j.eligibility + ": " + j.reason;
  INC.status = j.status;
  localStorage.setItem("yg_inc", JSON.stringify(INC)); paint();
  if (j.eligibility === "red") toast(TT("t_red"));
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
  if (!res.ok) { toast(TT("t_evl_err") + res.error); return; }
  HAVE = [...new Set([...HAVE, kind])]; saveHave(); paint();
  if (res.json.completeness && res.json.completeness.percent === 100) showW(3);
};

$("btnDiagram").onclick = async (e) => {
  if (!needInc()) return;
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents/" + INC.id + "/diagram", {method: "POST", body: "{}"});
  busy(btn, false);
  if (!res.ok) { toast(TT("t_dia_err") + res.error); return; }
  $("svgBox").innerHTML = res.json.svg || "";
};

$("btnConfirm").onclick = async (e) => {
  if (!needInc()) return;
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/incidents/" + INC.id + "/confirm", {method: "POST"});
  busy(btn, false);
  toast(res.ok ? TT("t_confirmed") : TT("t_conf_err") + res.error);};

/* Камера: реальное фото -> evidence-upload (с проверкой качества, очередь при офлайне) */
$("camInput").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  e.target.value = "";
  if (!f || !needInc()) return;
  const kind = $("evKind").value;
  const st = await photoStats(f);
  if (st.dark || st.blurry) {
    toast(st.dark && st.blurry ? TT("t_dark_blur") : st.dark ? TT("t_dark") : TT("t_blur"));
  }
  if (st.hash && await isDuplicate(st.hash)) toast(TT("t_dupe"));
  const knames = TT("kinds");
  const kindName = (knames && knames[$("evKind").selectedIndex]) || KIND_RU[kind] || kind;
  const url = URL.createObjectURL(f);
  const img = document.createElement("img");
  img.alt = kindName;
  img.onload = () => URL.revokeObjectURL(url);
  img.src = url;
  $("thumbs").appendChild(img);
  const fd = new FormData();
  fd.append("kind", kind);
  fd.append("file", f, f.name || "photo.jpg");
  toast(TT("t_uploading")+"");
  let res;
  try {
    const r = await fetch(API + "/incidents/" + INC.id + "/evidence-upload", {
      method: "POST", headers: {Authorization: "Bearer " + TOKEN}, body: fd});
    res = {ok: r.ok, json: await r.json().catch(() => null)};
    if (!r.ok) res.error = (res.json && res.json.detail) || ("HTTP " + r.status);
  } catch { res = {ok: false, error: "offline"}; }
  if (res.ok && res.json && res.json.saved) {
    HAVE = [...new Set([...HAVE, kind])]; saveHave(); paint();
    if (st.hash) rememberHash(st.hash);
    toast(TT("t_saved"));
    if (res.json.completeness && res.json.completeness.percent === 100) showW(3);
  } else if (res.error === "offline") {
    await queueUpload(INC.id, kind, f, f.name || "photo.jpg");
  } else toast(TT("t_upl_err") + (res.error || ""));
});

/* ИИ — главный: анализирует сам, без кнопки. Показывает схему + текст + фото-ответ */
let aiLoadedFor = 0;
async function loadAI() {
  if (!INC || aiLoadedFor === INC.id) return;
  aiLoadedFor = INC.id;
  $("aiBox").textContent = TT("ai_loading");
  $("aiRetry").style.display = "none";
  const res = await api("/incidents/" + INC.id + "/ai-analysis", {method: "POST"});
  if (!res.ok) {
    $("aiBox").textContent = TT("ai_down");
    $("aiRetry").style.display = "";
    aiLoadedFor = 0;
    return;
  }
  const j = res.json;
  $("aiBox").innerHTML = j.svg || "";
  const sevMap = TTArr("severities") ? TT("severities") : null;
  const sevRu = (sevMap && sevMap[j.damage_severity]) || "";
  const plates = j.plates || {};
  const plateLine = (plates.a || plates.b)
    ? `<br/><b>${esc(TT("ai_plates"))}</b> A: ${esc(plates.a || "—")} · B: ${esc(plates.b || "—")}` : "";
  const t = $("aiText");
  t.style.display = "block";
  t.innerHTML = `<b>${esc(TT("ai_src"))} (${esc(j.source)})</b><br/>${esc(j.description).replace(/\n/g, "<br/>")}`
    + `<br/><br/><b>${esc(TT("ai_cas"))}</b> ${esc(j.casualties_note)}${plateLine}`
    + `<br/><b>${esc(TT("ai_sev"))}</b> ${esc(sevRu)}`
    + `<br/><b>${esc(TT("d_todo"))}</b><ul class="ai-actions">`
    + `${(j.actions || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul>`;
}
$("aiRetry").onclick = () => { aiLoadedFor = 0; loadAI(); };

$("btnVehicle").onclick = async (e) => {
  const btn = e.currentTarget; busy(btn, true);
  const res = await api("/vehicles", {method: "POST",
    body: JSON.stringify({plate: $("gPlate").value.trim(), make: $("gMake").value.trim() || "Chevrolet",
      model: $("gModel").value.trim() || "Cobalt", year: 2020})});
  busy(btn, false);
  $("vehOut").textContent = JSON.stringify(res.json, null, 2);
  if (!res.ok) toast(TT("t_no_vehicle") + res.error);
};

/* Переписка: сотрудник пишет — водитель видит; водитель жмёт кнопку — сотрудник видит */
async function loadMsgs() {
  if (!INC || !TOKEN) return;
  const res = await api("/incidents/" + INC.id + "/messages");
  if (!res.ok || !Array.isArray(res.json)) return;
  const j = res.json;
  $("msgList").innerHTML = j.length ? j.map((m) =>
    `<div class="msg${m.role === "driver" ? "" : " mine"}"><small>${esc(m.from)} · ${esc(m.at)}</small><br/>${esc(m.text)}</div>`
  ).join("") : "<p class='hint'>" + esc(TT("w4_empty")) + "</p>";
}
async function sendQuick(text) {
  if (!INC) return;
  const r = await api("/incidents/" + INC.id + "/messages",
    {method: "POST", body: JSON.stringify({text})});
  if (!r.ok && r.status === 0) await queueMsg(INC.id, text);
  loadMsgs();
}
$("btnAck").onclick = () => sendQuick("Понял, жду");
$("btnHelp").onclick = () => sendQuick("Нужна помощь!");
setInterval(() => {
  if (!document.hidden && INC && $("scr-case").classList.contains("active")) loadMsgs();
}, 8000);

/* ================= PWA + офлайн-очередь ================= */
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
const idb = new Promise((resolve) => {
  if (!("indexedDB" in window)) { resolve(null); return; }
  const rq = indexedDB.open("yg-db", 1);
  rq.onupgradeneeded = () => {
    rq.result.createObjectStore("pending_uploads", {keyPath: "id", autoIncrement: true});
    rq.result.createObjectStore("pending_msgs", {keyPath: "id", autoIncrement: true});
  };
  rq.onsuccess = () => resolve(rq.result);
  rq.onerror = () => resolve(null);
});
function idbAll(store) {
  return idb.then((db) => new Promise((res) => {
    if (!db) { res([]); return; }
    const tx = db.transaction(store, "readonly");
    const q = tx.objectStore(store).getAll();
    q.onsuccess = () => res(q.result || []);
    q.onerror = () => res([]);
  }));
}
function idbPut(store, val) {
  return idb.then((db) => new Promise((res) => {
    if (!db) { res(false); return; }
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(val);
    tx.oncomplete = () => res(true);
    tx.onerror = () => res(false);
  }));
}
function idbDel(store, id) {
  return idb.then((db) => new Promise((res) => {
    if (!db) { res(false); return; }
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).delete(id);
    tx.oncomplete = () => res(true);
    tx.onerror = () => res(false);
  }));
}
async function queueUpload(iid, kind, blob, name) {
  await idbPut("pending_uploads", {iid, kind, name, mime: blob.type, blob});
  toast(TT("t_offline_q"));
  updatePending();
}
async function queueMsg(iid, text) {
  await idbPut("pending_msgs", {iid, text, at: Date.now()});
  toast(TT("t_msg_q"));
}
async function flushQueue() {
  if (!TOKEN) return;
  const ups = await idbAll("pending_uploads");
  for (const p of ups) {
    if (!p.blob) { await idbDel("pending_uploads", p.id); continue; }
    const fd = new FormData();
    fd.append("kind", p.kind);
    fd.append("file", p.blob, p.name || "file");
    try {
      const iid = p.iid;
      const r = await fetch(API + "/incidents/" + iid + "/evidence-upload", {
        method: "POST", headers: {Authorization: "Bearer " + TOKEN}, body: fd});
      if (r.ok) {
        await idbDel("pending_uploads", p.id);
        const j = await r.json().catch(() => null);
        const k = (j && j.saved) ? p.kind : null;
        if (k && INC && INC.id === iid) {
          HAVE = [...new Set([...HAVE, k])]; saveHave(); paint();
        }
      }
    } catch {}
  }
  const msgs = await idbAll("pending_msgs");
  for (const m of msgs) {
    const r = await api("/incidents/" + m.iid + "/messages",
      {method: "POST", body: JSON.stringify({text: m.text})});
    if (r.ok) await idbDel("pending_msgs", m.id);
  }
  updatePending();
  if (ups.length || msgs.length) { loadMsgs(); toast(TT("t_q_sent")); }
}
async function updatePending() {
  const ups = await idbAll("pending_uploads");
  const el = $("evQueue");
  if (el) el.textContent = ups.length ? `В очереди на отправку: ${ups.length}` : "";
}
window.addEventListener("online", flushQueue);
setTimeout(flushQueue, 3000);

/* ================= качество фото + дубликаты ================= */
async function photoStats(file) {
  try {
    const bmp = await createImageBitmap(file);
    const S = 48, c = document.createElement("canvas");
    c.width = S; c.height = S;
    const ctx = c.getContext("2d", {willReadFrequently: true});
    ctx.drawImage(bmp, 0, 0, S, S);
    if (bmp.close) bmp.close();
    const px = ctx.getImageData(0, 0, S, S).data;
    const g = [];
    let sum = 0;
    for (let i = 0; i < px.length; i += 4) {
      const v = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];
      g.push(v); sum += v;
    }
    const mean = sum / g.length;
    let lap = 0;
    const at = (x, y) => g[y * S + x];
    let n = 0, m2 = 0;
    for (let y = 1; y < S - 1; y++) for (let x = 1; x < S - 1; x++) {
      const l = -4 * at(x, y) + at(x - 1, y) + at(x + 1, y) + at(x, y - 1) + at(x, y + 1);
      n++; const d = l - (m2 / Math.max(1, n));
      m2 += d * d; lap = m2 / n;
    }
    // dHash 8x8
    let hash = "";
    for (let y = 0; y < 8; y++) {
      let byte = 0;
      for (let x = 0; x < 8; x++) byte = (byte << 1) | (at(x * 6, y * 6) > mean ? 1 : 0);
      hash += byte.toString(16).padStart(2, "0");
    }
    return {dark: mean < 45, blurry: lap < 60, hash};
  } catch { return {dark: false, blurry: false, hash: null}; }
}
function hashDist(a, b) {
  let d = 0;
  for (let i = 0; i < Math.min(a.length, b.length); i += 2) {
    let x = parseInt(a.substr(i, 2), 16) ^ parseInt(b.substr(i, 2), 16);
    while (x) { d += x & 1; x >>= 1; }
  }
  return d;
}
function knownHashes() {
  try { return JSON.parse(localStorage.getItem("yg_hash_" + (INC && INC.id)) || "[]"); }
  catch { return []; }
}
function rememberHash(h) {
  if (!h || !INC) return;
  const k = "yg_hash_" + INC.id;
  const arr = knownHashes();
  arr.push(h);
  try { localStorage.setItem(k, JSON.stringify(arr.slice(-40))); } catch {}
}
async function isDuplicate(h) {
  if (!h) return false;
  return knownHashes().some((x) => hashDist(x, h) <= 6);
}

/* ================= видео + диктофон ================= */
async function uploadMedia(kind, blob, name) {
  if (!needInc()) return;
  const fd = new FormData();
  fd.append("kind", kind);
  fd.append("file", blob, name);
  toast(kind === "voice_note" ? TT("t_voice_up") : TT("t_video_up"));
  try {
    const r = await fetch(API + "/incidents/" + INC.id + "/evidence-upload", {
      method: "POST", headers: {Authorization: "Bearer " + TOKEN}, body: fd});
    const j = await r.json().catch(() => null);
    if (r.ok && j && j.saved) {
      HAVE = [...new Set([...HAVE, kind])]; saveHave(); paint();
      toast(kind === "voice_note" ? TT("t_voice_ok") : TT("t_video_ok"));
    } else toast(TT("t_upl_err") + ((j && j.detail) || ("HTTP " + r.status)));
  } catch {
    await queueUpload(INC.id, kind, blob, name);
  }
}
if ($("vidInput")) $("vidInput").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  e.target.value = "";
  if (!f || !needInc()) return;
  if (f.size > 50 * 1024 * 1024) { toast(TT("t_big_video")); return; }
  $("thumbs").insertAdjacentHTML("beforeend",
    `<span class="chip">${esc(TT("t_vid_chip"))}: ${esc(f.name || "clip")}</span>`);
  uploadMedia("video_scene", f, f.name || "clip.mp4");
});
let mediaRec = null, recChunks = [];
if ($("btnRec")) $("btnRec").onclick = async () => {
  if (mediaRec && mediaRec.state !== "inactive") { mediaRec.stop(); return; }
  if (!needInc()) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    recChunks = [];
    mediaRec = new MediaRecorder(stream, {mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : ""});
    mediaRec.ondataavailable = (e) => { if (e.data.size) recChunks.push(e.data); };
    mediaRec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      $("btnRec").classList.remove("rec");
      $("btnRec").textContent = TT("rec_btn");
      const blob = new Blob(recChunks, {type: mediaRec.mimeType || "audio/webm"});
      if (blob.size < 1000) { toast(TT("t_voice_short")); return; }
      $("thumbs").insertAdjacentHTML("beforeend", `<span class="chip">${esc(TT("t_voice_chip"))}</span>`);
      uploadMedia("voice_note", blob, "voice_" + Date.now() + ".webm");
    };
    mediaRec.start();
    $("btnRec").classList.add("rec");
    $("btnRec").textContent = TT("rec_stop");
  } catch { toast(TT("t_no_mic")); }
};

/* ================= Web Push ================= */
function b64url(s) {
  const pad = "=".repeat((4 - (s.length % 4)) % 4);
  const b = (s + pad).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}
async function pushState() {
  const el = $("pushState");
  if (!el) return;
  if (!("Notification" in window) || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    el.textContent = "Push не поддерживается этим браузером"; return;
  }
  const reg = await navigator.serviceWorker.ready.catch(() => null);
  const sub = reg ? await reg.pushManager.getSubscription().catch(() => null) : null;
  el.textContent = sub ? "Уведомления включены ✓"
    : (Notification.permission === "denied" ? "Запрещены в браузере" : "Выключены");
}
if ($("btnPush")) $("btnPush").onclick = async (e) => {
  if (!TOKEN) { toast(TT("t_login_first")); return; }
  const btn = e.currentTarget; busy(btn, true);
  try {
    if (Notification.permission === "default") await Notification.requestPermission();
    if (Notification.permission !== "granted") { toast(TT("t_push_browser")); busy(btn, false); return; }
    const reg = await navigator.serviceWorker.ready;
    const vk = await api("/push/vapid-key");
    if (!vk.ok || !vk.json.publicKey) { toast(TT("t_push_server")); busy(btn, false); return; }
    const sub = await reg.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: b64url(vk.json.publicKey)});
    const r = await api("/push/subscribe", {method: "POST", body: JSON.stringify(sub.toJSON())});
    toast(r.ok ? TT("t_push_ok") : TT("t_push_err") + r.error);
  } catch { toast(TT("t_push_no")); }
  busy(btn, false);
  pushState();
};
setTimeout(pushState, 2500);
