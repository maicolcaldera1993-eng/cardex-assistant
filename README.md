# Cardex Assistant

First-line service for an espresso machine maker (Sereni, Florence, fictional), built on AssemblyAI. A barista abroad
calls because the machine is misbehaving; Cardex recognises the machine and the fault, walks the customer through the
maker's own troubleshooting procedure step by step, finds the right spare part in the ERP, tells who pays under
warranty, books the service call, and leaves a report a human approves before anything is ordered.

It runs in two ways on the same knowledge base:

- **Operator assist.** An Italian operator and a foreign customer talk in working English. Cardex transcribes live with
  speaker labels, shows the operator a clear Italian version, opens the procedure at the right step with the English
  sentence to read, and shows part cards with price, stock and delivery. The assistant proposes; the operator clicks.
- **Voice agent.** AssemblyAI's Voice Agent API talks to the customer directly, in English, Italian, Spanish, German,
  French or Portuguese. The agent converses freely, but every fact and every decision comes from Cardex through tools:
  it can only ask what the current step asks, and the server checks that the customer's words really answer it.

Built solo for the [AssemblyAI Voice Agent Hackathon](https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon) (lablab.ai, September 2026).

## Status

Day 10 of 15. Both modes work end to end in local tests with live voices. Knowledge base complete for the ten models:
fictional ERP (SQLite: 237 parts, compatibility, supersessions, stock per warehouse, prices, suppliers, installed base
with serial numbers and warranty, a two-week service calendar), step-by-step procedures for every family
(Marea and Giglio 13 faults, Onda 12, Monda 7), a manual per model in Italian and English, a sheet per part. 198 tests.

## How AssemblyAI is used

| Capability | Where |
|---|---|
| Universal-3.5 Pro streaming (WebSocket v3) with speaker labels | operator assist: who said what, word by word |
| `keyterms_prompt` updated mid-stream with `UpdateConfiguration` | vocabulary reloaded in three phases as machine, fault and part group become known |
| Word-level confidence | two candidate parts instead of a guess |
| Voice Agent API (`agents.assemblyai.com`) | voice agent: listening, conversation and voice in six languages, client-side function tools |
| LLM Gateway | clear Italian version of the customer's turns (operator assist) |

## Architecture decisions

Recorded here as they are made.

- **2026-09-16** Browser never talks to AssemblyAI with the API key: the backend owns the key, the limits and the logic (the voice agent gets a single-use token).
- **2026-09-16** Pure logic (normaliser, catalog search, context, vocabulary, roles, procedures) lives in `app/core/` with no network access and is covered by pytest before any audio is involved.
- **2026-09-16** Sample calls are streamed by the backend to AssemblyAI at real-time pace. No microphone involved, so demo and benchmark runs are reproducible.
- **2026-09-16** Text-to-speech uses the browser's speech synthesis. *(Superseded on 2026-09-24: the voice agent speaks with AssemblyAI's own voices.)*
- **2026-09-16** Streaming spike (`eval/spike_*.py`): six synthetic voices × three configs. Without keyterms the model missed 16 of 30 model mentions and 14 of 48 codes; with `keyterms_prompt` it missed 2 and 3. "Onda" became "Honda" in every bare run and in none of the keyterm runs.
- **2026-09-16** Known-defects files are step-by-step procedures, not lists of causes: each symptom is a small flowchart (ask/do steps, each answer branches to the next step or to an outcome: remote fix, part the customer fits, part fitted with service support, technician). The assistant never decides an outcome by itself.
- **2026-09-16** Pronunciation knowledge (how a German says "Giglio", how the ASR mis-hears "Onda") lives in `app/lexicon/pronunciation.json`, owned by Cardex. The ERP holds only business data.
- **2026-09-16** Knowledge base is structured, not a vector store: `data/sereni.db`, `data/kb/defects/*.json`, `data/kb/manuals/*.md`, `data/kb/parts/*.md`.
- **2026-09-17** LLM Gateway on a free account: only `qwen3.5-4b-32k-fast`, rate limit 2 requests per minute (`x-ratelimit-limit: 2`, measured with `eval/probe_gateway_rate.py`). The clear version queues customer turns and clarifies them in one batched call per free slot; it never blocks the transcript.
- **2026-09-17** A machine mentioned in passing does not move the call context: the assistant offers a one-click switch.
- **2026-09-18** Three layers of understanding. (1) Exact words: model names and part codes are closed sets, so lists and keyterms. (2) Meaning: a small local multilingual sentence-embedding model (`paraphrase-multilingual-MiniLM-L12-v2`, CPU) maps a fault description in any language onto a known symptom, above a threshold and only among the candidates the graph allows. (3) Reading the whole conversation with an LLM: probed, parked.
- **2026-09-18** Documents are a graph. Every page is cut into anchored sections that know which machines they belong to (`data/kb/index.json`, built by `data/build_wiki.py`). Similarity only chooses among the sections the graph admits for the machine on the call: near-identical part sheets (230 V vs 110 V element) make plain RAG unsafe for spare parts.
- **2026-09-18** Utterances of the same voice are merged until the other voice speaks; codes are rewritten in canonical form inside the sentence ("e L3010" shown as "EL-3010").
- **2026-09-21** Roles come only from AssemblyAI's word-level speaker labels (first voice = operator, mixed turns split by word). Timing heuristics were wrong too often.
- **2026-09-22** Meaning is read only on complete sentences, and a symptom must beat a generic "decoy" node by a margin: a turn cut at "the coffee comes out very" had opened the wrong procedure. Decisions are logged next to the raw turns for tracing.
- **2026-09-22** The serial number opens the installed-base record: model, build year, warranty (who pays the technician), previous orders. Tolerant to one mis-heard digit, with confirmation.
- **2026-09-23** While a step is open, what the customer says is an answer, not a new fault; faults are detected from the customer's voice only; a second fault waits until the operator starts it. The closed procedure shows what to do next: parts with price and delivery, warranty line, and a fictional two-week service calendar (remote desk or technician in the customer's zone) with one-click booking.
- **2026-09-24** Voice agent on the AssemblyAI Voice Agent API. The agent is configured inline per session (system prompt, voice, greeting, turn detection, `type: "function"` tools; a stored `agent_id` cannot be combined with per-session tools). The browser holds both sockets and relays tool calls to Cardex, so no public webhook is needed. Guard rails are server-side and deterministic: `answer_step` is accepted only if the customer's own words match an option of the current step (numbers said in words, yes/no, on/off pairs, negations, shared words, meaning, in English and Italian); `end_call` is refused while a step is open, while the outcome's parts are neither ordered nor declined, or before the agent has said goodbye; booking the fitting call orders the parts; the installed-base record wins over the model the customer names. The browser keeps the microphone closed while the agent's voice plays (half duplex), because barge-in misaligned answers and questions.
- **2026-09-24** Sentence vectors of the knowledge-base index are cached on disk (`data/kb/index.vectors.npz`, keyed by model and texts): with a manual per model, embedding 2,100 sentences at start-up took two minutes on a CPU.

## Running locally

```
python -m venv .venv          # Python 3.12
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then fill in ASSEMBLYAI_API_KEY
uvicorn app.main:app
python -m pytest -q
```

Rebuilding the knowledge base after editing the data scripts:

```
python data/build_db.py        # ERP, part sheets, lexicon
python data/build_manuals.py   # manuals for every model except the hand-written Marea 2 Plus
python data/build_wiki.py      # symptom pages and the section index
```

Headless checks against the real APIs: `eval/ws_duet.py` (operator assist with recorded customer lines),
`eval/ws_voice.py 8000 dave|lena|mario` (synthetic customer talking to the voice agent).

## Results

To be measured: part codes and symptoms correctly identified across four configurations (raw transcription,
static keyterms, dynamic keyterms, full pipeline).

## License

MIT
