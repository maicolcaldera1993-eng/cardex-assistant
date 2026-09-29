# Cardex Assistant

First-line service for an espresso machine maker (Sereni, Florence, fictional), built on AssemblyAI's Voice Agent API.
A barista abroad calls because the machine is misbehaving; Cardex recognises the machine and the fault, walks the
customer through the maker's own troubleshooting procedure step by step, finds the right spare part in the ERP, tells
who pays under warranty and what it costs, books the service call, and leaves a work order a human approves before
anything is ordered.

**Live demo:** https://cardex-production-4a67.up.railway.app

Built solo for the [AssemblyAI Voice Agent Hackathon](https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon) (lablab.ai, September 2026).

## Try it

The page has three ways in, all with the same knowledge base:

- **Mode 1 · Automatic assistant** (you are the customer). Pick one of the sample customers, read their sheet, press
  *Call the service desk* and describe the problem. The assistant starts in English and switches to Italian, Spanish,
  German, French or Portuguese if you speak one of them. **Wearing headphones? Turn on 🎧 Headphones** in the call bar:
  the microphone stays open, you can pause mid-sentence and talk over the agent to stop it. With laptop speakers leave
  it off (the agent would hear its own voice).
- **Listen to a call** (no microphone). The same assistant answers the selected customer, played by a second AI agent.
- **Mode 2 · Operator assist** (you are the operator). An AI customer (Luca, Dave, Klaus or Carmen) calls with a real
  fault; you answer on the microphone and Cardex listens to both sides. The console gives the operator the same tools
  the automatic assistant has: the procedure at the right step with the sentence to read, the answers to click, parts
  with price and delivery, warranty and who pays, the service or technician calendar, "the customer fits the parts
  alone", "the customer wants the technician", a line on how to keep the fault from coming back, and the work order.
  It points out what the customer says that matters: a refusal to open the machine, a request for a technician, a
  serial with digits missing.

Every call ends with a work order: outcome, machine and warranty, the checks done, parts with what the customer pays,
shipping, the service call, the appointment, the email the quote goes to, and notes for the operator.

The public demo has limits so that nobody can spend the owner's credits: two calls at a time, ten minutes per call,
a daily budget of agent minutes and ten calls per hour per address (`app/limits.py`, set from environment variables).

## How AssemblyAI is used

| Capability | Where |
|---|---|
| Voice Agent API (`agents.assemblyai.com`), configured inline per session | the automatic assistant (Mode 1) and the simulated customer (Mode 2 and the two-AI call) |
| Client-side function tools (`type: "function"`) relayed by the browser | 11 tools: identify the machine, find and follow the procedure, parts, booking, email, call status, notes, end of call |
| `language_codes`, `transcription_prompt`, key terms | listening limited to the six languages the agent speaks, domain context, machine names and part codes |
| `conversation.message` + `reply.create` | language handover: a new session with the customer's language voice gets the call so far and answers the last words |
| Semantic turn detection (default) and `transcription_mode: "max_accuracy"` | the customer can pause while spelling or thinking without being cut off; fewer turns split in the middle of a sentence |
| Temporary tokens (`/v1/token`) | the browser never sees the API key |
| LLM Gateway | English subtitles for lines said in another language |

## Architecture

```
browser ── mic/speaker ──► AssemblyAI Voice Agent (listens, talks)
   │                              │ tool.call
   │  transcripts, tool calls     ▼
   └────────── WebSocket ───► Cardex server (FastAPI)
                                 ├─ procedures: data/kb/defects/*.json (closed graphs: ask/do steps → outcomes)
                                 ├─ ERP: data/sereni.db (parts, stock, prices, installed base, warranty, calendar)
                                 ├─ documents: manuals, symptom pages, part sheets (anchored sections)
                                 └─ guard rails: every answer checked against the customer's own words
```

The agent converses freely, but every fact and every decision comes from Cardex through tools. It can only ask what
the current step asks; the server accepts an answer only if the customer's words match one of the step's options.

## Architecture decisions

Recorded as they were made. The first version (operator assist over Universal-3.5 Pro streaming with speaker labels)
was replaced by the Voice Agent on 24–26 September; its decisions stay here as history.

- **2026-09-16** Browser never talks to AssemblyAI with the API key: the backend owns the key, the limits and the logic.
- **2026-09-16** Pure logic (normaliser, catalog search, context, vocabulary, procedures) lives in `app/core/` with no network access and is covered by pytest before any audio is involved.
- **2026-09-16** Streaming spike (`eval/spike_*.py`): six synthetic voices × three configs. Without keyterms the model missed 16 of 30 model mentions and 14 of 48 codes; with `keyterms_prompt` it missed 2 and 3, with keyterms plus a prompt 1 and 6. "Onda" became "Honda" in 4 of 6 bare runs, 2 of 6 with keyterms, 1 of 6 with keyterms plus prompt (`eval/spike_results/`).
- **2026-09-16** Known-defects files are step-by-step procedures, not lists of causes: each symptom is a small flowchart (ask/do steps, each answer branches to the next step or to an outcome: remote fix, part the customer fits, part fitted with service support, technician). The assistant never decides an outcome by itself.
- **2026-09-16** Pronunciation knowledge lives in `app/lexicon/pronunciation.json`, owned by Cardex. The ERP holds only business data.
- **2026-09-16** Knowledge base is structured, not a vector store: `data/sereni.db`, `data/kb/defects/*.json`, `data/kb/manuals/*.md`, `data/kb/parts/*.md`.
- **2026-09-17** LLM Gateway on a free account: only `qwen3.5-4b-32k-fast`, 2 requests per minute (`eval/probe_gateway_rate.py`). Subtitles are batched and never block the call.
- **2026-09-18** Three layers of understanding. (1) Exact words: model names and part codes are closed sets. (2) Meaning: a local multilingual sentence-embedding model (`paraphrase-multilingual-MiniLM-L12-v2`, CPU) maps a fault described in any language onto a known symptom, above a threshold and only among the candidates the graph allows. (3) Reading the whole conversation with an LLM: probed, parked.
- **2026-09-18** Documents are a graph: every page is cut into anchored sections that know which machines they belong to (`data/kb/index.json`). Near-identical part sheets (230 V vs 110 V element) make plain RAG unsafe for spare parts.
- **2026-09-22** Meaning is read only on complete sentences, and a symptom must beat a generic "decoy" node by a margin. Decisions are logged for tracing.
- **2026-09-22** The serial number opens the installed-base record: model, build year, warranty, previous orders, contact email. Tolerant to one mis-heard digit, with confirmation.
- **2026-09-23** While a step is open, what the customer says is an answer, not a new fault; a second fault waits in a queue. The closed procedure shows what to do next: parts with price and delivery, who pays, a two-week service calendar.
- **2026-09-24** Voice Agent API. Configured inline per session (a stored `agent_id` cannot be combined with per-session tools). The browser holds both sockets and relays tool calls, so no public webhook is needed. Guard rails are server-side and deterministic: `answer_step` is accepted only if the customer's words match an option of the current step (numbers said in words, yes/no, on/off pairs, negations, "still"/"now it works", shared words, meaning, in several languages); `end_call` is refused while a step is open, while the outcome's parts are undecided, or before a goodbye.
- **2026-09-24** Sentence vectors of the index are cached on disk (`data/kb/index.vectors.npz`) and built into the Docker image.
- **2026-09-25** Commercial terms are data (`app/core/terms.py`): service call, technician, shipping inside and outside the EU, warranty coverage and exclusions. Payment is never taken on the call: a colleague emails the quote, parts ship on payment.
- **2026-09-25** The assistant follows the customer's language: a Voice Agent voice is fixed per session, so the page hands the call to a new session with that language's voice, replaying the call so far and its state.
- **2026-09-26** Turn detection left on AssemblyAI's semantic default: fixed silence rules cut the customer's sentences. The page holds the microphone back while the agent's voice plays (half duplex). Letting a loud voice interrupt the agent was tried and removed: laptop speakers' echo triggered it and the agent kept restarting its sentence.
- **2026-09-26** The customer's email is on file with the installed base; dictating addresses letter by letter over a call proved unreliable. A new address goes through a dedicated tool and must appear in the customer's own words.
- **2026-09-26** Diagnosis from AssemblyAI's own session recordings (`eval/session_fetch.py`, `eval/session_check.py`): the audio arrived whole, so the errors were live transcription or our logic. Tool results are sent only once the agent's reply is done (and dropped if it was interrupted), which stopped two replies starting together; `max_accuracy` transcription took duplicated replies in a synthetic A/B from 3 to 0.
- **2026-09-26** The price list is in the ERP (`service_prices`): service video call 35 €, technician call-out 80 €, shipping 9.90 € in the EU and 29 € outside, all free under warranty. A customer who can take the machine apart does it live with the agent; one who cannot or will not gets the technician, who brings the part.
- **2026-09-28** Eight test calls analysed one by one from AssemblyAI's recordings, each defect replayed as a test. The customer's words, not the agent's summary, choose the procedure ("it stays cold… it seems dead" was summarised as "the machine is dead"), and the latest words can move to another procedure once the customer confirms. Answers are read in their own language. A refusal ("I'm afraid to open it") or a request for a technician is read on the customer's sentence and closes the step even if the agent forgets to. The outcome is told once, in short turns. Slots are offered by part of the day. Each step asks one question.
- **2026-09-28** The page hangs up after the goodbye has been played, not after the reply that asked to close. With headphones the half duplex is switched off: the mic stays open and AssemblyAI's barge-in stops the agent, so a customer who pauses mid-sentence is no longer cut off.
- **2026-09-29** The listening set-up measured on the final product (`eval/keyterms_ab.py`, results in `eval/keyterms_ab_results.json`): the six accented spike recordings streamed into the Voice Agent with Cardex's key terms and transcription prompt, and without. Machine names heard right: 28 of 30 against 16 of 30; "Onda" heard as Onda in 4 of 6 recordings against 2. Part codes: 34 of 48 against 33, no gain, because codes are not among the key terms (adding the codes of the machine in the call is the next step); the synthetic Turkish voice loses most codes either way.
- **2026-09-28** Mode 2 gets the agent's tools: the operator console offers every decision the agent can take (technician instead of fitting, check-up visit after a remote fix, parts asked for in passing, prevention advice), and Cardex points out when the customer's words call for one. A check-up visit with the machine working is charged at list price even under warranty: there is nothing to repair.

## Running locally

```
python -m venv .venv          # Python 3.12
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env        # then fill in ASSEMBLYAI_API_KEY
uvicorn app.main:app
python -m pytest -q
```

The Docker image (`Dockerfile`) is what runs on Railway: the embedding model and the vector cache are built into it.

Rebuilding the knowledge base after editing the data scripts:

```
python data/build_db.py        # ERP, part sheets, lexicon
python data/build_manuals.py   # manuals for every model except the hand-written Marea 2 Plus
python data/build_wiki.py      # symptom pages and the section index
```

Checks in `eval/` (the ones that call AssemblyAI cost a few cents of agent time):

| Script | What it does |
|---|---|
| `ws_voice.py 8000 dave\|lena\|mario` | a synthetic customer calls the automatic assistant through the real Voice Agent |
| `ws_roleplay.py 8000 klaus\|luca` | a synthetic operator talks to the simulated customer |
| `keyterms_ab.py` | streams the six accented recordings into the Voice Agent with and without Cardex's key terms and prompt, and scores the machine names and part codes heard |
| `session_fetch.py` | lists AssemblyAI sessions and downloads one: stereo audio (customer left, agent right), timeline with confidences and tool calls |
| `session_check.py` | transcribes the customer's channel afterwards and compares it with what was understood live |
| `probe_gateway_rate.py` | measures how many LLM Gateway requests per minute the account accepts |
| `spike_*.py`, `make_spike_audio.py` | historical: the 16 September streaming spike quoted above |

## Tests

`python -m pytest -q` runs 268 tests in about a minute, with no microphone and no AssemblyAI credits (the first run
downloads the embedding model, about 200 MB).
They check Cardex's own side of the call: rules, data and decisions. What the agent says is produced by AssemblyAI's
model and is not deterministic; that is checked with live calls and with the headless checks above.

| File | Tests | What it guarantees |
|---|---|---|
| `test_voice_tools.py` | 72 | The agent's tools and guard rails, the operator console's decisions, costs and warranty, email, language handover, replays of live test calls |
| `test_normalizer.py` | 39 | Spoken part codes come back in canonical form ("e L3010" → EL-3010, "G E twenty-one forty" → GE-2140) |
| `test_defects_files.py` | 34 | Every procedure is a closed graph over the ERP: each answer leads to a step or an outcome, each part exists and fits, no step is unreachable, every model is covered |
| `test_semantic.py` | 31 | A fault described in eight languages reaches the right procedure; small talk and half sentences open nothing |
| `test_context_catalog.py` | 25 | Machine recognition, part search, serial numbers with one wrong digit, the service calendar |
| `test_symptoms_vocab.py` | 19 | Procedures and outcomes, answers not mistaken for new faults, the key terms within the session limits |
| `test_manuals.py` | 20 | A manual per model in both languages, with shared anchors and only compatible parts |
| `test_dialog.py` | 23 | Reading an answer: numbers said in words, yes/no, on/off, negations, serials, emails, language |
| `test_limits.py` | 5 | The public demo limits and the token that waits for its call |

Every defect found in a live call becomes a test that replays that moment, named after the call in its docstring:
the warranty covers the repair's parts but never consumables; "I think it's dirty" cannot answer "how old is the
gasket?"; "Goodbye." never replaces a finished procedure; a serial said twice in one sentence is still one serial;
an email spelled letter by letter is recorded, an invented one is not; "I'm afraid to open it, can someone come?"
brings the technician with the valve; "it seems dead" does not open "machine dead" when the customer also said the
lights are on; the email on file keeps its dashes when it is read back without them.

## Future work

Known debt, left alone before the deadline because it works and is covered by tests:

- `CallSession` (`app/session.py`) and the tool handler in `app/voice/agent.py` are long; they would split into
  smaller units (machine record, costs and booking, closing rules).
- The page opens the Voice Agent socket in two places (one agent, and the two-AI call); one shared helper would do.
- `test_voice_tools.py` would split by topic (procedure, costs, email, language, end of call).
- Accessibility of the call screen (live regions for the transcript, keyboard order) has not been reviewed.
- A reply started while a tool call is pending can still overlap with the next one when the customer talks over it.
- With laptop speakers the half duplex stays on, so a sentence paused mid-way can still lose its end; headphones
  mode avoids it. Real echo cancellation would make full duplex safe on speakers too.
- In Mode 1 the agent switches to a technician's visit on its own after a parts outcome, not yet to a check-up visit
  after a remote fix (the Mode 2 console offers both).

## License

MIT
