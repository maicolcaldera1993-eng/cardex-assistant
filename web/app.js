// Cardex Assistant — operator page. No framework: one WebSocket, a handful of render functions.
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const T = {
  it: {
    tagline: "service di primo ingresso · Sereni Macchine da Caffè",
    startTitle: "Il collega esperto che sta in linea con te.",
    startSub: "Trascrive la chiamata, ti spiega cosa intende il cliente, riconosce macchina e guasto, ti guida nella diagnosi e trova il ricambio.",
    sample: "Riproduci una chiamata di esempio", mic: "Usa il mio microfono (tu sei il cliente)",
    clarify: "Versione chiara", assistant: "Assistente", talk: "Conversazione", diag: "Diagnosi guidata", parts: "Ricambi proposti",
    log: "Registro dell'assistente", swap: "Scambia ruoli", end: "Fine chiamata", operator: "Operatore", customer: "Cliente",
    noDiag: "Nessun sintomo riconosciuto. Quando il cliente descrive un problema, la procedura compare qui.",
    ask: "Chiedi al cliente", do: "Fagli fare", say: "Da leggere al telefono", confirm: "Conferma", dismiss: "Scarta", sheet: "Scheda",
    maintenance: "Manutenzione ordinaria saltata: consigliare", lowConf: "riconoscimento incerto",
    outcome: { remote: "Risolto da remoto", part_diy: "Ricambio, lo monta il cliente", part_with_support: "Ricambio con supporto del service", technician: "Serve il tecnico" },
    incompatible: "Non compatibile con questa macchina", superseded: "Sostituito da", requires: "richiede",
    stock: "Giacenza", summary: "Resoconto della chiamata", machine: "Macchina", serial: "Matricola", symptom: "Sintomo", steps: "Verifiche fatte",
    confirmed: "Ricambi confermati", none: "nessuno", transcript: "Trascritto", again: "Nuova chiamata", outcomeLabel: "Esito",
    phase: "Vocabolario fase", terms: "termini", open: "in linea", closed: "chiusa", noSamples: "Nessuna chiamata di esempio caricata",
    tries: ["“Hi, we have a Marea 2 Plus and the coffee comes out weak and watery.”", "“The code on the invoice is G E twenty-one forty.”", "“I need the control board, E L three zero one zero.”"],
  },
  en: {
    tagline: "first-line service desk · Sereni espresso machines",
    startTitle: "The expert colleague who stays on the line with you.",
    startSub: "It transcribes the call, tells you what the customer means, recognises the machine and the fault, guides the diagnosis and finds the part.",
    sample: "Play a sample call", mic: "Use my microphone (you are the customer)",
    clarify: "Clear version", assistant: "Assistant", talk: "Conversation", diag: "Guided diagnosis", parts: "Proposed parts",
    log: "Assistant log", swap: "Swap roles", end: "End call", operator: "Operator", customer: "Customer",
    noDiag: "No symptom recognised yet. When the customer describes a problem, the procedure appears here.",
    ask: "Ask the customer", do: "Have them do", say: "Read this out", confirm: "Confirm", dismiss: "Dismiss", sheet: "Sheet",
    maintenance: "Routine maintenance skipped: recommend", lowConf: "low recognition confidence",
    outcome: { remote: "Fixed remotely", part_diy: "Part, fitted by the customer", part_with_support: "Part with service support", technician: "Technician needed" },
    incompatible: "Not compatible with this machine", superseded: "Superseded by", requires: "requires",
    stock: "Stock", summary: "Call report", machine: "Machine", serial: "Serial", symptom: "Symptom", steps: "Checks done",
    confirmed: "Confirmed parts", none: "none", transcript: "Transcript", again: "New call", outcomeLabel: "Outcome",
    phase: "Vocabulary phase", terms: "keyterms", open: "on the line", closed: "closed", noSamples: "No sample calls loaded",
    tries: ["“Hi, we have a Marea 2 Plus and the coffee comes out weak and watery.”", "“The code on the invoice is G E twenty-one forty.”", "“I need the control board, E L three zero one zero.”"],
  },
};

let lang = new URLSearchParams(location.search).get("lang") === "en" ? "en" : "it";
let L = T[lang];
let ws = null, audioCtx = null, micStream = null, timer = null, t0 = 0;
const cards = new Map();
const knownCodes = new Set();

function applyLanguage() {
  L = T[lang];
  document.documentElement.lang = lang;
  $("tagline").textContent = L.tagline; $("start-title").textContent = L.startTitle; $("start-sub").textContent = L.startSub;
  $("btn-sample").textContent = L.sample; $("btn-mic").textContent = L.mic; $("lb-clarify").textContent = L.clarify; $("lb-assistant").textContent = L.assistant;
  $("h-talk").textContent = L.talk; $("h-diag").textContent = L.diag; $("h-parts").textContent = L.parts; $("h-log").textContent = L.log;
  $("btn-swap").textContent = L.swap; $("btn-end").textContent = L.end; $("btn-lang").textContent = lang === "it" ? "EN" : "IT";
  $("try-saying").innerHTML = L.tries.map((t) => `<li>${esc(t)}</li>`).join("");
  if ($("diagnosis").classList.contains("empty")) $("diagnosis").textContent = L.noDiag;
}

async function loadSamples() {
  const list = await fetch("/api/samples").then((r) => r.json()).catch(() => []);
  const sel = $("sample-select");
  sel.innerHTML = list.length ? list.map((s) => `<option value="${esc(s.id)}">${esc(s[`title_${lang}`] || s.title || s.id)}</option>`).join("")
    : `<option value="">${esc(L.noSamples)}</option>`;
  $("btn-sample").disabled = !list.length;
}

function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

function startCall(source) {
  $("start").hidden = true; $("summary").hidden = true; $("call").hidden = false;
  ["turns", "parts", "log"].forEach((id) => ($(id).innerHTML = ""));
  $("diagnosis").className = "panel empty"; $("diagnosis").textContent = L.noDiag; cards.clear(); knownCodes.clear();
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/call?source=${encodeURIComponent(source)}&lang=${lang}`);
  ws.binaryType = "arraybuffer";
  ws.onmessage = (ev) => handle(JSON.parse(ev.data));
  ws.onclose = () => { stopMic(); clearInterval(timer); $("st-session").textContent = L.closed; $("st-session").classList.remove("on"); };
  ws.onopen = () => { t0 = Date.now(); timer = setInterval(tick, 500); if (source === "mic") startMic(); };
}

function tick() { const s = Math.floor((Date.now() - t0) / 1000); $("st-timer").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; }

async function startMic() {
  micStream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  audioCtx = new AudioContext();
  await audioCtx.audioWorklet.addModule("/static/worklet.js");
  const node = new AudioWorkletNode(audioCtx, "pcm16-downsampler");
  node.port.onmessage = (e) => { if (ws && ws.readyState === 1) ws.send(e.data); };
  audioCtx.createMediaStreamSource(micStream).connect(node);
}
function stopMic() { if (micStream) micStream.getTracks().forEach((t) => t.stop()); if (audioCtx) audioCtx.close(); micStream = audioCtx = null; }

function highlight(text) {
  let h = esc(text);
  for (const code of knownCodes) h = h.replaceAll(code, `<mark>${code}</mark>`);
  return h;
}

function handle(ev) {
  switch (ev.type) {
    case "session": $("st-session").textContent = L.open; $("st-session").classList.add("on"); break;
    case "turn": renderTurn(ev); break;
    case "clear": { const el = document.querySelector(`#turn-${ev.turn_id} .clear`); if (el) el.textContent = ev.text; break; }
    case "context": $("st-machine").textContent = [ev.model || ev.family || "—", ev.edition ? "Vaniglia" : "", ev.serial ? `#${ev.serial}` : ""].filter(Boolean).join(" · "); $("st-machine").classList.toggle("on", !!(ev.model || ev.family)); break;
    case "vocabulary": $("st-vocab").textContent = `${L.phase} ${ev.phase} · ${ev.count} ${L.terms}`; $("st-vocab").classList.toggle("on", ev.phase > 1); $("st-vocab").title = ev.sample.join(", "); break;
    case "parts": ev.cards.forEach((c) => { cards.set(c.code, c); knownCodes.add(c.code); }); renderParts(); break;
    case "part_status": if (cards.has(ev.code)) { cards.get(ev.code).status = ev.status; renderParts(); } break;
    case "diagnosis": renderDiagnosis(ev); break;
    case "agent": { const d = document.createElement("div"); d.innerHTML = `<time>${fmt(ev.at)}</time>${esc(ev.text)}`; $("log").prepend(d); break; }
    case "model_mention": { const d = document.createElement("div"); d.innerHTML = `<button class="ghost" style="padding:2px 8px;font-size:12px">→ ${esc(ev.model)}</button>`; d.querySelector("button").onclick = () => send({ type: "control", action: "set_machine", model_id: ev.model_id }); $("log").prepend(d); break; }
    case "toggles": $("tg-assistant").checked = ev.assistant; $("tg-clarify").checked = ev.clarify; break;
    case "summary": renderSummary(ev.summary); break;
    case "error": { const d = document.createElement("div"); d.style.color = "var(--bad)"; d.textContent = ev.text; $("log").prepend(d); break; }
  }
}
const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

function renderTurn(ev) {
  if (!ev.final) { $("partial").textContent = ev.text; return; }
  $("partial").textContent = "";
  let el = $(`turn-${ev.id}`);
  if (!el) { el = document.createElement("div"); el.id = `turn-${ev.id}`; $("turns").appendChild(el); }
  el.className = `turn ${ev.role}`;
  const low = ev.min_conf < 0.6 ? `<span class="low">${L.lowConf} (${ev.min_conf})</span>` : "";
  el.innerHTML = `<div class="who">${ev.role === "operator" ? L.operator : L.customer}${low}</div><div class="said">${highlight(ev.text)}</div><div class="clear"></div>`;
  el.scrollIntoView({ block: "end", behavior: "smooth" });
}

function renderDiagnosis(d) {
  const p = $("diagnosis"); p.className = "panel";
  const hist = d.history.length ? `<ol class="hist">${d.history.map((h) => `<li>${esc(h.text)} → <strong>${esc(h.answer)}</strong></li>`).join("")}</ol>` : "";
  const maint = d.maintenance_skipped ? `<div class="note">⚠ ${L.maintenance} ${d.suggested_parts.map(esc).join(", ")}</div>` : "";
  if (d.done) {
    p.innerHTML = `<h3>${esc(d.symptom)}</h3>${hist}${maint}<div class="outcome ${d.outcome}">${L.outcome[d.outcome]}${d.parts.length ? " · " + d.parts.map(esc).join(", ") : ""}</div>`;
    return;
  }
  const s = d.step;
  p.innerHTML = `<h3>${esc(d.symptom)}</h3>${hist}${maint}<div class="step"><div class="kind">${s.kind === "ask" ? L.ask : L.do}</div><div>${esc(s.text)}</div>` +
    `<div class="say"><small>${L.say}</small>${esc(s.say_in_english)}</div>${s.note ? `<div class="note">${esc(s.note)}</div>` : ""}` +
    `<div class="branches">${s.branches.map((b, i) => `<button data-branch="${i}">${esc(b)}</button>`).join("")}</div></div>`;
  p.querySelectorAll("[data-branch]").forEach((b) => (b.onclick = () => send({ type: "control", action: "answer_step", branch: +b.dataset.branch })));
}

function renderParts() {
  const why = { exact: "=", "near-code": "≈", description: "“…”", replacement: "↻", procedure: "✓" };
  $("parts").innerHTML = [...cards.values()].reverse().map((c) => {
    const stock = Object.entries(c.stock || {}).map(([w, q]) => `${esc(w.split(" ")[0])}: ${q}`).join(" · ");
    const flags = [!c.compatible ? L.incompatible : "", c.superseded_by ? `${L.superseded} ${c.superseded_by}${c.requires ? `, ${L.requires} ${c.requires}` : ""}` : ""].filter(Boolean);
    return `<div class="card ${c.status}"><span class="code">${esc(c.code)}</span><span class="why">${why[c.reason] || ""} ${Math.round(c.score * 100)}%</span>` +
      `<div>${esc(c.description)}</div><div class="meta">${c.price_eur != null ? c.price_eur.toFixed(2) + " € · " : ""}${L.stock} ${stock}</div>` +
      (flags.length ? `<div class="flag">${flags.map(esc).join(" · ")}</div>` : "") +
      `<div class="actions"><button data-act="confirm_part" data-code="${esc(c.code)}">${L.confirm}</button><button data-act="dismiss_part" data-code="${esc(c.code)}">${L.dismiss}</button><button data-sheet="${esc(c.code)}" class="ghost">${L.sheet}</button></div></div>`;
  }).join("");
  $("parts").querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => send({ type: "control", action: b.dataset.act, code: b.dataset.code })));
  $("parts").querySelectorAll("[data-sheet]").forEach((b) => (b.onclick = async () => {
    const r = await fetch(`/api/parts/${b.dataset.sheet}`).then((x) => x.json());
    $("sheet-body").textContent = r.sheet_markdown || ""; $("sheet").showModal();
  }));
}

function renderSummary(s) {
  $("call").hidden = true; $("summary").hidden = false;
  const o = s.outcome ? `${L.outcome[s.outcome.kind] || s.outcome.kind}${s.outcome.parts?.length ? " · " + s.outcome.parts.join(", ") : ""}` : "—";
  $("summary").innerHTML = `<div class="panel"><h3>${L.summary}</h3><table>` +
    `<tr><th>${L.machine}</th><td>${esc(s.machine || "—")}${s.edition ? " · Vaniglia" : ""}</td></tr><tr><th>${L.serial}</th><td>${esc(s.serial || "—")}</td></tr>` +
    `<tr><th>${L.symptom}</th><td>${esc(s.symptom || "—")}</td></tr><tr><th>${L.steps}</th><td>${s.steps.map((h) => `${esc(h.text)} → <strong>${esc(h.answer)}</strong>`).join("<br>") || "—"}</td></tr>` +
    `<tr><th>${L.outcomeLabel}</th><td><strong>${esc(o)}</strong></td></tr>` +
    `<tr><th>${L.confirmed}</th><td>${s.parts_confirmed.map((p) => `${esc(p.code)} — ${esc(p.description)} (${p.price_eur?.toFixed(2)} €)`).join("<br>") || L.none}</td></tr>` +
    `<tr><th>${L.transcript}</th><td>${s.transcript.map((t) => `<strong>${t.role === "operator" ? L.operator : L.customer}:</strong> ${esc(t.text)}${t.clear ? `<br><em style="color:var(--ok)">${esc(t.clear)}</em>` : ""}`).join("<br>")}</td></tr>` +
    `</table><p><button class="primary" onclick="location.reload()">${L.again}</button></p></div>`;
}

$("btn-sample").onclick = () => startCall(`sample:${$("sample-select").value}`);
$("btn-mic").onclick = () => startCall("mic");
$("btn-end").onclick = () => send({ type: "control", action: "end_call" });
$("btn-swap").onclick = () => send({ type: "control", action: "swap_roles" });
$("tg-clarify").onchange = (e) => send({ type: "control", action: "toggle", what: "clarify", on: e.target.checked });
$("tg-assistant").onchange = (e) => send({ type: "control", action: "toggle", what: "assistant", on: e.target.checked });
$("btn-lang").onclick = () => { lang = lang === "it" ? "en" : "it"; applyLanguage(); loadSamples(); };
$("sheet-close").onclick = () => $("sheet").close();
applyLanguage(); loadSamples();
