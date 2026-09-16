# Cardex Assistant

A voice agent that sits on a spare-parts support call between an Italian operator and a foreign customer.
It transcribes live with speaker labels, translates each turn in both directions, recognises part codes in
whatever language they are spoken, reloads the speech-to-text vocabulary as it learns which machine the call
is about, speaks translations back to the customer, and hands the operator a summary at the end.

Built solo for the [AssemblyAI Voice Agent Hackathon](https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon) (lablab.ai, September 2026).

## Status

Day 2 of 15: idea locked, architecture written, fictional catalog built (237 parts, 10 models), streaming spike done. No app code yet.

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
