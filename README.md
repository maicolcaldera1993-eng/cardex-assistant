# Cardex Assistant

A voice agent that sits on a spare-parts support call between an Italian operator and a foreign customer.
It transcribes live with speaker labels, translates each turn in both directions, recognises part codes in
whatever language they are spoken, reloads the speech-to-text vocabulary as it learns which machine the call
is about, speaks translations back to the customer, and hands the operator a summary at the end.

Built solo for the [AssemblyAI Voice Agent Hackathon](https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon) (lablab.ai, September 2026).

## Status

Day 4 of 15: idea locked, architecture written, fictional ERP built (SQLite, 14 tables, 237 parts, 10 models), known-defects file for the Marea family, first manual, product sheets, streaming spike done. Core logic written and tested (normaliser, model/group detection, catalog search, guided diagnosis, keyterm phases, roles). Server, call session and operator page work end to end on a streamed sample call.

## How AssemblyAI is used

| Capability | Where |
|---|---|
| Universal-3.5 Pro Realtime streaming (WebSocket v3) | every call |
| Streaming speaker diarization + `SpeakerRevision` | who is talking, translation direction, operator voice commands |
| Multilingual transcription with code-switching, `language_detection` | customer can speak any of 18 languages |
| `keyterms_prompt` + `prompt`, updated mid-stream with `UpdateConfiguration` | vocabulary reloaded in three phases as the machine and part group become known |
| Word-level confidence | show two candidate parts instead of guessing |
| LLM Gateway | per-turn translation (codes protected by placeholders), end-of-call summary |

## Architecture decisions

Recorded here as they are made.

- **2026-09-16** Browser never talks to AssemblyAI directly: the backend owns the key, the limits and the logic. Fallback if WebSocket deployment fails: temporary token + direct connection, logic moved to per-turn HTTP.
- **2026-09-16** Pure logic (normaliser, catalog search, context, vocabulary, roles, commands, summary) lives in `app/core/` with no network access and is covered by pytest before any audio is involved.
- **2026-09-16** Sample calls are streamed by the backend to AssemblyAI at real-time pace. No microphone or speakers involved, so demo and benchmark runs are reproducible.
- **2026-09-16** Text-to-speech uses the browser's speech synthesis. AssemblyAI voices exist only inside the Voice Agent API; production would use those.

- **2026-09-16** Streaming spike (`eval/spike_*.py`): six synthetic voices (Italian, US, German, Australian, Turkish and French accents reading English) × three configs. Without keyterms the model missed 16 of 30 model mentions and 14 of 48 codes; with `keyterms_prompt` it missed 2 and 3. "Onda" became "Honda" in every bare run and in none of the keyterm runs. Keyterms are the core of the recognition layer; the contextual `prompt` did not add anything measurable on this small set and will be re-tested in the benchmark. Turn detection needs pauses in the sample audio: continuous TTS produced one 44-second turn.

- **2026-09-16** Known-defects files are step-by-step procedures, not lists of causes: each symptom is a small flowchart (ask/do steps, each answer branches to the next step or to an outcome: remote fix, part the customer fits, part fitted with service support, technician). The operator sees one step at a time with the English sentence to read out, and clicks the customer's answer. The assistant never decides an outcome by itself.
- **2026-09-16** Pronunciation knowledge (how a German says "Giglio", how the ASR mis-hears "Onda") lives in `app/lexicon/pronunciation.json`, owned by Cardex. The ERP holds only real business data. Product sheets are static (no stock or prices): live figures are read from the database at call time.
- **2026-09-16** Knowledge base is structured, not embedded: `data/sereni.db` (SQLite ERP: parts, compatibility, supersessions, stock per warehouse, prices, suppliers, order stats), `data/kb/defects/*.json` (symptom → ordered causes → checks with the question to ask, the answer that confirms, what to do, resolution: remote / part_diy / part_with_support / technician), `data/kb/manuals/*.md`, `data/kb/parts/*.md` (generated from the DB, hand-written notes in `data/part_notes.py`). Retrieval will be fuzzy matching on spoken forms restricted to the detected model. No vector database: a few dozen defects and ten manuals do not need one, and deterministic retrieval is testable.

- **2026-09-17** LLM Gateway on a free AssemblyAI account: only `qwen3.5-4b-32k-fast` is accessible and about two requests per minute are accepted (HTTP 429 beyond that). The clear-version feature therefore queues customer turns and clarifies them in one batched call per free slot, with a trade glossary in the system prompt; it never blocks the transcript. Endpoint, model and rate are environment variables (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_MAX_PER_MINUTE`).
- **2026-09-17** A machine mentioned in passing does not move the call context: the assistant logs it and offers a one-click switch. Keyterm reloads happen at once for a new machine or a new symptom, and at most every 15 seconds for a mere change of topic.

- **2026-09-18** Three layers of understanding, each with its own job. (1) Exact words, instant: model names and part codes are closed sets, so lists and AssemblyAI keyterms are the right tool. (2) Meaning, instant: how a person describes a fault is open language in any tongue, so a small local multilingual sentence-embedding model (`paraphrase-multilingual-MiniLM-L12-v2`, CPU, ~10 ms) maps the last things said onto a known symptom. Reference texts exist only in Italian and English; tests cover German, Spanish, Turkish, French, Chinese and Portuguese. Below a threshold nothing is proposed; when two symptoms are close the operator picks. (3) Reading the whole conversation with an LLM: probed (`eval/probe_reader.py`), works even with the 4B model, parked until better LLM Gateway access.
- **2026-09-18** Documents are a graph, not a vector store. Every page is cut into anchored sections that know which machines they belong to (`data/kb/index.json`, built by `data/build_wiki.py`). Similarity is only allowed to choose among the sections the graph admits for the machine on the call, never to fetch a document by itself: near-identical part sheets (230 V vs 110 V heating element) make plain RAG unsafe in a spare-parts domain. The assistant opens the page at the right section and marks the sentence that matches what was said.
- **2026-09-18** A clean conversation is the first deliverable. The same voice keeps the same utterance however long the pause (reading a code off an invoice takes seconds): utterances are merged until the other voice speaks, and re-read each time they grow. Codes are rewritten in canonical form inside the sentence ("e L3010" is shown as "EL-3010").

## Running locally

```
python -m venv .venv          # Python 3.12
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then fill in ASSEMBLYAI_API_KEY
uvicorn app.main:app --reload
```

## Results

To be measured: part codes correctly identified out of 50 spoken utterances, across four configurations
(raw transcription, static keyterms, dynamic keyterms, full pipeline), plus codes surviving translation with and
without placeholder protection.

## License

MIT
