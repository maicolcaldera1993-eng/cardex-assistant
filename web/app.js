// Cardex — Sereni service desk. No framework: one WebSocket to our server (panel events, tools, transcript), plus
// for the voice agent a second one to AssemblyAI's Voice Agent API, relayed by this page.
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const eur = (v) => (v == null ? "—" : v.toLocaleString(lang === "it" ? "it-IT" : "en-GB", { style: "currency", currency: "EUR" }));

// ------------------------------------------------------------------ texts
const T = {
  it: {
    tagline: "Service Sereni Macchine da Caffè", demoBadge: "Demo · dati fittizi",
    startTitle: "Il primo livello di assistenza che conosce ogni macchina Sereni.",
    startSub: "Cardex riconosce la macchina e il guasto, guida il cliente nella procedura del costruttore passo per passo, trova il ricambio giusto, dice chi paga e fissa l'intervento. Una persona approva prima che parta qualsiasi ordine.",
    stats: (m, s) => [`<b>${m}</b> modelli`, `<b>${s}</b> procedure guidate`, `<b>237</b> ricambi a catalogo`, `<b>6</b> lingue parlate`],
    voiceEyebrow: "Modalità 1", voiceTitle: "Assistente automatico",
    voiceDesc: "Un assistente vocale che risponde da solo alle chiamate dei clienti. Riconosce macchina e guasto, guida il cliente nella procedura del costruttore, dice chi paga, ordina i ricambi e fissa l'intervento. Conversa liberamente, ma ogni domanda viene dalla procedura e ogni cifra dal gestionale.",
    voiceTry: "Provalo tu, nei panni del cliente: scegli una delle chiamate d'esempio, con la scheda di cosa dire, oppure il parlato libero.",
    lbPersona: "Chiamate d'esempio", lbVoiceLang: "Lingua della chiamata", voiceStart: "Chiama l'assistenza",
    voiceHelp: "Serve il microfono. Parla con calma e aspetta che l'agente finisca: mentre parla il microfono è in pausa. Chiudi con «Fine chiamata».",
    opEyebrow: "Modalità 2", opTitle: "Assistenza all'operatore",
    opDesc: "Cardex affianca l'operatore del service durante la telefonata con un cliente straniero: trascrive chi dice cosa, mostra la versione chiara in italiano, apre la procedura al passo giusto con la frase da leggere, prepara ricambi, appuntamento e scheda d'intervento.",
    opTry: "Provalo tu, nei panni dell'operatore al telefono: il cliente è un'intelligenza artificiale che recita il suo ruolo; tu rispondi al microfono e segui la procedura guidata.",
    duoTitle: "Oppure ascolta una chiamata", duoDesc: "L'assistente risponde al cliente scelto sopra, interpretato da un'altra IA: senti le due voci e vedi Cardex lavorare. Nessun microfono.", duoBtn: "Ascolta",
    modeDuo: "Chiamata tra due IA · ascolto", duoAgent: "Parla l'assistente Sereni", duoCustomer: "Parla il cliente", duoSub: "Ascolta: nessun microfono in questa modalità.", duoPickCustomer: "Scegli prima un cliente d'esempio.",
    rpTitle: "Fai tu l'operatore", rpDesc: "Scegli il cliente: ti chiama, descrive il guasto e risponde alle tue domande. Non conosci la soluzione: te la suggerisce Cardex.", rpBtn: "Rispondi alla chiamata",
    customerTalking: "Il cliente sta parlando", customerSub: "Il microfono è in pausa: aspetta che finisca.", yourTurn: "Tocca a te", yourTurnSub: "Rispondi al cliente: segui la procedura a destra.", opFirst: "Il telefono squilla: rispondi tu per primo, per esempio «Servizio Sereni, buongiorno».",
    modeRoleplay: "Assistenza all'operatore · cliente simulato",
    sampleTitle: "Ascolta una chiamata", sampleDesc: "Una telefonata registrata, senza microfono: guarda cosa riconosce Cardex.", sampleBtn: "Ascolta",
    duetTitle: "Fai tu l'operatore", duetHelp: "Parli al microfono come operatore e clicchi le battute del cliente registrato; Cardex ti suggerisce cosa chiedere.", duetBtn: "Inizia",
    micTitle: "Parlato libero", micDesc: "Parla tu, come cliente, e guarda cosa capisce Cardex.", micBtn: "Apri console",
    howTitle: "Come funziona",
    how: [["Ascolta", "AssemblyAI Universal-3.5 Pro trascrive in tempo reale, distingue le voci e ricarica il vocabolario (modelli, codici) man mano che capisce di quale macchina si parla."],
          ["Capisce", "Il guasto descritto in qualunque lingua viene collegato alla procedura del costruttore, ma solo tra quelle della macchina in linea: niente risposte inventate."],
          ["Agisce", "Ricambi con prezzo e consegna dal gestionale, garanzia dalla matricola, appuntamento dal calendario del service, e una scheda d'intervento da approvare."]],
    powered: "Voce e trascrizione: AssemblyAI Voice Agent API e Universal-3.5 Pro Streaming. Sereni, i clienti e il gestionale sono inventati per la demo.",
    noDuets: "Nessuna prova disponibile", noSamples: "Nessuna chiamata registrata",
    modeVoice: "Chiamata con l'agente vocale", modeOp: "Console operatore",
    open: "in linea", closed: "chiusa", connecting: "connessione…",
    presenceConnecting: "Connessione all'agente…", presenceSpeaking: "L'agente sta parlando", presenceListening: "Ti ascolto",
    presenceSubSpeaking: "Il microfono è in pausa: aspetta che finisca.", presenceSubListening: "Parla pure.", presenceDenied: "Microfono non disponibile", presenceSubDenied: "Consenti il microfono nel browser, poi riavvia la chiamata.",
    clarify: "Versione chiara", assistant: "Assistente", swap: "Scambia voci", end: "Fine chiamata",
    talk: "Conversazione", diag: "Procedura guidata", parts: "Ricambi", docs: "Documenti", log: "Registro dell'assistente",
    emptyTalk: "La conversazione compare qui, con chi dice cosa.", emptyParts: "Qui compaiono i ricambi citati o previsti dalla procedura.",
    noDocs: "Quando si parla di una macchina, di un guasto o di un ricambio, il documento giusto si apre qui, al punto giusto.",
    noDiag: "Nessun guasto riconosciuto. Appena il cliente descrive il problema, la procedura compare qui.",
    agent: "Agente", operator: "Operatore", customer: "Cliente",
    merged: "frasi unite", interrupted: "interrotta", lowConf: "riconoscimento incerto", clearWait: "versione chiara in arrivo…",
    micMuted: "mic in pausa", micDenied: "microfono negato", agentTalking: "parla l'agente",
    choose: "Due guasti possibili. Di quale si tratta?", change: "Procedura sbagliata? Cambia…", startProc: "Avvia una procedura a mano…",
    ask: "Chiedi al cliente", do: "Fagli fare", say: "Da leggere al telefono", keys: "tasti 1-4",
    watching: "L'agente conduce la procedura: i passi avanzano con le risposte del cliente.",
    closeRemote: "Risolto da remoto", closeTech: "Serve il tecnico", closeHint: "Chiudi quando il cliente conferma",
    pending: "In attesa", startNow: "Avvia", drop: "Scarta", maintenance: "Manutenzione ordinaria saltata: consigliare",
    outcome: { remote: "Risolto da remoto", part_diy: "Ricambio, lo monta il cliente", part_with_support: "Ricambio con supporto del service", technician: "Serve il tecnico" },
    nextTitle: "Cosa fare ora", total: "Totale ricambi",
    bookTech: "Appuntamento del tecnico", bookCall: "Seconda chiamata con il service", pickSlot: "Primi slot liberi", unbook: "Annulla",
    needSerial: "Serve la matricola per sapere la zona del tecnico.", noPartner: "Nessun partner service in questo paese: passare alla sede.",
    noSlots: "Nessuno slot libero nelle prossime due settimane.", booked: "Prenotato",
    handling: { diy: "Lo monta il cliente", support: "Montaggio con il service", technician: "Serve il tecnico" },
    sayPart: "Da dire al cliente", confirm: "Conferma", dismiss: "Scarta", sheet: "Scheda",
    incompatible: "Non compatibile con questa macchina", superseded: "Sostituito da", requires: "richiede", fromSupplier: "dal fornitore", days: "gg",
    reason: { exact: "codice esatto", "near-code": "codice simile", description: "dalla descrizione", replacement: "sostituto", procedure: "dalla procedura", "voice-agent": "richiesto" },
    warranty: "In garanzia fino al", noWarranty: "Fuori garanzia dal", built: "Costruita", installed: "Installata", voltage: "Tensione", orders: "Ordini precedenti",
    serialHeard: "sentita", phase: "Vocabolario", terms: "termini",
    // report
    wo: "Scheda d'intervento", reportFor: "Esito della chiamata", noOutcome: "Nessun esito",
    secMachine: "Cliente e macchina", secDiag: "Diagnosi", secParts: "Ricambi", secNext: "Seguito", secNotes: "Note per l'operatore",
    machine: "Macchina", serial: "Matricola", customerName: "Cliente", place: "Luogo", warrantyLbl: "Garanzia", symptom: "Guasto",
    thCode: "Codice", thDesc: "Descrizione", thStatus: "Stato", thPrice: "Listino", thPays: "A carico cliente", totalPays: "Totale a carico del cliente (confermati)",
    covered: "in garanzia", consumable: "materiale di consumo: non coperto dalla garanzia", pays: "paga il cliente", stConfirmed: "confermato", stProposed: "da confermare", stDismissed: "scartato", stMentioned: "citato, non ordinato", stIncompatible: "non compatibile",
    nextStep: "Prossimo passo", appointment: "Appuntamento", notBooked: "non prenotato: richiesto dall'esito", none: "nessuno", noSteps: "Nessuna verifica registrata.",
    approve: "Approva e invia al magazzino", approved: "Approvato · ordine inviato al magazzino (simulazione)", print: "Stampa", again: "Nuova chiamata",
    showTranscript: "Trascritto completo", diarCheck: "Attribuzione delle voci", duration: "Durata",
    toastApproved: "Ordine approvato. In produzione partirebbe verso il magazzino.",
    serverLost: "Connessione con il server persa: la chiamata è stata interrotta.", backHome: "Torna alla home",
  },
  en: {
    tagline: "Sereni espresso machines · service", demoBadge: "Demo · fictional data",
    startTitle: "First-line support that knows every Sereni machine.",
    startSub: "Cardex recognises the machine and the fault, walks the customer through the maker's procedure step by step, finds the right spare part, says who pays and books the visit. A person approves before any order goes out.",
    stats: (m, s) => [`<b>${m}</b> models`, `<b>${s}</b> guided procedures`, `<b>237</b> parts in the catalogue`, `<b>6</b> spoken languages`],
    voiceEyebrow: "Mode 1", voiceTitle: "Automatic assistant",
    voiceDesc: "A voice assistant that answers customers' calls on its own. It recognises the machine and the fault, walks the customer through the maker's procedure, says who pays, orders the parts and books the visit. It talks freely, but every question comes from the procedure and every figure from the ERP.",
    voiceTry: "Try it as the customer: pick one of the sample calls, each with a sheet of what to say, or free speech.",
    lbPersona: "Sample calls", lbVoiceLang: "Call language", voiceStart: "Call the service desk",
    voiceHelp: "Needs the microphone. Speak calmly and let the agent finish: while it talks your mic is paused. Close with “End call”.",
    opEyebrow: "Mode 2", opTitle: "Operator assist",
    opDesc: "Cardex sits next to the service operator during a call with a foreign customer: it transcribes who says what, shows a clear Italian version, opens the procedure at the right step with the sentence to read, and prepares parts, appointment and work order.",
    opTry: "Try it as the operator on the phone: the customer is an AI playing its part; you answer on the microphone and follow the guided procedure.",
    duoTitle: "Or listen to a call", duoDesc: "The assistant answers the customer picked above, played by another AI: hear both voices and watch Cardex work. No microphone.", duoBtn: "Listen",
    modeDuo: "Call between two AIs · listening", duoAgent: "The Sereni assistant is speaking", duoCustomer: "The customer is speaking", duoSub: "Listen: no microphone in this mode.", duoPickCustomer: "Pick a sample customer first.",
    rpTitle: "Be the operator", rpDesc: "Pick the customer: they call, describe the fault and answer your questions. You don't know the fix: Cardex suggests it.", rpBtn: "Answer the call",
    customerTalking: "The customer is speaking", customerSub: "Your mic is paused: let them finish.", yourTurn: "Your turn", yourTurnSub: "Answer the customer: follow the procedure on the right.", opFirst: "The phone rings: you speak first, for example “Sereni service, good morning”.",
    modeRoleplay: "Operator assist · simulated customer",
    sampleTitle: "Listen to a call", sampleDesc: "A recorded call, no microphone: see what Cardex picks up.", sampleBtn: "Listen",
    duetTitle: "Be the operator", duetHelp: "You speak on the mic as the operator and click the recorded customer's lines; Cardex suggests what to ask.", duetBtn: "Start",
    micTitle: "Free speech", micDesc: "You speak, as the customer, and see what Cardex understands.", micBtn: "Open console",
    howTitle: "How it works",
    how: [["Listens", "AssemblyAI Universal-3.5 Pro transcribes in real time, tells the voices apart and reloads the vocabulary (models, codes) as it learns which machine the call is about."],
          ["Understands", "A fault described in any language is linked to the maker's procedure, but only among those of the machine on the call: no made-up answers."],
          ["Acts", "Parts with price and delivery from the ERP, warranty from the serial number, a slot from the service calendar, and a work order to approve."]],
    powered: "Voice and transcription: AssemblyAI Voice Agent API and Universal-3.5 Pro Streaming. Sereni, its customers and the ERP are invented for the demo.",
    noDuets: "No rehearsal available", noSamples: "No recorded call",
    modeVoice: "Call with the voice agent", modeOp: "Operator console",
    open: "on the line", closed: "closed", connecting: "connecting…",
    presenceConnecting: "Connecting to the agent…", presenceSpeaking: "The agent is speaking", presenceListening: "Listening",
    presenceSubSpeaking: "Your mic is paused: let it finish.", presenceSubListening: "Go ahead.", presenceDenied: "Microphone unavailable", presenceSubDenied: "Allow the microphone in the browser, then restart the call.",
    clarify: "Clear version", assistant: "Assistant", swap: "Swap voices", end: "End call",
    talk: "Conversation", diag: "Guided procedure", parts: "Parts", docs: "Documents", log: "Assistant log",
    emptyTalk: "The conversation appears here, with who said what.", emptyParts: "Parts named on the call or foreseen by the procedure appear here.",
    noDocs: "When a machine, a fault or a part comes up, the right document opens here, at the right place.",
    noDiag: "No fault recognised yet. As soon as the customer describes the problem, the procedure appears here.",
    agent: "Agent", operator: "Operator", customer: "Customer",
    merged: "sentences joined", interrupted: "interrupted", lowConf: "low confidence", clearWait: "clear version on its way…",
    micMuted: "mic paused", micDenied: "microphone denied", agentTalking: "agent talking",
    choose: "Two possible faults. Which one is it?", change: "Wrong procedure? Change…", startProc: "Start a procedure by hand…",
    ask: "Ask the customer", do: "Have them do", say: "Read this out", keys: "keys 1-4",
    watching: "The agent leads the procedure: steps move on with the customer's answers.",
    closeRemote: "Fixed remotely", closeTech: "Technician needed", closeHint: "Close when the customer confirms",
    pending: "Waiting", startNow: "Start", drop: "Discard", maintenance: "Routine maintenance skipped: recommend",
    outcome: { remote: "Fixed remotely", part_diy: "Part, fitted by the customer", part_with_support: "Part with service support", technician: "Technician needed" },
    nextTitle: "What to do now", total: "Parts total",
    bookTech: "Technician's visit", bookCall: "Second call with service", pickSlot: "First free slots", unbook: "Cancel",
    needSerial: "The serial number is needed to know the technician's zone.", noPartner: "No service partner in this country: escalate to head office.",
    noSlots: "No free slot in the next two weeks.", booked: "Booked",
    handling: { diy: "Customer fits it", support: "Fitted with service support", technician: "Technician needed" },
    sayPart: "Say to the customer", confirm: "Confirm", dismiss: "Dismiss", sheet: "Sheet",
    incompatible: "Not compatible with this machine", superseded: "Superseded by", requires: "requires", fromSupplier: "from supplier", days: "days",
    reason: { exact: "exact code", "near-code": "similar code", description: "from description", replacement: "replacement", procedure: "from procedure", "voice-agent": "requested" },
    warranty: "Under warranty until", noWarranty: "Out of warranty since", built: "Built", installed: "Installed", voltage: "Voltage", orders: "Previous orders",
    serialHeard: "heard", phase: "Vocabulary", terms: "terms",
    wo: "Work order", reportFor: "Call outcome", noOutcome: "No outcome",
    secMachine: "Customer and machine", secDiag: "Diagnosis", secParts: "Parts", secNext: "Follow-up", secNotes: "Notes for the operator",
    machine: "Machine", serial: "Serial", customerName: "Customer", place: "Location", warrantyLbl: "Warranty", symptom: "Fault",
    thCode: "Code", thDesc: "Description", thStatus: "Status", thPrice: "List price", thPays: "Customer pays", totalPays: "Customer pays in total (confirmed)",
    covered: "warranty", consumable: "consumable: not covered by the warranty", pays: "customer pays", stConfirmed: "confirmed", stProposed: "to confirm", stDismissed: "dismissed", stMentioned: "mentioned, not ordered", stIncompatible: "does not fit",
    nextStep: "Next step", appointment: "Appointment", notBooked: "not booked: required by the outcome", none: "none", noSteps: "No checks recorded.",
    approve: "Approve and send to the warehouse", approved: "Approved · order sent to the warehouse (simulation)", print: "Print", again: "New call",
    showTranscript: "Full transcript", diarCheck: "Voice attribution", duration: "Duration",
    toastApproved: "Order approved. In production it would go to the warehouse.",
    serverLost: "Connection to the server lost: the call was interrupted.", backHome: "Back to home",
  },
};

// customers to play in the voice-agent mode: facts only, the conversation is up to the caller
const PERSONAS = [
  { id: "luca", name: "Luca Ferraro", lang: "it", machine: "Giglio 1 Plus Vaniglia", serial: "051040",
    it: { where: "Pasticceria italiana a Valencia", problem: "Quando togli il portafiltro a fine caffè, il fondo è liquido e schizza. Una ragazza al banco si è scottata.",
          facts: ["Non senti più lo sfiato «pssh» verso la vaschetta a fine erogazione.", "I lavaggi con la pastiglia li faceva lui; da tre settimane forse nessuno.", "Se ti fanno aprire l'elettrovalvola: pistoncino rigato, gommina spaccata."],
          ask: "Chiedi se è in garanzia e se la colpa dei ragazzi la fa perdere." },
    en: { where: "Italian pastry shop in Valencia", problem: "When you remove the portafilter after the shot, the puck is wet and it sprays. A barista got burnt.",
          facts: ["You no longer hear the short discharge into the drip tray.", "He used to backflush every night; maybe nobody has for three weeks.", "If asked to open the solenoid: the plunger is scratched, the rubber is split."],
          ask: "Ask if it's under warranty and whether the staff's neglect voids it." } },
  { id: "mehmet", name: "Mehmet Aydın", lang: "en", machine: "Marea 2 Evo", serial: "052710",
    it: { where: "Capo barista, Hotel Excelsior, Vienna", problem: "Dal gruppo di sinistra, a portafiltro agganciato, esce acqua intorno al bordo e gocciola nella tazza.",
          facts: ["L'acqua viene dal bordo del portafiltro, non dal gruppo sopra.", "Guarnizione originale, la maniglia va molto oltre il centro.", "Sulla vecchia confezione: G E twenty-four ten (è di un'altra macchina)."],
          ask: "Chiedi se paghi, quanto ci mette ad arrivare e se puoi montarla tu." },
    en: { where: "Head barista, Hotel Excelsior, Vienna", problem: "On the left group, with the portafilter locked, water comes out around the rim and drips into the cup.",
          facts: ["Water comes from the portafilter rim, not from the group above.", "Original gasket; the handle goes far past the centre.", "The old packaging says G E twenty-four ten (another machine's part)."],
          ask: "Ask if you pay, how long delivery takes, and whether you can fit it yourself." } },
  { id: "dave", name: "Dave Miller", lang: "en", machine: "Marea 2 · 110 V", serial: "041302",
    it: { where: "Espresso Corner, Chicago", problem: "Da stamattina la macchina resta fredda: manometro a zero, niente vapore.",
          facts: ["Spie e tasti accesi, nessun allarme.", "Pulsante rosso premuto: dopo dieci minuti ancora fredda.", "All'accensione senti il clic del teleruttore. Macchina a 110 volt."],
          ask: "Chiedi quanto costa in tutto e quando arrivano i pezzi; accetta il primo slot." },
    en: { where: "Espresso Corner, Chicago", problem: "Since this morning the machine stays cold: gauge at zero, no steam.",
          facts: ["Lights and buttons on, no alarm.", "Red reset button pressed: ten minutes later still cold.", "You hear the contactor click at power-on. 110-volt machine."],
          ask: "Ask the total cost and when parts arrive; accept the first slot." } },
  { id: "klaus", name: "Klaus Becker", lang: "en", machine: "Onda MB2", serial: "044801",
    it: { where: "Kaffeehaus Nord, Berlino", problem: "Niente vapore: il manometro della caldaia vapore è a zero, il latte non si monta.",
          facts: ["L'icona del vapore sul pannello è accesa.", "Sul display nessun errore, la pressione resta 0,0.", "Macchina Onda MB2 a 230 volt."],
          ask: "Chiedi se deve venire un tecnico e quando." },
    en: { where: "Kaffeehaus Nord, Berlin", problem: "No steam: the steam boiler gauge is at zero, milk won't froth.",
          facts: ["The steam icon on the panel is on.", "No error on the display, pressure stays at 0.0.", "Onda MB2, 230 volts."],
          ask: "Ask whether a technician must come, and when." } },
  { id: "free", name: "", lang: null, machine: "", serial: "",
    it: { where: "", problem: "", facts: [], ask: "" }, en: { where: "", problem: "", facts: [], ask: "" } },
];
const PERSONA_LABEL = { it: "Parlato libero", en: "Free speech" };
const FREE_BRIEF = {
  it: "Inventa tu cliente e guasto. Matricole in archivio: 047219 Marea 2 Plus · 041188 Marea 2 · 043377 Giglio 1 · 049155 Onda MB3 · 053002 Onda MB2 Evo · G24-0177 Monda 65 · G25-0412 Monda 65 Digit.",
  en: "Make up your own customer and fault. Serials on file: 047219 Marea 2 Plus · 041188 Marea 2 · 043377 Giglio 1 · 049155 Onda MB3 · 053002 Onda MB2 Evo · G24-0177 Monda 65 · G25-0412 Monda 65 Digit.",
};

let lang = new URLSearchParams(location.search).get("lang") === "en" ? "en" : "it";
let L = T[lang];
let persona = "luca";
let counts = { models: 10, symptoms: 32 };
let ws = null, audioCtx = null, micStream = null, timer = null, t0 = 0, micMuted = false, duetId = null, duetPlaying = false, micWatchdog = null;
let callMode = "op";
let roleplay = false, rpSpoke = false;
const cards = new Map();
const knownCodes = new Set();
const docs = [];
let activeDoc = -1;
let lastMachine = null;

// ------------------------------------------------------------------ home
function applyLanguage() {
  L = T[lang];
  document.documentElement.lang = lang;
  const set = (id, v) => { const e = $(id); if (e) e.textContent = v; };
  set("tagline", L.tagline); set("demo-badge", L.demoBadge); set("start-title", L.startTitle); set("start-sub", L.startSub);
  $("stats").innerHTML = L.stats(counts.models, counts.symptoms).map((s) => `<li>${s}</li>`).join("");
  set("voice-eyebrow", L.voiceEyebrow); set("voice-title", L.voiceTitle); set("voice-desc", L.voiceDesc); set("lb-persona", L.lbPersona);
  set("lb-voice-lang", L.lbVoiceLang); set("btn-voice", L.voiceStart); set("voice-help", L.voiceHelp);
  set("op-eyebrow", L.opEyebrow); set("op-title", L.opTitle); set("op-desc", L.opDesc); set("op-try", L.opTry); set("voice-try", L.voiceTry);
  set("rp-title", L.rpTitle); set("rp-desc", L.rpDesc); set("btn-roleplay", L.rpBtn);
  set("duo-title", L.duoTitle); set("duo-desc", L.duoDesc); set("btn-duo", L.duoBtn);
  $("rp-select").innerHTML = PERSONAS.filter((p) => p.id !== "free").concat([{ id: "carmen", name: "Carmen Ruiz", machine: "Marea 2" }])
    .map((p) => `<option value="${p.id}">${esc(p.name)} · ${esc(p.machine)}</option>`).join("");
  set("sample-title", L.sampleTitle); set("sample-desc", L.sampleDesc); set("btn-sample", L.sampleBtn);
  set("duet-title", L.duetTitle); set("duet-help", L.duetHelp); set("btn-duet", L.duetBtn);
  set("mic-title", L.micTitle); set("mic-desc", L.micDesc); set("btn-mic", L.micBtn);
  set("how-title", L.howTitle); set("powered", L.powered);
  $("how-steps").innerHTML = L.how.map(([h, t]) => `<li><strong>${esc(h)}</strong><span>${esc(t)}</span></li>`).join("");
  set("lb-clarify", L.clarify); set("lb-assistant", L.assistant); set("btn-swap", L.swap); set("lb-end", L.end);
  set("h-talk", L.talk); set("h-diag", L.diag); set("h-parts", L.parts); set("h-docs", L.docs); set("h-log", L.log);
  $("btn-lang").textContent = lang === "it" ? "English" : "Italiano";
  if ($("doc-view").classList.contains("empty")) $("doc-view").textContent = L.noDocs;
  if ($("diagnosis").classList.contains("empty")) renderEmptyDiag();
  renderPersonas();
}

function renderPersonas() {
  $("personas").innerHTML = PERSONAS.map((p) => `<button class="persona ${p.id === persona ? "active" : ""}" data-p="${p.id}">${esc(p.name || PERSONA_LABEL[lang])}<small>${esc(p.machine || "—")}</small></button>`).join("");
  $("personas").querySelectorAll("[data-p]").forEach((b) => (b.onclick = () => {
    persona = b.dataset.p;
    const p = PERSONAS.find((x) => x.id === persona);
    if (p.lang) $("voice-lang").value = p.lang;
    renderPersonas();
  }));
  const p = PERSONAS.find((x) => x.id === persona);
  const b = p[lang];
  $("persona-brief").innerHTML = p.id === "free" ? `<p style="margin:0">${esc(FREE_BRIEF[lang])}</p>` :
    `<h5>${esc(p.name)} · ${esc(b.where)}</h5>
     <dl><dt>${esc(L.machine)}</dt><dd>${esc(p.machine)}</dd><dt>${esc(L.serial)}</dt><dd>${esc(p.serial)}</dd><dt>${esc(L.symptom)}</dt><dd>${esc(b.problem)}</dd></dl>
     <ul>${b.facts.map((f) => `<li>${esc(f)}</li>`).join("")}</ul><div class="say-it">${esc(b.ask)}</div>`;
}

async function loadHomeData() {
  const [models, symptoms, samples, duets] = await Promise.all([
    fetch("/api/models").then((r) => r.json()).catch(() => null), fetch("/api/symptoms").then((r) => r.json()).catch(() => null),
    fetch("/api/samples").then((r) => r.json()).catch(() => []), fetch("/api/duets").then((r) => r.json()).catch(() => [])]);
  if (models) counts.models = models.length;
  if (symptoms) counts.symptoms = symptoms.length;
  $("stats").innerHTML = L.stats(counts.models, counts.symptoms).map((s) => `<li>${s}</li>`).join("");
  $("sample-select").innerHTML = samples.length ? samples.map((s) => `<option value="${esc(s.id)}">${esc(s[`title_${lang}`] || s.title || s.id)}</option>`).join("") : `<option value="">${esc(L.noSamples)}</option>`;
  $("btn-sample").disabled = !samples.length;
  $("duet-select").innerHTML = duets.length ? duets.map((d) => `<option value="${esc(d.id)}">${esc(d[`title_${lang}`] || d.id)}</option>`).join("") : `<option value="">${esc(L.noDuets)}</option>`;
  $("btn-duet").disabled = !duets.length;
}

// ------------------------------------------------------------------ call
function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

function startCall(source) {
  callMode = source === "voice" ? "voice" : "op";
  roleplay = source.startsWith("roleplay");
  $("start").hidden = true; $("topbar").hidden = true; $("summary").hidden = true; $("call").hidden = false;
  $("call").classList.toggle("voice", callMode === "voice");
  $("call").classList.toggle("sample", source.startsWith("sample:"));
  $("call-mode").textContent = callMode === "voice" ? L.modeVoice : roleplay ? L.modeRoleplay : L.modeOp;
  $("st-session").textContent = L.connecting; $("live-dot").classList.remove("on");
  $("turns").innerHTML = `<div class="empty-hint" id="talk-empty">${esc(L.emptyTalk)}</div>`;
  $("parts").innerHTML = `<div class="empty-hint" id="parts-empty">${esc(L.emptyParts)}</div>`;
  $("log").innerHTML = ""; $("machine-record").hidden = true; lastMachine = null; $("st-warranty").hidden = true;
  symptomMenu = []; renderEmptyDiag(); cards.clear(); knownCodes.clear(); docs.length = 0; activeDoc = -1;
  $("doc-tabs").innerHTML = ""; $("doc-view").className = "doc-view empty"; $("doc-view").textContent = L.noDocs;
  $("presence").hidden = callMode !== "voice" && !roleplay; setPresence("connecting");
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/call?source=${encodeURIComponent(source)}&lang=${lang}`);
  ws.binaryType = "arraybuffer";
  ws.onmessage = (ev) => handle(JSON.parse(ev.data));
  ws.onclose = () => {
    stopMic(); clearInterval(timer); $("st-session").textContent = L.closed; $("live-dot").classList.remove("on");
    if (!$("call").hidden) {                                   // the server went away mid-call: say so, end the agents
      toast(L.serverLost); logLine(L.serverLost, true);
      if (duo) duoEnd(); else if (vws && vws.readyState === 1) { try { vws.send(JSON.stringify({ type: "session.end" })); vws.close(); } catch (e) { /* closing */ } }
      $("lb-end").textContent = L.backHome; $("btn-end").onclick = () => location.reload();
    }
  };
  duetId = source.startsWith("duet:") ? source.slice(5) : null; $("duet-panel").hidden = !duetId; $("duet-lines").innerHTML = "";
  ws.onopen = () => { t0 = Date.now(); timer = setInterval(tick, 500); if (source === "mic" || source === "auto" || duetId) startMic(); };
}

function tick() { const s = Math.floor((Date.now() - t0) / 1000); $("st-timer").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; }

function setMeter(peak, state) {
  const m = $("mic-meter"); const bars = m.children; const level = Math.min(1, peak / 9000);
  for (let i = 0; i < bars.length; i++) bars[i].style.height = `${4 + Math.max(0, level * 14 - Math.abs(i - 2) * 2.5)}px`;
  m.classList.toggle("hot", state === "hot"); m.classList.toggle("hold", state === "hold");
}
let presenceState = "";
function setPresence(state) {
  if (state === presenceState) return;
  presenceState = state;
  const p = $("presence"); p.classList.toggle("speaking", state === "speaking"); p.classList.toggle("listening", state === "listening"); p.classList.toggle("denied", state === "denied");
  const R = roleplay, D = !!duo;
  $("presence-title").textContent = D ? ({ speaking: L.duoAgent, customer: L.duoCustomer }[state] || L.modeDuo)
    : ({ speaking: R ? L.customerTalking : L.presenceSpeaking, listening: R ? L.yourTurn : L.presenceListening, denied: L.presenceDenied }[state] || L.presenceConnecting);
  $("presence-sub").textContent = D ? L.duoSub
    : ({ speaking: R ? L.customerSub : L.presenceSubSpeaking, listening: R ? (rpSpoke ? L.yourTurnSub : L.opFirst) : L.presenceSubListening, denied: L.presenceSubDenied }[state] || "");
  p.classList.toggle("customer", state === "customer");
}

async function startMic() {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  } catch (e) {
    $("st-mic").textContent = e.name === "NotAllowedError" ? L.micDenied : e.message; $("st-mic").classList.add("bad"); return;
  }
  audioCtx = new AudioContext();
  await audioCtx.resume();
  await audioCtx.audioWorklet.addModule("/static/worklet.js");
  const node = new AudioWorkletNode(audioCtx, "pcm16-downsampler");
  node.port.onmessage = (e) => {
    const pcm = new Int16Array(e.data); let peak = 0;
    for (let i = 0; i < pcm.length; i += 8) { const v = Math.abs(pcm[i]); if (v > peak) peak = v; }
    const pill = $("st-mic");
    pill.textContent = micMuted ? L.micMuted : "mic"; pill.classList.toggle("on", !micMuted && peak > 1500);
    setMeter(micMuted ? 0 : peak, micMuted ? "hold" : peak > 1500 ? "hot" : "");
    if (ws && ws.readyState === 1 && !micMuted) ws.send(e.data);
  };
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
    case "session": $("st-session").textContent = L.open; $("live-dot").classList.add("on"); break;
    case "turn": renderTurn(ev); break;
    case "clear": { const el = document.querySelector(`#turn-${ev.turn_id} .clear`); if (el) { el.textContent = ev.text; el.classList.remove("wait"); } break; }
    case "clear_pending": { const el = document.querySelector(`#turn-${ev.turn_id} .clear`); if (el && !el.textContent) { el.textContent = L.clearWait; el.classList.add("wait"); } break; }
    case "context":
      $("st-machine").textContent = [ev.model || ev.family || "—", ev.edition ? "Vaniglia" : "", ev.serial ? `#${ev.serial}` : ""].filter(Boolean).join(" · ");
      $("st-machine").classList.toggle("on", !!(ev.model || ev.family));
      symptomMenu = ev.symptoms || []; if ($("diagnosis").classList.contains("empty")) renderEmptyDiag();
      if (lastMachine && ev.model && lastMachine.model !== ev.model) { lastMachine.model = ev.model; renderMachine(lastMachine); }
      break;
    case "vocabulary": $("st-vocab").textContent = `${L.phase} ${ev.phase} · ${ev.count} ${L.terms}`; $("st-vocab").title = ev.sample.join(", "); break;
    case "parts": ev.cards.forEach((c) => { cards.set(c.code, c); knownCodes.add(c.code); }); renderParts(); break;
    case "part_status": if (cards.has(ev.code)) { cards.get(ev.code).status = ev.status; renderParts(); } break;
    case "diagnosis": renderDiagnosis(ev); break;
    case "symptom_choice": renderChoice(ev.options); break;
    case "machine_record": {
      lastMachine = ev; renderMachine(ev);
      const w = $("st-warranty"); w.hidden = false;
      w.textContent = ev.in_warranty ? `✓ ${L.warranty} ${ev.warranty_until}` : `${L.noWarranty} ${ev.warranty_until}`;
      w.className = `chip ${ev.in_warranty ? "on" : "bad"}`;
      toast(`${ev.model} #${ev.serial} · ${w.textContent}`);
      break;
    }
    case "duet_script": renderDuet(ev.lines); break;
    case "speak": speak(ev); break;
    case "tool_result": voiceToolResult(ev); break;
    case "hangup": if (vws) { vEndPending = true; setTimeout(voiceEnd, 15000); } break;
    case "duet": { const b = document.querySelector(`.duet-line[data-n="${ev.n}"]`); if (b) { b.classList.toggle("playing", ev.state === "playing"); if (ev.state === "done") b.classList.add("said"); } if (ev.state === "done" || ev.state === "busy") { clearTimeout(micWatchdog); setTimeout(() => { micMuted = false; duetPlaying = false; }, 300); } break; }
    case "open_doc": openDoc(ev); break;
    case "agent": logLine(ev.text, false, ev.at); break;
    case "model_mention": { const d = document.createElement("div"); d.innerHTML = `<button class="btn small">→ ${esc(ev.model)}</button>`; d.querySelector("button").onclick = () => send({ type: "control", action: "set_machine", model_id: ev.model_id }); $("log").prepend(d); break; }
    case "toggles": $("tg-assistant").checked = ev.assistant; $("tg-clarify").checked = ev.clarify; break;
    case "summary": renderSummary(ev.summary); break;
    case "error": logLine(ev.text, true); break;
  }
}
const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

function renderTurn(ev) {
  if (!ev.final) { $("partial").textContent = ev.text; return; }
  $("partial").textContent = "";
  $("talk-empty")?.remove();
  let el = $(`turn-${ev.id}`);
  if (!el) { el = document.createElement("div"); el.id = `turn-${ev.id}`; $("turns").appendChild(el); }
  el.className = `turn ${ev.role}${ev.interrupted ? " interrupted" : ""}`;
  const keptClear = el.querySelector(".clear")?.textContent || "";
  const extra = (ev.merged > 1 ? `<span class="merged">${ev.merged} ${L.merged}</span>` : "") + (ev.interrupted ? `<span class="merged">${L.interrupted}</span>` : "") +
    (ev.min_conf < 0.6 ? `<span class="low">${L.lowConf}</span>` : "");
  const wasWaiting = el.querySelector(".clear")?.classList.contains("wait");
  const who = ev.role === "operator" ? L.operator : ev.role === "agent" ? L.agent : L.customer;
  el.innerHTML = `<div class="who">${who}${extra}</div><div class="said">${highlight(ev.text)}</div><div class="clear ${wasWaiting ? "wait" : ""}">${esc(keptClear)}</div>`;
  const box = $("col-talk");
  if (box.scrollHeight - box.scrollTop - box.clientHeight < 200) box.scrollTop = box.scrollHeight;
}

// ------------------------------------------------------------------ procedure
let symptomMenu = [];
function menuSelect(items, placeholder) {
  return items.length ? `<select class="alt"><option value="">${placeholder}</option>${items.map((a) => `<option value="${esc(a.id)}">${esc(a.title)}</option>`).join("")}</select>` : "";
}
function bookingHtml(b) {
  if (!b) return "";
  let body;
  if (b.booked) body = `<div class="booked">✓ ${L.booked}: ${esc(b.booked.label)} · ${esc(b.booked.technician)} ${callMode === "op" ? `<button data-unbook class="btn small ghost">${L.unbook}</button>` : ""}</div>`;
  else if (b.need_serial) body = `<div class="note">${L.needSerial}</div>`;
  else if (b.no_partner) body = `<div class="note">${L.noPartner}</div>`;
  else if (!b.slots.length) body = `<div class="note">${L.noSlots}</div>`;
  else body = `<div class="note">${L.pickSlot} · ${esc(b.slots[0].technician)}</div><div class="slots">${b.slots.map((s) => `<button class="btn small" data-slot="${esc(s.id)}" ${callMode === "voice" ? "disabled" : ""}>${esc(s.label)}</button>`).join("")}</div>`;
  return `<div class="booking"><div class="kind">${b.kind === "onsite" ? L.bookTech : L.bookCall}</div>${body}</div>`;
}
function wireDiag(p) {
  p.querySelectorAll("[data-slot]").forEach((b) => (b.onclick = () => send({ type: "control", action: "book_slot", id: b.dataset.slot })));
  p.querySelectorAll("[data-unbook]").forEach((b) => (b.onclick = () => send({ type: "control", action: "cancel_booking" })));
  p.querySelectorAll("[data-close]").forEach((b) => (b.onclick = () => send({ type: "control", action: "close_symptom", kind: b.dataset.close })));
  p.querySelectorAll("[data-branch]").forEach((b) => (b.onclick = () => send({ type: "control", action: "answer_step", branch: +b.dataset.branch })));
  p.querySelectorAll("[data-start]").forEach((b) => (b.onclick = () => send({ type: "control", action: "start_symptom", symptom_id: b.dataset.start })));
  p.querySelectorAll("[data-drop]").forEach((b) => (b.onclick = () => send({ type: "control", action: "drop_pending", symptom_id: b.dataset.drop })));
  const sel = p.querySelector("select.alt");
  if (sel) sel.onchange = () => { if (sel.value) send({ type: "control", action: "start_symptom", symptom_id: sel.value }); };
}
function renderEmptyDiag() {
  const p = $("diagnosis"); p.className = "panel empty";
  p.innerHTML = `<div>${esc(L.noDiag)}</div>${callMode === "op" ? `<div style="margin-top:10px">${menuSelect(symptomMenu, L.startProc)}</div>` : ""}`;
  wireDiag(p); currentBranches = 0;
}
function partsTable(parts) {
  if (!parts.length) return "";
  const rows = parts.map((c) => {
    const dl = (c.delivery || [])[0];
    const when = dl ? (dl.qty > 0 ? esc(dl.from.replace(/^[A-Z]{2}-\d+ /, "")) : L.fromSupplier) + ", " + dl.days + " " + L.days : "";
    return `<tr><td><span class="code">${esc(c.code)}</span><br>${esc(c.description)}<br><span class="tag ${c.handling === "diy" ? "ok" : "warn"}">${L.handling[c.handling] || ""}</span> <small>${when}</small></td>` +
      `<td>${c.covered_by_warranty ? `<s>${eur(c.price_eur)}</s><br><span class="tag ok">${L.covered}</span>` : eur(c.customer_pays_eur ?? c.price_eur)}</td></tr>`;
  }).join("");
  const total = parts.reduce((a, c) => a + ((c.customer_pays_eur ?? c.price_eur) || 0), 0);
  return `<table class="nparts"><tbody>${rows}</tbody><tfoot><tr><td>${L.totalPays}</td><td>${eur(total)}</td></tr></tfoot></table>`;
}
function renderDiagnosis(d) {
  const p = $("diagnosis"); p.className = "panel";
  const hist = d.history.length ? `<ol class="timeline">${d.history.map((h) => `<li>${esc(h.text)}<br><span class="ans">${esc(h.answer)}</span></li>`).join("")}</ol>` : "";
  const maint = d.maintenance_skipped ? `<div class="maint">⚠ ${L.maintenance} ${d.suggested_parts.map(esc).join(", ")}</div>` : "";
  const head = `<div class="dhead"><h3>${esc(d.symptom)}</h3>${callMode === "op" ? menuSelect(d.alternatives || [], L.change) : ""}</div>`;
  const pend = (d.pending || []).length ? `<div class="pending"><small>${L.pending}</small>${d.pending.map((q) =>
    `<span>${esc(q.title)} <button data-start="${esc(q.id)}" class="btn small ok">${L.startNow}</button><button data-drop="${esc(q.id)}" class="btn small ghost">${L.drop}</button></span>`).join("")}</div>` : "";
  if (d.done) {
    const n = d.next || {};
    p.innerHTML = `${head}${hist}${maint}<div class="outcome ${d.outcome}">${L.outcome[d.outcome]}</div>` +
      `<div class="next"><div class="kind">${L.nextTitle}</div><div>${esc(n.text || "")}</div>` +
      (n.warranty_text ? `<div class="wline ${n.warranty === true ? "ok" : n.warranty === false ? "bad" : ""}">${esc(n.warranty_text)}</div>` : "") +
      partsTable(n.parts || []) + bookingHtml(n.booking) +
      (n.say_en && callMode === "op" ? `<div class="say"><small>${L.say}</small>${esc(n.say_en)}</div>` : "") + `</div>${pend}`;
    wireDiag(p); currentBranches = 0;
    return;
  }
  const s = d.step;
  const branches = callMode === "voice"
    ? `<div class="branches watch">${s.branches.map((b) => `<span class="opt">${esc(b)}</span>`).join("")}</div><div class="watching">${L.watching}</div>`
    : `<div class="branches">${s.branches.map((b, i) => `<button class="btn" data-branch="${i}"><kbd>${i + 1}</kbd> ${esc(b)}</button>`).join("")}</div>`;
  p.innerHTML = `${head}${hist}${maint}<div class="step"><div class="kind">${s.kind === "ask" ? L.ask : L.do}</div><div class="q">${esc(s.text)}</div>` +
    (callMode === "op" ? `<div class="say"><small>${L.say}</small>${esc(s.say_in_english)}</div>` : "") + (s.note ? `<div class="note">${esc(s.note)}</div>` : "") + branches + `</div>` +
    (callMode === "op" ? `<div class="closebar"><span class="note">${L.closeHint} · ${L.keys}</span><button data-close="remote" class="btn small ok">${L.closeRemote}</button><button data-close="technician" class="btn small warn">${L.closeTech}</button></div>` : "") + pend;
  wireDiag(p);
  currentBranches = callMode === "op" ? s.branches.length : 0;
  if (d.doc) followStep(d.doc);
}
let currentBranches = 0;
document.addEventListener("keydown", (e) => {
  if (e.target.matches("input, textarea, select")) return;
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= currentBranches && !$("call").hidden) { send({ type: "control", action: "answer_step", branch: n - 1 }); currentBranches = 0; }
});
function followStep(doc) {
  const i = docs.findIndex((d) => d.page === doc.page);
  if (i < 0) return;
  docs[i].anchor = doc.anchor;
  if (i === activeDoc) applyAnchor(docs[i]); else { docs[i].fresh = true; renderTabs(); }
}
function applyAnchor(d) {
  const v = $("doc-view");
  v.querySelectorAll(".target").forEach((n) => n.classList.remove("target"));
  const head = d.anchor && v.querySelector(`#${CSS.escape(d.anchor)}`);
  if (head) {
    head.classList.add("target");
    const level = +head.tagName[1];
    for (let n = head.nextElementSibling; n && !(/^H[1-6]$/.test(n.tagName) && +n.tagName[1] <= level); n = n.nextElementSibling) n.classList.add("target");
  }
  const focus = v.querySelector("mark") || head;
  if (focus) v.scrollTop = Math.max(0, focus.offsetTop - v.offsetTop - 40);
}
function renderChoice(options) {
  const p = $("diagnosis"); p.className = "panel";
  p.innerHTML = `<h3 style="margin:0">${L.choose}</h3><div class="choice">${options.map((o) => `<button class="btn" data-sym="${esc(o.symptom_id)}">${esc(o.title)} <small>${Math.round(o.score * 100)}%</small></button>`).join("")}</div>`;
  p.querySelectorAll("[data-sym]").forEach((b) => (b.onclick = () => send({ type: "control", action: "start_symptom", symptom_id: b.dataset.sym })));
}

function renderDuet(lines) {
  $("duet-lines").innerHTML = lines.map((l) => `${l.cue ? `<div class="cue op">${esc(l.cue)}</div>` : ""}<button class="duet-line" data-n="${l.n}"><small>${l.n}</small>${esc(l.text)}</button>${l.expect_it ? `<div class="cue expect">${esc(l.expect_it)}</div>` : ""}`).join("");
  $("h-duet").textContent = lang === "it" ? "Cliente registrato: fagli dire…" : "Recorded customer: have them say…";
  $("duet-lines").querySelectorAll(".duet-line").forEach((b) => (b.onclick = () => {
    const n = +b.dataset.n, line = lines.find((x) => x.n === n);
    if (duetPlaying) return;
    duetPlaying = true; micMuted = true;
    new Audio(`/duet-audio/${duetId}/${line.file}`).play().catch(() => {});
    send({ type: "control", action: "play_line", n });
    clearTimeout(micWatchdog);
    micWatchdog = setTimeout(() => { micMuted = false; duetPlaying = false; }, (line.seconds + 4) * 1000);
  }));
}

function renderMachine(m) {
  const box = $("machine-record"); box.hidden = false; box.className = "machine";
  const w = m.in_warranty ? `<span class="tag ok">${L.warranty} ${esc(m.warranty_until)}</span>` : `<span class="tag bad">${L.noWarranty} ${esc(m.warranty_until)}</span>`;
  const orders = (m.orders || []).slice(0, 3).map((o) => `<li>${esc(o.ordered_on)} · <b>${esc(o.code)}</b> ×${o.qty} — ${esc(lang === "it" ? o.description_it : o.description_en)}</li>`).join("");
  box.innerHTML = `<div class="machine-top"><div><h5>${esc(m.model)}${m.edition ? " · Vaniglia" : ""}</h5><div class="serial">#${esc(m.serial)}${m.exact ? "" : ` (${L.serialHeard})`}</div></div>${w}</div>` +
    `<div class="machine-grid"><div><span>${L.customerName}</span><b>${esc(m.customer)}</b></div><div><span>${L.place}</span><b>${esc(m.city)} (${esc(m.country)})</b></div>` +
    `<div><span>${L.built}</span><b>${esc(m.built)}</b></div><div><span>${L.voltage}</span><b>${esc(m.voltage)}</b></div></div>` +
    (m.notes ? `<div class="note">${esc(m.notes)}</div>` : "") + (orders ? `<ul class="orders">${orders}</ul>` : "");
}

// ------------------------------------------------------------------ documents
const KIND = { manual: "📘", symptom: "🩺", part: "🔩" };
async function openDoc(ev) {
  let i = docs.findIndex((d) => d.page === ev.page);
  if (i < 0) { docs.push({ ...ev, fresh: true }); i = docs.length - 1; } else { Object.assign(docs[i], ev, { fresh: true }); }
  if (activeDoc < 0) await showDoc(i); else renderTabs();
}
function renderTabs() {
  $("doc-tabs").innerHTML = docs.map((d, i) => `<div class="doc-tab ${i === activeDoc ? "active" : ""} ${d.fresh && i !== activeDoc ? "fresh" : ""}" data-doc="${i}" title="${esc(d.title)}"><small>${KIND[d.kind] || ""}</small>${esc(d.title)}</div>`).join("");
  $("doc-tabs").querySelectorAll("[data-doc]").forEach((t) => (t.onclick = () => showDoc(+t.dataset.doc)));
}
async function showDoc(i) {
  const d = docs[i]; activeDoc = i; d.fresh = false; renderTabs();
  const q = new URLSearchParams({ page: d.page, lang }); if (d.highlight) q.set("hl", d.highlight);
  const r = await fetch(`/api/docs/render?${q}`).then((x) => x.json()).catch(() => null);
  const v = $("doc-view"); v.className = "doc-view"; v.innerHTML = r ? r.html : "—";
  applyAnchor(d);
}

// ------------------------------------------------------------------ parts
function renderParts() {
  if (!cards.size) return;
  $("parts-empty")?.remove();
  $("parts").innerHTML = [...cards.values()].reverse().map((c) => {
    const where = (c.delivery || []).map((d) => `<span class="chip">${d.qty > 0 ? `${esc(d.from.replace(/^[A-Z]{2}-\d+ /, ""))} · ${d.qty} · ${d.days} ${L.days}` : `${L.fromSupplier} · ${d.days} ${L.days}`}</span>`).join("");
    const flags = [!c.compatible ? L.incompatible : "", c.superseded_by ? `${L.superseded} ${c.superseded_by}${c.requires ? `, ${L.requires} ${c.requires}` : ""}` : ""].filter(Boolean);
    return `<div class="card ${c.status}"><div class="card-top"><div><span class="code">${esc(c.code)}</span><span class="why">${esc(L.reason[c.reason] || L.reason[c.source] || "")}</span></div><span class="price">${eur(c.price_eur)}</span></div>` +
      `<div class="desc">${esc(c.description)}</div><div class="meta"><span class="tag ${c.handling === "diy" ? "ok" : "warn"}">${L.handling[c.handling] || ""}</span>${where}</div>` +
      (flags.length ? `<div class="flag">${flags.map(esc).join(" · ")}</div>` : "") +
      (c.say_en && callMode === "op" ? `<div class="say"><small>${L.sayPart}</small>${esc(c.say_en)}</div>` : "") +
      `<div class="actions">${callMode === "op" ? `<button class="btn small" data-act="confirm_part" data-code="${esc(c.code)}">${L.confirm}</button><button class="btn small ghost" data-act="dismiss_part" data-code="${esc(c.code)}">${L.dismiss}</button>` : (c.status === "confirmed" ? `<span class="tag ok">✓ ${L.stConfirmed}</span>` : "")}<button data-sheet="${esc(c.code)}" class="btn small ghost">${L.sheet}</button></div></div>`;
  }).join("");
  $("parts").querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => send({ type: "control", action: b.dataset.act, code: b.dataset.code })));
  $("parts").querySelectorAll("[data-sheet]").forEach((b) => (b.onclick = () => {
    const c = cards.get(b.dataset.sheet);
    openDoc({ kind: "part", page: `parts/${b.dataset.sheet}.md`, anchor: "montaggio", title: `${b.dataset.sheet} — ${c ? c.description : ""}`, highlight: null });
  }));
}

// ------------------------------------------------------------------ report (work order)
function renderSummary(s) {
  $("call").hidden = true; $("topbar").hidden = false; $("summary").hidden = false;
  const now = new Date();
  const woNum = `SR-${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}-${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}`;
  const kind = s.outcome ? s.outcome.kind : null;
  const m = s.machine_record || {};
  const warranty = m.warranty_until ? (m.in_warranty ? `<span class="tag ok">${L.warranty} ${esc(m.warranty_until)}</span>` : `<span class="tag bad">${L.noWarranty} ${esc(m.warranty_until)}</span>`) : "—";
  const steps = s.steps.length ? `<ol class="timeline">${s.steps.map((h) => `<li>${esc(h.text)}<br><span class="ans">${esc(h.answer)}</span></li>`).join("")}</ol>` : `<p class="note">${L.noSteps}</p>`;
  const stOf = (p) => (p.compatible === false ? "incompatible" : p.in_outcome === false ? "mentioned" : "proposed");
  const all = [...s.parts_confirmed.map((p) => ({ ...p, st: "confirmed" })), ...(s.parts_proposed || []).map((p) => ({ ...p, st: stOf(p) }))];
  const stTag = { confirmed: ["ok", L.stConfirmed], proposed: ["warn", L.stProposed], mentioned: ["", L.stMentioned], incompatible: ["bad", L.stIncompatible] };
  const pays = (p) => (p.customer_pays_eur == null ? p.price_eur : p.customer_pays_eur);
  const partsRows = all.map((p) => `<tr><td class="code">${esc(p.code)}</td><td>${esc(p.description)}${p.why === "consumable" ? `<br><small class="note">${L.consumable}</small>` : ""}</td>` +
    `<td><span class="tag ${stTag[p.st][0]}">${stTag[p.st][1]}</span></td><td class="num">${eur(p.price_eur)}</td>` +
    `<td class="num">${p.st === "incompatible" ? "—" : p.covered_by_warranty ? `<span class="tag ok">${L.covered}</span>` : eur(pays(p))}</td></tr>`).join("");
  const total = s.parts_confirmed.reduce((a, p) => a + (pays(p) || 0), 0);
  const partsTbl = all.length ? `<table class="rtable"><thead><tr><th>${L.thCode}</th><th>${L.thDesc}</th><th>${L.thStatus}</th><th class="num">${L.thPrice}</th><th class="num">${L.thPays}</th></tr></thead><tbody>${partsRows}</tbody>` +
    `<tfoot><tr><td colspan="4">${L.totalPays}</td><td class="num">${eur(total)}</td></tr></tfoot></table>` : `<p class="note">${L.none}</p>`;
  const diar = s.diarization_check ? `${Math.round((s.diarization_check.accuracy || 0) * 100)}%` : null;
  const transcript = s.transcript.map((t) => `<div class="turn ${t.role}${t.interrupted ? " interrupted" : ""}"><div class="who">${t.role === "operator" ? L.operator : t.role === "agent" ? L.agent : L.customer}</div>${esc(t.text)}${t.clear ? `<div class="clear">${esc(t.clear)}</div>` : ""}</div>`).join("");
  const hasOrder = s.parts_confirmed.length || s.booking;
  $("summary").innerHTML = `<article class="report">
    <div class="report-head"><div><div class="wo">${L.wo} · ${woNum}</div><h2>${esc(s.symptom || L.reportFor)}</h2>
      <div class="note">${now.toLocaleString(lang === "it" ? "it-IT" : "en-GB")} · ${L.duration} ${fmt(s.duration_s || 0)}${diar ? ` · ${L.diarCheck} ${diar}` : ""}</div></div>
      <div class="outcome ${kind || ""}">${kind ? L.outcome[kind] : L.noOutcome}</div></div>
    <div class="report-body">
      <section class="report-sec"><h4>${L.secMachine}</h4><dl class="kv">
        <dt>${L.machine}</dt><dd>${esc(s.machine || "—")}${s.edition ? " · Vaniglia" : ""}</dd><dt>${L.serial}</dt><dd>${esc(s.serial || "—")}</dd>
        <dt>${L.customerName}</dt><dd>${esc(m.customer || "—")}</dd><dt>${L.place}</dt><dd>${m.city ? `${esc(m.city)} (${esc(m.country)})` : "—"}</dd>
        <dt>${L.warrantyLbl}</dt><dd>${warranty}</dd></dl></section>
      <section class="report-sec"><h4>${L.secNext}</h4><dl class="kv">
        <dt>${L.nextStep}</dt><dd>${esc(s.next ? s.next.text : "—")}${s.next && s.next.warranty_text ? `<br><small>${esc(s.next.warranty_text)}</small>` : ""}</dd>
        <dt>${L.appointment}</dt><dd>${s.booking ? `${esc(s.booking.label)} · ${esc(s.booking.technician)}` : (["part_with_support", "technician"].includes(kind) ? `<span class="tag bad">${L.notBooked}</span>` : "—")}</dd></dl></section>
      <section class="report-sec wide"><h4>${L.secDiag}</h4>${steps}</section>
      <section class="report-sec wide"><h4>${L.secParts}</h4>${partsTbl}</section>
      ${(s.notes || []).length ? `<section class="report-sec wide"><h4>${L.secNotes}</h4><ul>${s.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></section>` : ""}
    </div>
    <details><summary>${L.showTranscript} (${s.transcript.length})</summary><div class="turns">${transcript}</div></details>
    <div class="report-actions"><span class="approved" id="approved" hidden>✓ ${L.approved}</span>
      ${hasOrder ? `<button class="btn primary" id="btn-approve">${L.approve}</button>` : ""}
      <button class="btn" id="btn-print">${L.print}</button><button class="btn" id="btn-again">${L.again}</button></div>
  </article>`;
  $("btn-approve")?.addEventListener("click", () => { $("approved").hidden = false; $("btn-approve").remove(); toast(L.toastApproved); });
  $("btn-print").onclick = () => window.print();
  $("btn-again").onclick = () => location.reload();
  window.scrollTo(0, 0);
}
function toast(text) { const t = $("toast"); t.textContent = text; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => (t.hidden = true), 3500); }
function logLine(text, bad, at) {
  const d = document.createElement("div"); if (bad) d.className = "err";
  d.innerHTML = `${at != null ? `<time>${fmt(at)}</time>` : ""}${esc(text)}`;
  $("log").prepend(d);
  if (bad) toast(text.slice(0, 140));
}

// ------------------------------------------------------------------ AssemblyAI Voice Agent
// The hosted agent listens and talks over its own socket; this page relays its transcripts and tool calls to our
// server (memory, procedures, parts, calendar) and the results back.
let vws = null, vCtx = null, vStream = null, vNext = 0, vSources = [], vEndPending = false;
async function startVoice(persona) {
  const rp = !!persona;
  startCall(rp ? `roleplay:${persona}` : "voice");
  vEndPending = false; rpSpoke = false;
  let agent, tok;
  try {
    agent = await fetch(rp ? `/api/voice/customer?persona=${encodeURIComponent(persona)}` : `/api/voice/agent?lang=${encodeURIComponent($("voice-lang").value || "en")}`).then((r) => r.json());
    tok = await fetch("/api/voice/token").then((r) => r.json());
  } catch (e) { logLine("voice agent: " + e.message, true); return; }
  if (!agent.session || !tok.token) { logLine("voice agent: " + JSON.stringify(agent.detail || tok.detail || agent), true); return; }
  const url = new URL("wss://agents.assemblyai.com/v1/ws"); url.searchParams.set("token", tok.token);
  vws = new WebSocket(url.toString());
  vws.onopen = () => { vws.send(JSON.stringify({ type: "session.update", session: agent.session })); };
  vws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    switch (m.type) {
      case "session.ready": $("st-session").textContent = L.open; $("live-dot").classList.add("on"); startVoiceMic(); break;
      case "transcript.user": if (rp) rpSpoke = true; send({ type: "control", action: "transcript", role: rp ? "operator" : "customer", text: m.text }); break;
      case "transcript.agent": send({ type: "control", action: "transcript", role: rp ? "customer" : "agent", text: m.text, interrupted: !!m.interrupted }); break;
      case "reply.audio": voicePlay(m.data || m.audio); break;
      case "reply.done":
        if (m.status === "interrupted") voiceStop();
        if (vEndPending) { const left = vCtx ? Math.max(0, vNext - vCtx.currentTime) : 0; setTimeout(voiceEnd, left * 1000 + 800); }
        break;
      case "tool.call": send({ type: "control", action: "tool", call_id: m.call_id, name: m.name, arguments: m.arguments }); logLine("⚙ " + m.name + " " + JSON.stringify(m.arguments || {})); break;
      case "session.error": case "error": logLine("voice agent: " + (m.message || m.code || e.data), true); break;
      case "session.ended": logLine(`voice agent: ${Math.round(m.audio_duration_seconds || 0)} s`); vws.close(); break;
    }
  };
  vws.onclose = () => { stopVoiceMic(); vws = null; send({ type: "control", action: "voice_end" }); };
}
function voiceToolResult(ev) {
  if (!vws || vws.readyState !== 1) return;
  vws.send(JSON.stringify({ type: "tool.result", call_id: ev.call_id, result: ev.result, is_error: false }));
  if (ev.end) { vEndPending = true; setTimeout(voiceEnd, 15000); }
}
function voiceEnd() {
  if (duo) { duoEnd(); return; }
  if (vws && vws.readyState === 1) { try { vws.send(JSON.stringify({ type: "session.end" })); } catch (e) { /* closing */ } }
}
async function startVoiceMic() {
  try {
    vStream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  } catch (e) {
    $("st-mic").textContent = e.name === "NotAllowedError" ? L.micDenied : e.message; $("st-mic").classList.add("bad"); setPresence("denied"); return;
  }
  vCtx = new AudioContext({ sampleRate: 24000 });
  await vCtx.resume();
  await vCtx.audioWorklet.addModule("/static/worklet.js");
  const node = new AudioWorkletNode(vCtx, "pcm16-downsampler", { processorOptions: { rate: 24000 } });
  const silence = btoa(String.fromCharCode.apply(null, new Uint8Array(2400)));
  node.port.onmessage = (e) => {
    // half duplex: while the agent's voice is still playing (plus a short tail) the customer is not heard
    const agentTalking = vCtx && vCtx.currentTime < vNext + 0.35;
    const bytes = new Uint8Array(e.data); let bin = "";
    for (let i = 0; i < bytes.length; i += 0x2000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x2000));
    if (vws && vws.readyState === 1) vws.send(JSON.stringify({ type: "input.audio", audio: agentTalking ? silence : btoa(bin) }));
    const pcm = new Int16Array(e.data); let peak = 0;
    for (let i = 0; i < pcm.length; i += 8) { const v = Math.abs(pcm[i]); if (v > peak) peak = v; }
    const pill = $("st-mic");
    pill.textContent = agentTalking ? L.agentTalking : "mic";
    pill.classList.toggle("on", !agentTalking && peak > 1500); pill.classList.toggle("hold", agentTalking);
    setMeter(agentTalking ? 0 : peak, agentTalking ? "hold" : peak > 1500 ? "hot" : "");
    setPresence(agentTalking ? "speaking" : "listening");
  };
  vCtx.createMediaStreamSource(vStream).connect(node);
}
function stopVoiceMic() { if (vStream) vStream.getTracks().forEach((t) => t.stop()); if (vCtx) vCtx.close(); vStream = vCtx = null; }
function voicePlay(b64) {
  if (!vCtx || !b64) return;
  const bin = atob(b64); const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const pcm = new Int16Array(bytes.buffer); const f32 = new Float32Array(pcm.length);
  for (let i = 0; i < pcm.length; i++) f32[i] = pcm[i] / 32768;
  const buf = vCtx.createBuffer(1, f32.length, 24000); buf.getChannelData(0).set(f32);
  const src = vCtx.createBufferSource(); src.buffer = buf; src.connect(vCtx.destination);
  const at = Math.max(vCtx.currentTime + 0.05, vNext); src.start(at); vNext = at + buf.duration;
  vSources.push(src); src.onended = () => { vSources = vSources.filter((s) => s !== src); };
}
function voiceStop() { vSources.forEach((s) => { try { s.stop(); } catch (e) { /* already done */ } }); vSources = []; vNext = 0; }

// ------------------------------------------------------------------ two AIs talking (no microphone)
// A = the Sereni assistant (Cardex's tools), B = the simulated customer. Each agent's voice is played on the speakers and
// streamed into the other agent at real-time pace (50 ms frames); silence fills the gaps so turn detection works.
let duo = null;
const FRAME = 2400;                                    // 50 ms of PCM16 at 24 kHz
const b64ToBytes = (b64) => { const s = atob(b64); const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u; };
const bytesToB64 = (u) => { let s = ""; for (let i = 0; i < u.length; i += 0x2000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x2000)); return btoa(s); };
async function startDuo() {
  const p = PERSONAS.find((x) => x.id === persona);
  if (!p || p.id === "free") { toast(L.duoPickCustomer); return; }
  startCall("voice");
  $("call-mode").textContent = L.modeDuo; $("call").classList.add("duo");
  vEndPending = false;
  const ctx = new AudioContext({ sampleRate: 24000 }); await ctx.resume().catch(() => {});
  duo = { ctx, next: 0, sockets: {}, queues: { A: [], B: [] }, carry: { A: new Uint8Array(0), B: new Uint8Array(0) }, ready: { A: false, B: false }, sent: { A: 0, B: 0 }, heard: { A: 0, B: 0 }, timer: null, speaking: "", ended: false };
  window.cardexDuo = () => ({ ready: duo.ready, queued: { A: duo.queues.A.length, B: duo.queues.B.length }, sent: duo.sent, audioFrom: duo.heard });
  let a, b, ta, tb;
  try {
    [a, b, ta, tb] = await Promise.all([
      fetch(`/api/voice/agent?lang=${encodeURIComponent(p.lang || "en")}`).then((r) => r.json()),
      fetch(`/api/voice/customer?persona=${encodeURIComponent(p.id)}`).then((r) => r.json()),
      fetch("/api/voice/token").then((r) => r.json()), fetch("/api/voice/token").then((r) => r.json())]);
  } catch (e) { logLine("duo: " + e.message, true); return; }
  const open = (who, token, session) => {
    const url = new URL("wss://agents.assemblyai.com/v1/ws"); url.searchParams.set("token", token);
    const ws = new WebSocket(url.toString()); duo.sockets[who] = ws;
    if (who === "A") vws = ws;                               // tool results and the hang-up go to the assistant
    const other = who === "A" ? "B" : "A";
    ws.onopen = () => ws.send(JSON.stringify({ type: "session.update", session }));
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.type === "session.ready") {
        duo.ready[who] = true;
        if (who === "B") open("A", ta.token, a.session);        // the customer listens first, then the assistant greets
      } else if (m.type === "reply.audio") {
        duo.heard[who]++;
        const bytes = b64ToBytes(m.data || m.audio);
        duoPlay(bytes, who);
        duoFeed(other, bytes);                                        // the other agent hears it as one continuous stream
      } else if (m.type === "reply.done") {
        duoFeed(other, null);                                         // flush the tail of the sentence
        if (who === "A" && vEndPending) setTimeout(duoEnd, Math.max(0, duo.next - duo.ctx.currentTime) * 1000 + 800);
      } else if (m.type === "transcript.agent") {
        send({ type: "control", action: "transcript", role: who === "A" ? "agent" : "customer", text: m.text, interrupted: !!m.interrupted });
      } else if (m.type === "tool.call" && who === "A") {
        send({ type: "control", action: "tool", call_id: m.call_id, name: m.name, arguments: m.arguments });
        logLine("⚙ " + m.name + " " + JSON.stringify(m.arguments || {}));
      } else if (m.type === "session.error" || m.type === "error") {
        logLine(`duo ${who}: ` + (m.message || m.code || e.data), true);
      }
    };
    ws.onclose = () => { if (!duo || duo.ended) return; duoEnd(); };
  };
  open("B", tb.token, b.session);
  $("st-session").textContent = L.open; $("live-dot").classList.add("on");
  const silence = bytesToB64(new Uint8Array(FRAME));
  duo.timer = setInterval(() => {
    for (const who of ["A", "B"]) {
      const ws = duo.sockets[who];
      if (!ws || ws.readyState !== 1 || !duo.ready[who]) continue;          // frames wait in the queue until the session is ready
      const q = duo.queues[who].shift(); if (q) duo.sent[who]++;
      ws.send(JSON.stringify({ type: "input.audio", audio: q || silence }));
    }
    const talking = duo.ctx.currentTime < duo.next ? duo.speaking : "";
    setPresence(talking === "A" ? "speaking" : talking === "B" ? "customer" : "listening");
  }, 50);
}
// audio arrives in chunks of any size: keep a running buffer per listener and cut exact 50 ms frames from it, so the
// listener hears continuous speech (padding every chunk to a frame would insert gaps and garble it)
function duoFeed(to, bytes) {
  let buf = duo.carry[to];
  if (bytes) { const n = new Uint8Array(buf.length + bytes.length); n.set(buf); n.set(bytes, buf.length); buf = n; }
  let i = 0;
  for (; i + FRAME <= buf.length; i += FRAME) duo.queues[to].push(bytesToB64(buf.subarray(i, i + FRAME)));
  buf = buf.subarray(i);
  if (!bytes && buf.length) { const f = new Uint8Array(FRAME); f.set(buf); duo.queues[to].push(bytesToB64(f)); buf = new Uint8Array(0); }
  duo.carry[to] = buf;
}
function duoPlay(bytes, who) {
  const pcm = new Int16Array(bytes.buffer, 0, bytes.length >> 1); const f32 = new Float32Array(pcm.length);
  for (let i = 0; i < pcm.length; i++) f32[i] = pcm[i] / 32768;
  const buf = duo.ctx.createBuffer(1, f32.length, 24000); buf.getChannelData(0).set(f32);
  const src = duo.ctx.createBufferSource(); src.buffer = buf; src.connect(duo.ctx.destination);
  const at = Math.max(duo.ctx.currentTime + 0.05, duo.next); src.start(at); duo.next = at + buf.duration; duo.speaking = who;
}
function duoEnd() {
  if (!duo || duo.ended) return;
  duo.ended = true; clearInterval(duo.timer);
  for (const ws of Object.values(duo.sockets)) { try { if (ws.readyState === 1) ws.send(JSON.stringify({ type: "session.end" })); ws.close(); } catch (e) { /* closing */ } }
  setTimeout(() => { try { duo.ctx.close(); } catch (e) { /* closed */ } }, 1500);
  vws = null;
  send({ type: "control", action: "voice_end" });
}

// the edge-tts automatic assistant (superseded by the Voice Agent, kept for the headless tests)
function speak(ev) {
  const el = document.createElement("div"); el.className = "turn agent";
  el.innerHTML = `<div class="who">${L.agent}</div><div class="said">${esc(ev.text)}</div>`;
  $("talk-empty")?.remove(); $("turns").appendChild(el);
  micMuted = true;
  const a = new Audio(ev.url);
  let done = false;
  const finish = () => { if (done) return; done = true; clearTimeout(micWatchdog); setTimeout(() => { micMuted = false; send({ type: "control", action: "spoken" }); }, 250); };
  a.onended = finish; a.onerror = finish; a.play().catch(finish);
  clearTimeout(micWatchdog); micWatchdog = setTimeout(finish, (ev.seconds + 6) * 1000);
}

// ------------------------------------------------------------------ wiring
$("btn-sample").onclick = () => startCall(`sample:${$("sample-select").value}`);
$("btn-mic").onclick = () => startCall("mic");
$("btn-duet").onclick = () => startCall(`duet:${$("duet-select").value}`);
$("btn-voice").onclick = () => startVoice();
$("btn-roleplay").onclick = () => startVoice($("rp-select").value);
$("btn-duo").onclick = () => startDuo();
$("btn-end").onclick = () => { voiceEnd(); send({ type: "control", action: "end_call" }); };
$("btn-swap").onclick = () => send({ type: "control", action: "swap_roles" });
$("tg-clarify").onchange = (e) => send({ type: "control", action: "toggle", what: "clarify", on: e.target.checked });
$("tg-assistant").onchange = (e) => send({ type: "control", action: "toggle", what: "assistant", on: e.target.checked });
$("btn-lang").onclick = () => { lang = lang === "it" ? "en" : "it"; applyLanguage(); loadHomeData(); };
$("sheet-close").onclick = () => $("sheet").close();
applyLanguage(); loadHomeData();
