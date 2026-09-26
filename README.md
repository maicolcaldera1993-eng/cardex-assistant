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
  German, French or Portuguese if you speak one of them.
- **Listen to a call** (no microphone). The same assistant answers the selected customer, played by a second AI agent.
- **Mode 2 · Operator assist** (you are the operator). An AI customer calls with a real fault; you answer on the
  microphone and Cardex listens to both sides: it opens the procedure at the right step with the sentence to read,
  finds parts, warranty and a slot, and prepares the work order.

Every call ends with a work order: outcome, machine and warranty, the checks done, parts with what the customer pays,
shipping, the service call, the appointment, the email the quote goes to, and notes for the operator.

The public demo has limits so that nobody can spend the owner's credits: two calls at a time, ten minutes per call,
a daily budget of agent minutes and a few calls per hour per address (`app/limits.py`, set from environment variables).

## How AssemblyAI is used

| Capability | Where |
|---|---|
| Voice Agent API (`agents.assemblyai.com`), configured inline per session | the automatic assistant (Mode 1) and the simulated customer (Mode 2 and the two-AI call) |
| Client-side function tools (`type: "function"`) relayed by the browser | 11 tools: identify the machine, find and follow the procedure, parts, booking, email, call status, notes, end of call |
| `language_codes`, `transcription_prompt`, key terms | listening limited to the six languages the agent speaks, domain context, machine names and part codes |
| `conversation.message` + `reply.create` | language handover: a new session with the customer's language voice gets the call so far and answers the last words |
| Semantic turn detection and barge-in (defaults) | the operator and the customer can pause while spelling or thinking without being cut off |
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
- **2026-09-16** Streaming spike (`eval/spike_*.py`): six synthetic voices × three configs. Without keyterms the model missed 16 of 30 model mentions and 14 of 48 codes; with `keyterms_prompt` it missed 2 and 3. "Onda" became "Honda" in every bare run and in none of the keyterm runs.
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
- **2026-09-26** Turn detection left on AssemblyAI's semantic default: fixed silence rules cut the customer's sentences. The page holds the microphone back while the agent's voice plays, and a clear sustained voice interrupts it.
- **2026-09-26** The customer's email is on file with the installed base; dictating addresses letter by letter over a call proved unreliable. A new address goes through a dedicated tool and must appear in the customer's own words.

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

Headless checks against the real Voice Agent (they cost a few cents of agent time):
`eval/ws_voice.py 8000 dave|lena|mario` (a synthetic customer calls the automatic assistant) and
`eval/ws_roleplay.py 8000 klaus` (a synthetic operator talks to the simulated customer).

## Tests

`python -m pytest -q` runs 241 tests in under a minute, with no microphone, no network and no AssemblyAI credits.
They check Cardex's own side of the call: rules, data and decisions. What the agent says is produced by AssemblyAI's
model and is not deterministic; that is checked with live calls and with the headless checks above.

| File | Tests | What it guarantees |
|---|---|---|
| `test_voice_tools.py` | 49 | The agent's tools and guard rails, costs and warranty, email, language handover, replays of live test calls |
| `test_normalizer.py` | 39 | Spoken part codes come back in canonical form ("e L3010" → EL-3010, "G E twenty-one forty" → GE-2140) |
| `test_defects_files.py` | 34 | Every procedure is a closed graph over the ERP: each answer leads to a step or an outcome, each part exists and fits, no step is unreachable, every model is covered |
| `test_semantic.py` | 31 | A fault described in seven languages reaches the right procedure; small talk and half sentences open nothing |
| `test_context_catalog.py` | 25 | Machine recognition, part search, serial numbers with one wrong digit, the service calendar |
| `test_symptoms_vocab.py` | 20 | Procedures and outcomes, answers not mistaken for new faults, keyterm phases |
| `test_manuals.py` | 20 | A manual per model in both languages, with shared anchors and only compatible parts |
| `test_dialog.py` | 19 | Reading an answer: numbers said in words, yes/no, on/off, negations, serials, emails, language |
| `test_limits.py` | 4 | The public demo limits and the token that waits for its call |

Every defect found in a live call becomes a test that replays that moment, named after the call in its docstring:
the warranty covers the repair's parts but never consumables; "I think it's dirty" cannot answer "how old is the
gasket?"; "Goodbye." never replaces a finished procedure; a serial said twice in one sentence is still one serial;
an email spelled letter by letter is recorded, an invented one is not.

## License

MIT
