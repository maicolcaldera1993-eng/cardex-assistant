"""One support call: audio in, events out.

The transcript layer is always on. Two operator toggles sit on top of it:
`clarify` (the clear version of what the customer said) and `assistant` (model,
symptom, guided diagnosis, part cards, keyterm reloads). The assistant proposes;
every decision is a click from the operator.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import wave
from dataclasses import asdict
from pathlib import Path
from typing import Awaitable, Callable

from .asr.assemblyai_stream import AssemblyAIStream
from .core.catalog import Catalog
from .core.context import ContextDetector
from .core.normalizer import canonicalize_codes, extract_codes
from .core.roles import CUSTOMER, OPERATOR, RoleTracker
from .core.semantic import AMBIGUITY_GAP, DECOY_MARGIN, SECTION_THRESHOLD, SYMPTOM_THRESHOLD, SemanticIndex
from .core.symptoms import DefectsLibrary, Diagnosis, parse_then, Outcome
from .core.vocabulary import VocabularyManager
from .llm.clarify import Clarifier
from .agent.dialog import AutoAgent
from .agent.tts import TTS
from .voice.agent import run_tool, tool_result_text

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
DUETS = SAMPLES / "duet"
MAX_SESSION_SECONDS = int(os.getenv("MAX_SESSION_SECONDS", "600"))          # public demo guard
MAX_REHEARSAL_SECONDS = int(os.getenv("MAX_REHEARSAL_SECONDS", "1500"))     # two-voice rehearsals take longer
_REQUEST_CUE = re.compile(r"\b(need|want|add|box|extra|include|buy|purchase|as well|order|ordered|send|replace|replacement|spare|part|broken|new one|another|"
                          r"serve|servono|ordin\w+|mand\w+|sostitu\w+|ricambio|rotto|rotta|nuov[oa])\b", re.I)
INACTIVITY_TIMEOUT = int(os.getenv("INACTIVITY_TIMEOUT_SECONDS", "60"))
_DEBUG_LOG = os.getenv("CARDEX_DEBUG_TURNS") or str(ROOT / "eval" / "logs" / "turns.jsonl")   # raw final turns, local only
Path(_DEBUG_LOG).parent.mkdir(parents=True, exist_ok=True)
CHUNK_MS = 50

# Loaded once, shared by every session (read-only).
CATALOG = Catalog()
CONTEXT = ContextDetector()
DEFECTS = DefectsLibrary()
VOCAB = VocabularyManager(CATALOG)
SEMANTIC = SemanticIndex()      # the model is loaded in the background at server start-up (see main.py)

# Same voice keeps talking: it is the same utterance, however long the pause (reading a code off an invoice
# takes seconds). Only the other voice, a very long silence or a very long bubble closes it.
MERGE_WINDOW_S = 60
MERGE_WINDOW_SINGLE_S = 6      # one-voice demo mode: nobody else can close the utterance, so use time
MERGE_MAX_WORDS = 70

Emit = Callable[[dict], Awaitable[None]]


def _manifest_single(source: str) -> str | None:
    """A sample recorded with one voice declares who that voice is in samples/manifest.json."""
    try:
        name = source.split(":", 1)[1]
        for s in json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8")):
            if s["id"] == name:
                return s.get("single_speaker")
    except (IndexError, OSError, ValueError):
        pass
    return None

_SERIAL = re.compile(r"(?:serial(?: number)?|matricola|numero di serie|n[úu]mero de serie|seriennummer)\D{0,15}((?:\d[\s\-]?){5,8})", re.I)
_SERIAL_ASKED = re.compile(r"serial|matricola|numero di serie|n[úu]mero de serie|seriennummer|typenschild|targhetta", re.I)
_SENTENCE_END = re.compile(r"[.!?…]\s*$")


def sentence_complete(text: str) -> bool:
    """AssemblyAI closes a turn mid-sentence now and then ("the coffee comes out very" | "thin and fast."). A fragment
    without final punctuation has not said what the fault is yet: meaning is read only on whole sentences."""
    return bool(_SENTENCE_END.search(text))


class CallSession:
    def __init__(self, api_key: str, emit: Emit, *, source: str = "mic", lang: str = "it"):
        self.api_key, self.emit, self.source, self.lang = api_key, emit, source, lang
        single = CUSTOMER if source in ("mic", "auto") else _manifest_single(source)   # duet: two real voices, no single role
        self.duet: dict | None = None
        self.duet_playing = False
        self.duet_last_done = -10.0
        self.duet_windows: list[tuple[float, float]] = []
        self.diarization_agrees: list[tuple[str, str | None]] = []   # (role from timing, label from AssemblyAI)
        self.label_votes: dict[str, dict[str, int]] = {}             # voice label -> votes for operator / customer
        self.stream_ms = 0.0
        if source.startswith("duet:"):
            f = DUETS / source.split(":", 1)[1] / "script.json"
            if f.is_file() and f.resolve().parent.parent == DUETS.resolve():
                self.duet = json.loads(f.read_text(encoding="utf-8"))
        self.roles = RoleTracker(single_speaker_role=single)
        self.assistant_on, self.clarify_on = True, True
        self.model_id: str | None = None
        self.family: str | None = None
        self.edition: str | None = None
        self.groups: list[str] = []
        self.serial: str | None = None
        self.machine: dict | None = None
        self.diagnosis: Diagnosis | None = None
        self.pending_symptoms: list[str] = []
        self.closed_symptoms: list[str] = []      # procedures that reached an outcome in this call
        self.dropped_symptoms: set[str] = set()   # files the operator said were wrong, or discarded from the queue
        self.other_models: list[str] = []
        self.last_vocab_at = 0.0
        self.vocab_trigger: tuple | None = None
        self.cards: dict[str, dict] = {}
        self.turns: dict[int, dict] = {}          # utterance id -> utterance (merged turns of one voice)
        self.utterances: list[dict] = []
        self.turn_to_utt: dict[int, int] = {}
        self.opened_docs: set[str] = set()
        self.offered_choices: set[tuple] = set()
        self.vocab_phase = 0
        self.vocab_key: tuple | None = None
        self.outcome: dict | None = None
        self.booking: dict | None = None         # service slot booked by the operator (fictional calendar)
        self.started = time.monotonic()
        self.asr: AssemblyAIStream | None = None
        self.audio_q: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=400)
        self.clarifier = Clarifier(api_key, lang, self._on_clear)
        self._closing = False
        # automatic mode: the assistant itself asks the questions (voice) and follows the customer's answers
        self.auto = AutoAgent(self, TTS, SEMANTIC.similarities) if source == "auto" else None
        # voice agent mode: AssemblyAI's hosted agent listens and talks; we are its memory and its tools
        self.voice = source == "voice"
        # operator practice with a simulated customer: both sides come as transcripts relayed by the page
        self.roleplay = source.startswith("roleplay")
        self.customer_lang = ""                   # roleplay: the language the simulated customer speaks
        if self.roleplay:
            from .voice.customer import PERSONAS
            self.customer_lang = PERSONAS.get(source.split(":", 1)[-1], {}).get("lang", "")
        self.relay = self.voice or self.roleplay
        self.voice_done = False
        self.voice_ended = asyncio.Event()
        self.voice_turn = 0
        self.notes: list[str] = []                # things the agent could not answer, for the operator
        self.unclear_steps: set[str] = set()      # steps where the agent's reported answer was rejected once
        self.unclear_count: dict[str, int] = {}   # rejections per step: a long off-topic reply needs a third call
        self.end_refused: set[str] = set()        # end_call refused once per reason: open step, parts, no goodbye
        self.end_wanted = False                   # the agent asked to end at least once
        self.fits_alone = False                   # the customer declined the service call: fits the parts alone
        self.last_agent_text = ""
        self.last_customer_text = ""
        self.serial_asked = 0                     # customer sentences still read as the answer to "which serial?"
        self.pending_description = ""             # the fault as described before the machine was known

    # ------------------------------------------------------------------ lifecycle
    async def run(self) -> None:
        vocab = VOCAB.build()
        self.vocab_phase, self.vocab_key = 1, (None, None, None, ())
        if self.relay:
            try:
                await self.emit({"type": "session", "state": "open", "source": self.source, "lang": self.lang,
                                 "limits": {"max_seconds": MAX_SESSION_SECONDS}})
                await self._emit_vocab(vocab)
                await self._emit_context()
                if self.roleplay:
                    self.clarifier.start()
                await asyncio.wait_for(self.voice_ended.wait(), timeout=MAX_REHEARSAL_SECONDS if self.roleplay else MAX_SESSION_SECONDS)
            except asyncio.TimeoutError:
                await self._agent("Tempo massimo raggiunto." if self.lang == "it" else "Time limit reached.")
            except Exception as e:  # noqa: BLE001
                await self.emit({"type": "error", "text": f"{type(e).__name__}: {e}"})
            finally:
                if self.roleplay:
                    await self.clarifier.close()
                await self._emit_summary()
            return
        try:
            async with AssemblyAIStream(self.api_key, keyterms=vocab.keyterms, prompt=vocab.prompt,
                                        inactivity_timeout=INACTIVITY_TIMEOUT) as asr:
                self.asr = asr
                self.clarifier.start()
                await self.emit({"type": "session", "state": "open", "source": self.source, "lang": self.lang,
                                 "limits": {"max_seconds": MAX_REHEARSAL_SECONDS if self.duet else MAX_SESSION_SECONDS}})
                await self._emit_vocab(vocab)
                if self.duet:
                    await self.emit({"type": "duet_script", "id": self.duet["id"], "lines": self.duet["lines"]})
                if self.auto:
                    await self.auto.start()
                feeder = asyncio.create_task(self._feed_sample() if self.source.startswith("sample:") else self._feed_mic())
                guard = asyncio.create_task(self._time_limit())
                try:
                    async for msg in asr.messages():
                        await self._on_asr(msg)
                finally:
                    feeder.cancel()
                    guard.cancel()
        except Exception as e:  # noqa: BLE001
            await self.emit({"type": "error", "text": f"{type(e).__name__}: {e}"})
        finally:
            await self.clarifier.close()
            await self._emit_summary()

    async def _time_limit(self) -> None:
        limit = MAX_REHEARSAL_SECONDS if self.duet else MAX_SESSION_SECONDS
        await asyncio.sleep(max(0, limit - 45))
        await self._agent("Tra 45 secondi la chiamata si chiude per il limite di durata." if self.lang == "it"
                          else "The call closes in 45 seconds (time limit).")
        await asyncio.sleep(45)
        await self._agent("Limite di durata della demo raggiunto: chiudo la chiamata." if self.lang == "it"
                          else "Demo time limit reached: closing the call.")
        await self.end()

    async def end(self) -> None:
        if self.relay:
            self._closing = True
            self.voice_ended.set()
            return
        if not self._closing and self.asr:
            self._closing = True
            # the last thing said has no pause after it: send a little silence so the model hears the end,
            # force the turn to close, give the final text time to arrive, then terminate
            try:
                silence = b"\x00" * (16000 * 2 * CHUNK_MS // 1000)
                for _ in range(16):
                    await self.asr.send_audio(silence)
                    await asyncio.sleep(CHUNK_MS / 1000)
                await self.asr.force_endpoint()
                await asyncio.sleep(1.5)
            except Exception:  # noqa: BLE001
                pass
            await self.audio_q.put(None)
            await self.asr.terminate()

    async def push_audio(self, pcm: bytes) -> None:
        if not self._closing:
            try:
                self.audio_q.put_nowait(pcm)
            except asyncio.QueueFull:
                pass

    async def _feed_mic(self) -> None:
        while True:
            chunk = await self.audio_q.get()
            if chunk is None:
                return
            if self.duet_playing:
                continue                      # the recorded customer is talking: the operator's mic stays out of the stream
            await self.asr.send_audio(chunk)
            self.stream_ms += len(chunk) / 32          # 16 kHz, 16-bit mono: 32 bytes per millisecond of audio

    async def play_duet_line(self, n: int) -> None:
        """Streams one recorded customer line into the same AssemblyAI session, at real-time pace, while the
        browser plays it through the speakers for the operator to hear. Two real voices, one stream."""
        if not self.duet or self._closing:
            return
        if self.duet_playing:
            await self.emit({"type": "duet", "state": "busy", "n": n})    # tell the page, so the mic is never left muted
            return
        line = next((l for l in self.duet["lines"] if l["n"] == n), None)
        if not line:
            return
        path = DUETS / self.duet["id"] / line["file"]
        with wave.open(str(path), "rb") as w:
            pcm = w.readframes(w.getnframes())
        self.duet_playing = True
        await self.emit({"type": "duet", "state": "playing", "n": n})
        start_ms = self.stream_ms
        self.duet_windows.append((start_ms, float("inf")))     # open window: turns arrive WHILE the clip plays
        try:
            step = 16000 * 2 * CHUNK_MS // 1000
            t0 = time.monotonic()
            for k, i in enumerate(range(0, len(pcm), step)):
                if self._closing:
                    return
                await self.asr.send_audio(pcm[i:i + step].ljust(step, b"\x00"))
                self.stream_ms += step / 32
                await asyncio.sleep(max(0.0, t0 + (k + 1) * CHUNK_MS / 1000 - time.monotonic()))
            await asyncio.sleep(0.4)
        finally:
            self.duet_windows[-1] = (start_ms, self.stream_ms)     # close the window: where the recorded customer spoke
            self.duet_playing = False
            self.duet_last_done = time.monotonic()
            await self.emit({"type": "duet", "state": "done", "n": n})

    def _diarization_report(self) -> dict | None:
        """Rehearsal only: did AssemblyAI's speaker labels agree with the roles we know from timing?"""
        if not self.diarization_agrees:
            return None
        n = len(self.diarization_agrees)
        ok = sum(1 for truth, said in self.diarization_agrees if truth == said)
        return {"segments": n, "attributed_correctly": ok, "accuracy": round(ok / n, 2) if n else None}

    def _duet_role(self, words: list[dict]) -> str | None:
        """In rehearsal mode roles come from timing, not from diarization: a turn whose words fall inside a
        recorded-clip window is the customer, anything else is the operator at the microphone."""
        if not words:
            return None
        mid = (words[0].get("start", 0) + words[-1].get("end", 0)) / 2
        for a, b in self.duet_windows:
            if a - 50 <= mid <= b + 100:          # the operator's mic is off while the clip plays: edges are sharp
                return CUSTOMER
        return OPERATOR

    async def _feed_sample(self) -> None:
        name = self.source.split(":", 1)[1]
        path = (SAMPLES / name).with_suffix(".wav")
        if not path.is_file() or path.parent != SAMPLES:
            await self.emit({"type": "error", "text": f"sample not found: {name}"})
            return await self.end()
        with wave.open(str(path), "rb") as w:
            pcm = w.readframes(w.getnframes())
        step = 16000 * 2 * CHUNK_MS // 1000
        t0 = time.monotonic()
        for n, i in enumerate(range(0, len(pcm), step)):
            if self._closing:
                return
            await self.asr.send_audio(pcm[i:i + step].ljust(step, b"\x00"))
            await asyncio.sleep(max(0.0, t0 + (n + 1) * CHUNK_MS / 1000 - time.monotonic()))
        await asyncio.sleep(1.5)
        await self.end()

    # ------------------------------------------------------------------ ASR events
    async def _on_asr(self, msg: dict) -> None:
        t = msg.get("type")
        if t == "Turn":
            await self._on_turn(msg)
        elif t == "SpeakerRevision":
            for rev in msg.get("revisions", msg.get("turns", [])):
                tid = self.turn_to_utt.get(rev.get("turn_order"))
                if tid in self.turns and rev.get("speaker_label"):
                    role, label = self.roles.role_for(rev["speaker_label"])
                    self.turns[tid].update(role=role, speaker=label)
        elif t == "Termination":
            await self._agent(f"Sessione chiusa: {msg.get('audio_duration_seconds')} s di audio." if self.lang == "it"
                              else f"Session closed: {msg.get('audio_duration_seconds')} s of audio.")
        elif t == "Error" or "error" in msg:
            await self.emit({"type": "error", "text": json.dumps(msg)[:300]})

    def _log_decision(self, what: str, **data) -> None:
        """Same local log as the raw turns: what the assistant decided and why, so a wrong symptom can be traced
        without re-running the audio."""
        if _DEBUG_LOG:
            with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps({"stream_ms": round(self.stream_ms), "decision": what, **data}, ensure_ascii=False) + "\n")

    async def _on_turn(self, msg: dict) -> None:
        if _DEBUG_LOG and msg.get("end_of_turn"):
            with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps({"stream_ms": round(self.stream_ms), "windows": self.duet_windows, "turn": msg}, ensure_ascii=False) + "\n")
        tid = msg.get("turn_order", 0)
        text = (msg.get("transcript") or "").strip()
        if not text:
            return
        if not msg.get("end_of_turn"):
            if self.auto:
                self.auto.still_talking()                  # partial words: the customer has not finished
            await self.emit({"type": "turn", "id": tid, "final": False, "text": text})
            return
        self.last_eot_confidence = float(msg.get("end_of_turn_confidence") or 1.0)   # the automatic assistant waits longer on a shaky turn end
        words = msg.get("words") or []
        # One AssemblyAI turn can hold both voices when the second starts without a pause ("Okay, what's the
        # problem? We have a problem with..."). Split it by word: timing in rehearsal mode, word-level speaker
        # labels otherwise. Each piece is then handled as a turn of its own.
        segments = self._split_by_speaker(words, msg.get("speaker_label"))
        if len(segments) <= 1:
            role, label = (segments[0][0], segments[0][1]) if segments else self.roles.role_for(msg.get("speaker_label"))
            await self._on_final_piece(tid * 100, text, role, label, words)      # same id scale as split pieces
            return
        for i, (role, label, piece_words) in enumerate(segments):
            piece = " ".join(w.get("text", "") for w in piece_words).strip()
            if piece:
                await self._on_final_piece(tid * 100 + i, piece, role, label, piece_words)

    def _split_by_speaker(self, words: list[dict], turn_label: str | None) -> list[tuple[str, str | None, list[dict]]]:
        """Roles come from AssemblyAI's word-level voice labels, in every mode: the first voice with a final
        turn is the operator (they answered the phone), the other one the customer. In rehearsal mode the clip
        timing is used only to CHECK the labels (the report's diarization line), never to decide."""
        if not words:
            return []
        out: list[tuple[str, str | None, list[dict]]] = []
        prev_role: str | None = None
        for w in words:
            wl = w.get("speaker")
            if wl in (None, "", "PENDING") and prev_role:
                role, label = prev_role, turn_label
            else:
                role, label = self.roles.role_for(wl or turn_label)
            if out and out[-1][0] == role:
                out[-1][2].append(w)
            else:
                out.append((role, label, [w]))
            prev_role = role
        # diarization labels flicker: one or two words of the other voice inside a sentence are noise, not a speaker change
        smoothed: list[tuple[str, str | None, list[dict]]] = []
        for i, seg in enumerate(out):
            stray = 0 < i < len(out) - 1 and len(seg[2]) <= 2 and out[i - 1][0] == out[i + 1][0]
            if smoothed and (stray or smoothed[-1][0] == seg[0]):
                smoothed[-1][2].extend(seg[2])
            else:
                smoothed.append((seg[0], seg[1], list(seg[2])))
        if self.duet:
            for role, label, ws in smoothed:
                truth = self._duet_role(ws)
                if truth:
                    self.diarization_agrees.append((truth, role))     # (who really spoke, who we said)
        return smoothed

    async def _on_final_piece(self, tid: int, text: str, role: str, label: str | None, words: list[dict]) -> None:
        min_conf = round(min((w.get("confidence", 1.0) for w in words), default=1.0), 2)
        now = round(time.monotonic() - self.started, 1)

        last = self.utterances[-1] if self.utterances else None
        window = MERGE_WINDOW_SINGLE_S if self.roles.single else MERGE_WINDOW_S
        if (last and last["role"] == role and now - last["at_end"] <= window
                and len(last["raw"].split()) + len(text.split()) <= MERGE_MAX_WORDS):
            last["raw"] += " " + text
            last["fragments"].append(text)
            last["turn_ids"].append(tid)
            last["min_conf"] = min(last["min_conf"], min_conf)
            last["confs"].append(min_conf)
            last["at_end"] = now
            utt = last
        else:
            utt = {"id": tid, "raw": text, "fragments": [text], "confs": [min_conf], "role": role, "speaker": label, "turn_ids": [tid], "min_conf": min_conf,
                   "at": now, "at_end": now, "clear": None}
            self.utterances.append(utt)
            self.turns[tid] = utt
        self.turn_to_utt[tid] = utt["id"]
        utt["text"], utt["codes"] = canonicalize_codes(utt["raw"])      # "e L3010" is shown as "EL-3010"

        await self.emit({"type": "turn", "id": utt["id"], "final": True, "text": utt["text"], "role": role,
                         "speaker": label, "min_conf": utt["min_conf"], "merged": len(utt["turn_ids"])})
        if role == CUSTOMER and self.clarify_on:
            self.clarifier.submit(utt["id"], utt["text"])
            await self.emit({"type": "clear_pending", "turn_id": utt["id"]})
        if self.assistant_on:
            # the whole utterance is re-read every time it grows: "the code is..." [4 s] "GE-2140" is one thought
            # codes need the whole utterance (a code can straddle a pause); meaning is read on what was just said,
            # the last two fragments, otherwise a long utterance dilutes it
            recent = [canonicalize_codes(f)[0] for f in utt["fragments"][-2:]]
            if len(recent) == 2:
                recent = [recent[-1], " ".join(recent)]          # what was just said, then with its predecessor for context
            await self._assist(utt["id"], utt["text"], role, utt["confs"][-1], recent, utt)
        if self.auto and role == CUSTOMER:
            self.auto.heard(text)                            # the automatic assistant answers once the customer pauses

    # ------------------------------------------------------------------ the assistant
    async def _assist(self, tid: int, text: str, role: str, min_conf: float, recent: list[str] | None = None,
                      utt: dict | None = None) -> None:
        recent = recent or [text]
        hit = CONTEXT.detect(text)
        changed = False
        if hit.model_id and self.model_id and hit.model_id != self.model_id:
            # another machine mentioned in passing ("in the other shop we have a Monda"): do not jump, offer the switch
            if hit.model_id not in self.other_models:
                self.other_models.append(hit.model_id)
                name = VOCAB.model_names[hit.model_id]
                await self.emit({"type": "model_mention", "model_id": hit.model_id, "model": name})
                await self._agent(f"Citata anche un'altra macchina: {name}. Resto su {VOCAB.model_names[self.model_id]}." if self.lang == "it"
                                  else f"Another machine was mentioned: {name}. Staying on {VOCAB.model_names[self.model_id]}.")
        elif hit.model_id and hit.model_id != self.model_id:
            self.model_id, self.family, changed = hit.model_id, hit.family, True
            name = VOCAB.model_names[hit.model_id]
            heard = f" (sentito: «{hit.matched}»)" if hit.via_variant else ""
            await self._agent(f"Macchina riconosciuta: {name}{heard}" if self.lang == "it"
                              else f"Machine recognised: {name}" + (f" (heard: “{hit.matched}”)" if hit.via_variant else ""))
            await self._open_manual(self.model_id)
        elif hit.family and not self.model_id and hit.family != self.family:
            self.family, changed = hit.family, True
            await self._agent(f"Famiglia riconosciuta: {hit.family}. Versione da chiedere." if self.lang == "it"
                              else f"Family recognised: {hit.family}. Ask which version.")
        if hit.edition and hit.edition != self.edition:
            self.edition, changed = hit.edition, True
            await self._agent("Edizione Vaniglia (finitura crema)." if self.lang == "it" else "Vaniglia edition (cream finish).")
        if hit.groups and hit.groups != self.groups:
            self.groups, changed = hit.groups, True
        m = _SERIAL.search(text)
        if m:
            await self._set_serial(re.sub(r"\D", "", m.group(1)))
        if changed:
            await self._emit_context()

        # meaning-based symptom detection listens to the CUSTOMER only: the operator's questions ("what is the
        # problem?", "how long does a shot take?") are about the fault, not descriptions of it. Exact spoken phrases
        # still count from either voice (operators restate what they heard).
        if role == CUSTOMER and not self.voice:
            # the operator's questions are about the fault, not descriptions of it ("no level alarm?" is a question)
            if not await self._detect_symptom(recent, semantic=sentence_complete(recent[0])) \
                    and not (self.diagnosis and self.diagnosis.current):
                await self._open_matching_section(recent[-1])

        cards = []
        codes = extract_codes(text)
        for c in codes:
            if c.code in self.cards:
                continue                                       # already on the table from an earlier fragment
            conf = min_conf
            if utt:                                            # confidence of the fragment the code was heard in
                for frag, fc in zip(utt["fragments"], utt["confs"]):
                    if c.code in canonicalize_codes(frag)[0]:
                        conf = fc
                        break
            cards += CATALOG.search_code(c.code, model_id=self.model_id, family=self.family, groups=self.groups,
                                         min_confidence=conf if c.exact_shape else 0.0)
        if not codes and role == CUSTOMER and _REQUEST_CUE.search(recent[0]):
            # a part named by description counts only when the CUSTOMER is asking for something, not when the
            # operator reads a procedure aloud ("14 grams in the double basket" is not an order for baskets)
            cards += CATALOG.search_description(recent[0], model_id=self.model_id, family=self.family, groups=self.groups)
        await self._add_cards(cards, tid, source="voice")
        for c in cards:
            if c.reason in ("exact", "near-code", "description", "replacement"):   # an incompatible or superseded code is exactly when the sheet matters
                await self._open_doc(f"part/{c.code}", "code" if c.reason != "description" else "description")
                break
        await self._maybe_reload_vocabulary()

    # ------------------------------------------------------------------ meaning and documents
    async def _detect_symptom(self, texts: list[str], semantic: bool = True) -> bool:
        """Which known fault is the CUSTOMER describing? Meaning first (any language), exact phrases as a tie-breaker.
        Only the symptoms that apply to the machine being discussed are candidates. While a step is open, what the
        customer says is first of all an answer to it; a symptom already closed or discarded in this call never
        reopens by itself."""
        exact = DEFECTS.match(texts[-1], model_id=self.model_id, family=self.family)
        chosen, heard, options = None, None, []
        fam = CATALOG.family_models(self.family) if self.family and not self.model_id else None
        allowed = SEMANTIC.ids_for("symptom", self.model_id, fam) if SEMANTIC.ready else set()
        decoys = {n for n in allowed if SEMANTIC.nodes[n].get("decoy")}
        if exact:
            chosen, heard = exact.symptom_id, exact.matched          # an exact spoken phrase is strong evidence...
            if SEMANTIC.ready and semantic:
                # ...unless the sentence as a whole clearly means another fault: "the steam is very weak, foaming the
                # milk takes forever" contains the slow-coffee phrase "takes forever", but it is about steam
                sims = {m.node_id.split("/", 1)[1]: m.score for m in SEMANTIC.search(texts[-1], allowed=allowed - decoys, k=5)}
                if sims:
                    top_id, top = max(sims.items(), key=lambda kv: kv[1])
                    if top_id != chosen and top >= SYMPTOM_THRESHOLD and top - sims.get(chosen, 0.0) >= 0.10:
                        self._log_decision("exact_overruled", text=texts[-1], exact=chosen, by=top_id,
                                           scores=[round(top, 3), round(sims.get(chosen, 0.0), 3)])
                        chosen, heard = top_id, f"≈ {SEMANTIC.nodes['symptom/' + top_id]['title_en']}, {top:.2f}"
        elif SEMANTIC.ready and semantic:
            best: dict[str, object] = {}
            decoy = 0.0
            for q in texts:                                          # the last fragment alone, then with context
                for m in SEMANTIC.search(q, allowed=allowed - decoys, k=3):
                    if m.node_id not in best or m.score > best[m.node_id].score:
                        best[m.node_id] = m
                # the generic decoy is always scored, even when it would not be among the top matches
                decoy = max([decoy] + [m.score for m in SEMANTIC.search(q, allowed=decoys, k=1)])
            ranked = sorted(best.values(), key=lambda m: m.score, reverse=True)
            # "we have a problem with the machine": not a symptom yet. A real fault must clear the decoy by a margin,
            # otherwise a half sentence read with its context can edge past it
            ms = [m for m in ranked if m.score >= max(SYMPTOM_THRESHOLD, decoy + DECOY_MARGIN)][:2]
            self._log_decision("symptom_scores", texts=texts, decoy=round(decoy, 3),
                               top=[(m.node_id, round(m.score, 3)) for m in ranked[:3]])
            if ms:
                ids = [m.node_id.split("/", 1)[1] for m in ms]
                if len(ms) == 2 and ms[0].score - ms[1].score < AMBIGUITY_GAP:
                    options = ms
                else:
                    chosen, heard = ids[0], f"≈ {ms[0].ref}, {ms[0].score:.2f}"
        if not chosen and not options:
            return False
        active = self.diagnosis.symptom["id"] if self.diagnosis else None
        open_step = bool(self.diagnosis and self.diagnosis.current)
        if chosen == active:
            return True
        if chosen and (chosen in self.closed_symptoms or chosen in self.dropped_symptoms):
            self._log_decision("symptom_ignored", text=texts[0], chosen=chosen, why="already closed or discarded")
            return True
        if open_step and self.diagnosis.is_answer(texts[0]):
            # "Okay, I found the red button, I pressed it." is the answer to the step, not "a button does not respond"
            self._log_decision("answer_not_symptom", text=texts[0], step=self.diagnosis.current,
                               looked_like=chosen or [m.node_id for m in options])
            return True
        self._log_decision("symptom", text=texts[0], chosen=chosen, heard=heard, active=active,
                           options=[m.node_id for m in options], semantic=semantic)
        if options:
            key = tuple(sorted(m.node_id for m in options))
            if key not in self.offered_choices and not open_step:
                self.offered_choices.add(key)
                await self.emit({"type": "symptom_choice", "options": [
                    {"symptom_id": m.node_id.split("/", 1)[1], "score": m.score,
                     "title": DEFECTS.symptoms[m.node_id.split("/", 1)[1]][f"symptom_{self.lang}"]} for m in options]})
                await self._agent("Due guasti possibili: scegli quello giusto nel pannello." if self.lang == "it"
                                  else "Two possible faults: pick the right one in the panel.")
            return True
        if open_step:
            if chosen not in self.pending_symptoms:
                self.pending_symptoms.append(chosen)
                await self._agent(f"Secondo problema in attesa: {DEFECTS.symptoms[chosen]['symptom_it']}. Lo avvii dal pannello quando hai chiuso questo." if self.lang == "it"
                                  else f"Second problem waiting: {DEFECTS.symptoms[chosen]['symptom_en']}. Start it from the panel once this one is closed.")
                await self._emit_diagnosis()
        else:
            await self._start_diagnosis(chosen, heard)
        return True

    async def _open_matching_section(self, text: str) -> None:
        """A section of THIS machine's manual that talks about what was just said."""
        if not (SEMANTIC.ready and self.model_id):
            return
        allowed = SEMANTIC.ids_for("manual", self.model_id)
        for m in SEMANTIC.search(text, allowed=allowed, k=1):
            if m.score >= SECTION_THRESHOLD:
                await self._open_doc(m.node_id, "topic", query=text, score=m.score)

    async def _open_manual(self, model_id: str) -> None:
        ids = sorted(i for i in SEMANTIC.ids_for("manual", model_id))
        if ids:
            first = next((i for i in ids if i.endswith("#descrizione")), ids[0])
            await self._open_doc(first, "machine")

    async def _open_doc(self, node_id: str, reason: str, query: str | None = None, score: float | None = None) -> None:
        node = SEMANTIC.nodes.get(node_id)
        if not node or node_id in self.opened_docs:
            return
        self.opened_docs.add(node_id)
        highlight = None
        if query and SEMANTIC.ready and len(node["refs"]) > 1:
            best = SEMANTIC.best_sentence(query, node["refs"][1 + node.get("n_topics", 0):])   # skip title and topic keywords
            if best and best[1] >= 0.55:
                highlight = best[0]
        await self.emit({"type": "open_doc", "node_id": node_id, "kind": node["kind"], "page": node["page"],
                         "anchor": node["anchor"], "title": node["title"], "reason": reason,
                         "highlight": highlight, "score": score})
        label = {"machine": "libretto della macchina", "topic": "sezione del libretto", "symptom": "fascicolo difetti",
                 "code": "scheda del ricambio", "description": "scheda del ricambio", "procedure": "scheda del ricambio"}
        if self.lang == "it":
            await self._agent(f"Apro {label.get(reason, 'documento')}: {node['title']}")
        else:
            await self._agent(f"Opening {node['kind']} page: {node.get('title_en') or node['title']}")

    async def _set_serial(self, serial: str) -> None:
        if serial == self.serial:
            return
        self.serial = serial
        rec = CATALOG.machine(serial)
        self.machine = rec
        if not rec:
            await self._agent(f"Matricola {serial}: non trovata nel parco installato." if self.lang == "it"
                              else f"Serial {serial}: not found in the installed base.")
            await self._emit_context()
            return
        if not rec["matched_exactly"]:
            await self._agent(f"Matricola sentita «{serial}», in archivio c'è {rec['serial']}: confermare." if self.lang == "it"
                              else f"Heard serial “{serial}”, the records have {rec['serial']}: confirm.")
        in_warranty = rec["warranty_until"] >= time.strftime("%Y-%m-%d")
        rec["in_warranty"] = in_warranty                  # the outcome view needs it to say who pays
        name = VOCAB.model_names.get(rec["model_id"], rec["model_id"])
        if rec["model_id"] != self.model_id:
            if self.model_id:
                await self._agent(f"Attenzione: la matricola {rec['serial']} è di una {name}, non di una {VOCAB.model_names[self.model_id]}."
                                  if self.lang == "it" else
                                  f"Warning: serial {rec['serial']} belongs to a {name}, not a {VOCAB.model_names[self.model_id]}.")
            else:
                self.model_id, self.family = rec["model_id"], CONTEXT.family_of[rec["model_id"]].capitalize()
                await self._agent(f"Macchina dalla matricola: {name}" if self.lang == "it" else f"Machine from the serial: {name}")
        if rec["edition"]:
            self.edition = rec["edition"]
        notes = []
        notes.append((f"costruita {rec['built']}, installata {rec['installed']} a {rec['city']} ({rec['customer']})") if self.lang == "it"
                     else f"built {rec['built']}, installed {rec['installed']} in {rec['city']} ({rec['customer']})")
        notes.append((f"IN GARANZIA fino al {rec['warranty_until']}: l'eventuale tecnico è a carico nostro" if in_warranty
                      else f"FUORI GARANZIA dal {rec['warranty_until']}: l'eventuale tecnico è a carico del cliente") if self.lang == "it"
                     else (f"UNDER WARRANTY until {rec['warranty_until']}: a technician visit is on us" if in_warranty
                           else f"OUT OF WARRANTY since {rec['warranty_until']}: a technician visit is charged to the customer"))
        if rec["notes"]:
            notes.append(rec["notes"])
        for n in notes:
            await self._agent(n)
        for o in rec["orders"][:4]:
            await self._agent((f"Ordine {o['ordered_on']}: {o['code']} ×{o['qty']} ({o['description_it']})") if self.lang == "it"
                              else f"Order {o['ordered_on']}: {o['code']} ×{o['qty']} ({o['description_en']})")
        await self.emit({"type": "machine_record", "serial": rec["serial"], "model": name, "edition": rec["edition"],
                         "built": rec["built"], "voltage": rec["voltage"], "customer": rec["customer"], "city": rec["city"],
                         "country": rec["country"], "warranty_until": rec["warranty_until"], "in_warranty": in_warranty,
                         "notes": rec["notes"], "orders": rec["orders"], "exact": rec["matched_exactly"]})
        await self._emit_context()
        await self._maybe_reload_vocabulary()

    async def _start_diagnosis(self, symptom_id: str, matched: str | None = None) -> None:
        self.diagnosis = DEFECTS.start(symptom_id)
        s = self.diagnosis.symptom
        if s["group"] not in self.groups:
            self.groups = [s["group"]] + self.groups
        heard = f" («{matched}»)" if matched else ""
        await self._agent(f"Sintomo riconosciuto: {s['symptom_it']}{heard}. Apro la procedura." if self.lang == "it"
                          else f"Symptom recognised: {s['symptom_en']}{heard}. Opening the procedure.")
        await self._emit_diagnosis()
        await self._open_doc(f"symptom/{symptom_id}", "symptom")

    def _say_for_part(self, c, handling: str) -> str:
        """One sentence the operator can read out: what we do with this part and when it arrives."""
        if not c.compatible:
            return (f"{c.code} does not fit your machine" + (f"; the current part is {c.superseded_by}." if c.superseded_by else "."))
        where = c.delivery[0] if c.delivery else None
        ship = (f"I can ship {c.description_en} ({c.code}) from {where['from'].replace('FI-01 ', '').replace('NL-01 ', '')}, "
                f"{where['days']} working days" if where and where["qty"] > 0 else
                f"{c.description_en} ({c.code}) is not in stock, {where['days'] if where else '7-10'} working days from the supplier")
        if handling == "diy":
            return ship + ". You can fit it yourself: I'll send you the sheet with the steps."
        return ship + ". Fitting this one needs our service on the line: we'll book a second call when it arrives."

    async def _add_cards(self, cards, tid: int | None, source: str) -> None:
        new = []
        for c in cards:
            if c.code in self.cards:
                continue
            d = asdict(c)
            d.update(status="proposed", source=source, turn_id=tid,
                     description=d[f"description_{self.lang}"])
            d["handling"] = DEFECTS.handling.get(c.code) or ("support" if c.group in ("CA", "ID", "EL") else "diy")
            d["say_en"] = self._say_for_part(c, d["handling"])
            self.cards[c.code] = d
            new.append(d)
        if new:
            await self.emit({"type": "parts", "cards": new})
            for d in new:
                if d["reason"] == "replacement":
                    continue
                txt = {"exact": "codice esatto", "near-code": "codice simile, da confermare",
                       "description": "trovato dalla descrizione"}.get(d["reason"], d["reason"]) if self.lang == "it" else \
                      {"exact": "exact code", "near-code": "similar code, to confirm",
                       "description": "found from the description"}.get(d["reason"], d["reason"])
                warn = ""
                if not d["compatible"]:
                    warn = " — NON compatibile con questa macchina" if self.lang == "it" else " — NOT compatible with this machine"
                if d["superseded_by"]:
                    warn += (f" — sostituito da {d['superseded_by']}" + (f", richiede {d['requires']}" if d["requires"] else "")) \
                        if self.lang == "it" else \
                        (f" — superseded by {d['superseded_by']}" + (f", requires {d['requires']}" if d["requires"] else ""))
                await self._agent(f"{d['code']}: {txt}{warn}")

    def _symptom_parts(self) -> list[str]:
        if not self.diagnosis:
            return []
        out: list[str] = []
        for st in self.diagnosis.symptom["steps"]:
            for p in st.get("parts", []):
                if p not in out:
                    out.append(p)
            for b in st["branches"]:
                o = parse_then(b["then"])
                if isinstance(o, Outcome):
                    out += [p for p in o.parts if p not in out]
        return out

    async def _maybe_reload_vocabulary(self) -> None:
        group = self.groups[0] if self.groups else None
        parts = tuple(self._symptom_parts())
        key = (self.model_id, self.family if not self.model_id else None, group if (self.model_id or self.family) else None, parts)
        if key == self.vocab_key or not (self.model_id or self.family):
            return
        # a new machine or a new symptom reloads at once; a mere change of topic at most every 15 seconds
        trigger = (key[0], key[1], parts)
        if trigger == self.vocab_trigger and time.monotonic() - self.last_vocab_at < 15:
            return
        self.vocab_key, self.vocab_trigger, self.last_vocab_at = key, trigger, time.monotonic()
        vocab = VOCAB.build(model_id=self.model_id, family=self.family, group=group, symptom_parts=list(parts))
        self.vocab_phase = vocab.phase
        if self.asr and not self._closing:
            await self.asr.update(keyterms=vocab.keyterms, prompt=vocab.prompt)
        await self._emit_vocab(vocab)

    # ------------------------------------------------------------------ operator controls
    async def control(self, msg: dict) -> None:
        a = msg.get("action")
        if a == "end_call":
            await self.end()
        elif a == "play_line" and self.duet:
            asyncio.create_task(self.play_duet_line(int(msg.get("n", 0))))
        elif a == "swap_roles":
            self.roles.swap()
            await self._agent("Ruoli scambiati." if self.lang == "it" else "Roles swapped.")
        elif a == "toggle":
            if msg.get("what") == "assistant":
                self.assistant_on = bool(msg.get("on"))
            elif msg.get("what") == "clarify":
                self.clarify_on = self.clarifier.enabled = bool(msg.get("on"))
            await self.emit({"type": "toggles", "assistant": self.assistant_on, "clarify": self.clarify_on})
        elif a == "answer_step" and self.diagnosis and not self.diagnosis.outcome:
            self.diagnosis.answer(int(msg["branch"]))
            if self.diagnosis.outcome:
                await self._on_outcome(self.diagnosis.outcome)
            else:
                await self._emit_diagnosis()
        elif a == "start_symptom" and msg.get("symptom_id") in DEFECTS.symptoms:
            sid = msg["symptom_id"]
            if self.diagnosis and self.diagnosis.current and self.diagnosis.symptom["id"] != sid:
                self.dropped_symptoms.add(self.diagnosis.symptom["id"])   # the operator says it was the wrong file
            if sid in self.pending_symptoms:
                self.pending_symptoms.remove(sid)
            self.dropped_symptoms.discard(sid)
            await self._start_diagnosis(sid, "scelta dall'operatore" if self.lang == "it" else "operator's choice")
            await self._maybe_reload_vocabulary()
        elif a == "drop_pending" and msg.get("symptom_id") in self.pending_symptoms:
            self.pending_symptoms.remove(msg["symptom_id"])
            self.dropped_symptoms.add(msg["symptom_id"])
            await self._emit_diagnosis()
        elif a == "book_slot" and msg.get("id") and self.diagnosis and self.diagnosis.outcome:
            zone, off, _ = str(msg["id"]).split(":")
            slot = next((x for x in CATALOG.service_slots(zone, from_day=int(off), limit=8) if x["id"] == msg["id"]), None)
            if slot:
                self.booking = slot
                self.fits_alone = False
                await self._confirm_outcome_parts()            # booking the fitting means the parts are ordered
                v = self._slot_view(slot)
                await self._agent(f"Prenotato: {v['label']} con {slot['technician']}." if self.lang == "it"
                                  else f"Booked: {v['label']} with {slot['technician']}.")
                await self._emit_diagnosis()
        elif a == "confirm_outcome_parts" and self.diagnosis and self.diagnosis.outcome:
            done = await self._confirm_outcome_parts()
            if done:
                await self._agent(("Ordine ricambi confermato: " if self.lang == "it" else "Parts order confirmed: ") + ", ".join(done))
            await self._emit_diagnosis()
        elif a == "fits_alone" and self.diagnosis and self.diagnosis.outcome:
            self.fits_alone = bool(msg.get("on", True))
            if self.fits_alone:
                self.booking = None
                await self._confirm_outcome_parts()            # the customer still buys the parts
                note = ("Il cliente monta i ricambi da solo: seconda chiamata con il service rifiutata." if self.lang == "it"
                        else "The customer fits the parts alone: service call declined.")
                if note not in self.notes:
                    self.notes.append(note)
                await self._agent(note)
            await self._emit_diagnosis()
        elif a == "cancel_booking" and self.booking:
            self.booking = None
            await self._agent("Prenotazione annullata." if self.lang == "it" else "Booking cancelled.")
            await self._emit_diagnosis()
        elif a == "spoken" and self.auto:
            await self.auto.spoken()
        elif a == "transcript" and self.relay and msg.get("text"):
            await self.voice_transcript(msg.get("role") or "customer", str(msg["text"]).strip(), bool(msg.get("interrupted")))
        elif a == "tool" and self.voice:
            result = await run_tool(self, msg.get("name") or "", msg.get("arguments") or {})
            self._log_decision("tool", name=msg.get("name"), arguments=msg.get("arguments"), result=result)
            await self.emit({"type": "tool_result", "call_id": msg.get("call_id"), "name": msg.get("name"),
                             "result": tool_result_text(result), "end": bool(result.get("end"))})
        elif a == "voice_end" and self.relay:
            await self.end()
        elif a in ("confirm_part", "dismiss_part") and msg.get("code") in self.cards:
            self.cards[msg["code"]]["status"] = "confirmed" if a == "confirm_part" else "dismissed"
            await self.emit({"type": "part_status", "code": msg["code"], "status": self.cards[msg["code"]]["status"]})
        elif a == "set_machine" and msg.get("model_id") in VOCAB.model_names:
            self.model_id = msg["model_id"]
            self.family = CONTEXT.family_of[self.model_id].capitalize()
            await self._agent(f"Macchina impostata dall'operatore: {VOCAB.model_names[self.model_id]}" if self.lang == "it"
                              else f"Machine set by the operator: {VOCAB.model_names[self.model_id]}")
            await self._emit_context()
            await self._maybe_reload_vocabulary()
        elif a == "set_outcome":
            self.outcome = {"kind": msg.get("kind"), "by": "operator"}
            await self._agent(f"Esito impostato dall'operatore: {msg.get('kind')}" if self.lang == "it"
                              else f"Outcome set by the operator: {msg.get('kind')}")
        elif a == "close_symptom" and self.diagnosis:
            kind = msg.get("kind", "remote")
            if kind in ("remote", "part_diy", "part_with_support", "technician"):
                self.diagnosis.outcome = Outcome(kind, [])
                self.diagnosis.current = None
                await self._on_outcome(self.diagnosis.outcome)
        elif a == "set_serial" and msg.get("serial"):
            await self._set_serial(re.sub(r"[^0-9A-Za-z]", "", msg["serial"]))

    # ------------------------------------------------------------------ voice agent helpers
    async def voice_transcript(self, role: str, text: str, interrupted: bool = False) -> None:
        """A final utterance relayed from the Voice Agent session: shown as a turn, remembered for the summary,
        and (for the customer) read for machine, serial and part codes like any other customer turn. An agent
        sentence cut short by the customer is kept, marked as interrupted."""
        self.voice_turn += 1
        tid = self.voice_turn * 100
        who = CUSTOMER if role == "customer" else OPERATOR if role == "operator" else "agent"
        from .agent.dialog import serials_in
        if who == CUSTOMER:
            self.last_customer_text = text
        if not self.machine:
            # a number said after the serial was asked, or any number that IS a machine in the installed base
            # (the operator reading it back: "mi conferma che è 051040?")
            for digits in serials_in(text):                 # "zero four four, eight zero one" -> 044801
                if (who == CUSTOMER and self.serial_asked) or (CATALOG.machine(digits) or {}).get("matched_exactly"):
                    await self._set_serial(digits)
                    if self.machine:
                        break
        if who in (OPERATOR, "agent") and _SERIAL_ASKED.search(text):
            self.serial_asked = 2                            # the answer may come one sentence later
        elif who == CUSTOMER and self.serial_asked:
            self.serial_asked -= 1
        if who == "agent":
            self.last_agent_text = text
            from .voice.agent import ready_to_hang_up
            if ready_to_hang_up(self, text):
                self.voice_done = True
                await self.emit({"type": "hangup"})            # the page ends the agent session after this sentence
        text, codes = canonicalize_codes(text)
        utt = {"id": tid, "raw": text, "text": text, "codes": codes, "fragments": [text], "confs": [1.0], "role": who,
               "speaker": None, "turn_ids": [tid], "min_conf": 1.0, "at": round(time.monotonic() - self.started, 1),
               "at_end": round(time.monotonic() - self.started, 1), "clear": None, "interrupted": bool(interrupted)}
        self.utterances.append(utt)
        self.turns[tid] = utt
        await self.emit({"type": "turn", "id": tid, "final": True, "text": text, "role": who, "speaker": None, "min_conf": 1.0,
                         "merged": 1, "interrupted": bool(interrupted)})
        if who in (CUSTOMER, OPERATOR) and self.assistant_on:
            if who == CUSTOMER and self.roleplay and self.clarify_on and self.customer_lang != "it":
                self.clarifier.submit(tid, text)                  # the clear Italian version, as on a real call
                await self.emit({"type": "clear_pending", "turn_id": tid})
            await self._assist(tid, text, who, 1.0, [text], utt)

    async def apply_model_words(self, text: str) -> None:
        """The agent passes the customer's words about the model: same detector as the live transcript."""
        hit = CONTEXT.detect(text)
        changed = False
        if hit.model_id and hit.model_id != self.model_id:
            self.model_id, self.family, changed = hit.model_id, hit.family, True
            await self._agent(f"Macchina riconosciuta: {VOCAB.model_names[hit.model_id]}" if self.lang == "it"
                              else f"Machine recognised: {VOCAB.model_names[hit.model_id]}")
            await self._open_manual(self.model_id)
        elif hit.family and not self.model_id and hit.family != self.family:
            self.family, changed = hit.family, True
        if hit.edition and hit.edition != self.edition:
            self.edition, changed = hit.edition, True
        if changed:
            await self._emit_context()
            await self._maybe_reload_vocabulary()

    async def adopt_machine_record(self) -> None:
        """The installed-base record decides model, edition and serial (what was heard only found it)."""
        m = self.machine
        changed = False
        if m["model_id"] != self.model_id:
            self.model_id, changed = m["model_id"], True
            self.family = CONTEXT.family_of[self.model_id].capitalize()
            await self._agent(f"Modello dalla scheda macchina: {VOCAB.model_names[self.model_id]}" if self.lang == "it"
                              else f"Model from the machine record: {VOCAB.model_names[self.model_id]}")
        if (m.get("edition") or None) != self.edition:
            self.edition, changed = m.get("edition"), True
        if m["serial"] != self.serial:
            self.serial, changed = m["serial"], True
        if changed:
            await self._emit_context()
            await self._maybe_reload_vocabulary()

    def symptom_candidates(self, text: str, k: int = 3) -> list[dict]:
        """The closest procedures for a description that did not open one by itself (for the agent to ask)."""
        if not SEMANTIC.ready:
            return []
        fam = CATALOG.family_models(self.family) if self.family and not self.model_id else None
        allowed = SEMANTIC.ids_for("symptom", self.model_id, fam)
        allowed = {n for n in allowed if not SEMANTIC.nodes[n].get("decoy")}
        out = []
        for m in SEMANTIC.search(text, allowed=allowed, k=k):
            if m.score >= 0.45:
                sid = m.node_id.split("/", 1)[1]
                out.append({"symptom_id": sid, "title": DEFECTS.symptoms[sid]["symptom_en"], "score": m.score})
        return out

    async def parts_for(self, query: str) -> list[dict]:
        """Part cards for a code or a description said by the customer (shown on the panel too)."""
        text, _ = canonicalize_codes(query)
        cards = []
        for c in extract_codes(text):
            cards += CATALOG.search_code(c.code, model_id=self.model_id, family=self.family, groups=self.groups)
        if not cards:
            cards = CATALOG.search_description(text, model_id=self.model_id, family=self.family, groups=self.groups)
        await self._add_cards(cards, None, source="voice-agent")
        return [self.cards[c.code] for c in cards if c.code in self.cards]

    async def _on_outcome(self, outcome: Outcome) -> None:
        self.outcome = {"kind": outcome.kind, "parts": outcome.parts, "by": "procedure"}
        if self.diagnosis and self.diagnosis.symptom["id"] not in self.closed_symptoms:
            self.closed_symptoms.append(self.diagnosis.symptom["id"])
        label = {"remote": "risolto da remoto", "part_diy": "ricambio, montaggio in autonomia",
                 "part_with_support": "ricambio con supporto del service", "technician": "tecnico"}[outcome.kind] \
            if self.lang == "it" else outcome.kind.replace("_", " ")
        await self._agent(f"Esito della procedura: {label}" + (f" ({', '.join(outcome.parts)})" if outcome.parts else "")
                          if self.lang == "it" else
                          f"Procedure outcome: {label}" + (f" ({', '.join(outcome.parts)})" if outcome.parts else ""))
        cards = [CATALOG.card(code, 0.95, "procedure", self.model_id) for code in outcome.parts if CATALOG.exists(code)]
        await self._add_cards(cards, None, source="procedure")
        await self._emit_diagnosis()                       # closed view: what to do now, parts priced, who pays
        self.pending_symptoms = [x for x in self.pending_symptoms if x not in self.closed_symptoms and x not in self.dropped_symptoms]
        if self.pending_symptoms:
            nxt = self.pending_symptoms[0]
            await self._agent(("In attesa: " + DEFECTS.symptoms[nxt]["symptom_it"] + ". Avvialo dal pannello quando sei pronto.") if self.lang == "it"
                              else "Waiting: " + DEFECTS.symptoms[nxt]["symptom_en"] + ". Start it from the panel when ready.")

    def _symptom_menu(self) -> list[dict]:
        """The procedures that apply to the machine in the call, for the operator to pick by hand."""
        out = []
        for sid, sym in DEFECTS.symptoms.items():
            if self.model_id and self.model_id not in sym["models"]:
                continue
            if self.family and not self.model_id and not any(m.startswith(self.family.lower()) for m in sym["models"]):
                continue
            out.append({"id": sid, "title": sym[f"symptom_{self.lang}"]})
        return out

    _WD_IT = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
    _MO_IT = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]

    def _slot_view(self, slot: dict) -> dict:
        """A calendar slot with a label in the operator's language and one in English (to read out)."""
        d = time.strptime(slot["date"], "%Y-%m-%d")
        it = f"{self._WD_IT[d.tm_wday]} {d.tm_mday} {self._MO_IT[d.tm_mon - 1]}"
        en = time.strftime("%a %d %b", d)
        return {**slot, "label": f"{it if self.lang == 'it' else en} {slot['start']}-{slot['end']}",
                "label_en": f"{en}, {slot['start']} to {slot['end']}"}

    @staticmethod
    def _max_days(delivery: list[dict]) -> int:
        """'2-4' working days -> 4; the remote fitting call is booked after the parts can be there."""
        nums = [int(x) for d in delivery[:1] for x in re.findall(r"\d+", str(d.get("days", "")))]
        return max(nums) if nums else 3

    def _booking_view(self, kind: str, parts: list[dict]) -> dict:
        """Which calendar to open for this outcome and its first free slots."""
        if kind == "technician":
            zone = CATALOG.service_zone(self.machine)
            slots = CATALOG.service_slots(zone, from_day=1) if zone else []
            return {"kind": "onsite", "zone": zone, "need_serial": not self.machine, "no_partner": bool(self.machine) and not zone,
                    "slots": [self._slot_view(x) for x in slots],
                    "booked": self._slot_view(self.booking) if self.booking and self.booking["kind"] == "onsite" else None}
        lead = max([self._max_days(c["delivery"]) for c in parts] + [0])
        slots = CATALOG.service_slots("REMOTE", from_day=lead + 1)
        return {"kind": "remote", "zone": "REMOTE", "need_serial": False, "no_partner": False,
                "slots": [self._slot_view(x) for x in slots],
                "booked": self._slot_view(self.booking) if self.booking and self.booking["kind"] == "remote" else None}

    CONSUMABLE_GROUPS = ("CR",)            # tablets, brushes, trims: never covered by the warranty

    def charge_for(self, code: str) -> dict:
        """What the customer pays for one part: the list price, unless the machine is under warranty and the part is
        one of the parts of the procedure's outcome (a repair). Consumables are always charged."""
        c = self.cards.get(code) or {}
        price = c.get("price_eur")
        in_repair = bool(self.diagnosis and self.diagnosis.outcome and code in self.diagnosis.outcome.parts)
        consumable = code[:2] in self.CONSUMABLE_GROUPS
        w = self.machine.get("in_warranty") if self.machine else None
        covered = bool(w and in_repair and not consumable)
        why = ("warranty" if covered else "consumable" if consumable else "out_of_warranty" if w is False
               else "not_in_repair" if w else "warranty_unknown")
        return {"list_price_eur": price, "covered_by_warranty": covered, "customer_pays_eur": 0.0 if covered else price, "why": why}

    def _next_step(self) -> dict:
        """What the operator does now that the procedure has an outcome: the parts with price and delivery, who pays,
        the service call or the technician's visit to book (with the free slots), and one English sentence to read."""
        o = self.diagnosis.outcome
        it = self.lang == "it"
        w = self.machine.get("in_warranty") if self.machine else None
        parts = [self.cards[c] for c in o.parts if c in self.cards]
        text = {"remote": ("Problema chiuso da remoto: nessun ricambio, nessun intervento.",
                           "Fixed remotely: no parts, no visit."),
                "part_diy": ("Spedire i ricambi qui sotto: il cliente li monta con la scheda.",
                             "Ship the parts below: the customer fits them with the sheet."),
                "part_with_support": ("Spedire i ricambi qui sotto e prenotare la seconda chiamata con il service per quando arrivano.",
                                      "Ship the parts below and book the second call with service for when they arrive."),
                "technician": ("Fissare l'intervento del tecnico.", "Book the technician's visit.")}[o.kind]
        wt, say_w = ("", ""), ""
        if o.kind != "remote":
            if w is True:
                wt = ("In garanzia: senza addebito.", "Under warranty: no charge.")
                say_w = "Your machine is under warranty, so there is no charge."
            elif w is False:
                wt = ("Fuori garanzia: ricambi e intervento a pagamento, inviare il preventivo.",
                      "Out of warranty: parts and labour are charged, send the quote.")
                say_w = "Your warranty has ended, so parts and labour are charged; we'll send you a quote."
            else:
                wt = ("Garanzia sconosciuta: chiedere la matricola.", "Warranty unknown: ask for the serial number.")
                say_w = "Can you give me the serial number, so I can check the warranty?"
        say_k = {"remote": "Good, that's fixed. If it comes back, call us with the serial number.",
                 "part_diy": "I'll ship the parts; you can fit them yourself with the sheet I'll send you.",
                 "part_with_support": "I'll ship the parts and we'll book a call with our service to fit them when they arrive.",
                 "technician": "We need to send a technician; we'll call you to book the visit."}[o.kind]
        fits_alone = self.fits_alone and o.kind == "part_with_support"
        if fits_alone:
            text = ("Spedire i ricambi qui sotto: il cliente li monta da solo (ha rifiutato la seconda chiamata; può "
                    "richiamare il service se serve aiuto).",
                    "Ship the parts below: the customer fits them alone (declined the service call; can call service back).")
            say_k = "I'll ship the parts; if you need help fitting them, call our service and we'll book a call with you."
        booking = self._booking_view(o.kind, parts) if o.kind in ("part_with_support", "technician") and not fits_alone else None
        if booking and booking["booked"]:
            b = booking["booked"]
            say_k = (f"Our technician can come on {b['label_en']}. Does that work for you?" if booking["kind"] == "onsite"
                     else f"We'll call you on {b['label_en']} to fit the parts together, once they have arrived. Does that work for you?")
        pay = self._payment(o.kind, w, parts)
        return {"kind": o.kind, "text": text[0] if it else text[1], "warranty": w, "warranty_text": wt[0] if it else wt[1],
                "say_en": " ".join(x for x in (say_w, say_k, pay["say_en"] if pay else "") if x).strip(), "booking": booking,
                "fits_alone": fits_alone, "payment": pay, "ship_to": self._ship_to() if parts else None,
                "parts_confirmed": bool(parts) and all(c["status"] == "confirmed" for c in parts),
                "parts": [{"code": c["code"], "description": c["description"], "description_en": c["description_en"],
                           "price_eur": c["price_eur"], "delivery": c["delivery"], "handling": c["handling"],
                           **self.charge_for(c["code"])} for c in parts]}

    def _payment(self, kind: str, warranty, parts: list[dict]) -> dict | None:
        """Who pays and how, after the call. Payment is never taken on the phone: a colleague reviews the work order
        and emails the quote with the payment instructions; the parts leave the warehouse when the payment is
        confirmed. Under warranty nothing is charged except consumables."""
        it = self.lang == "it"
        pays = round(sum(self.charge_for(c["code"])["customer_pays_eur"] or 0 for c in parts), 2)
        labour = kind in ("part_with_support", "technician") and warranty is False and not self.fits_alone
        if kind == "remote" or (not parts and kind != "technician"):
            return None
        if warranty is None:
            return {"status": "unknown", "text": "Chi paga dipende dalla garanzia: serve la matricola." if it
                    else "Who pays depends on the warranty: the serial number is needed.", "say_en": ""}
        if pays == 0 and not labour:
            return {"status": "free", "text": "Senza addebito: i ricambi partono appena la scheda è approvata." if it
                    else "No charge: the parts ship as soon as the work order is approved.",
                    "say_en": "There is nothing to pay: the parts ship as soon as the order is approved."}
        return {"status": "awaiting_payment", "amount_eur": pays, "labour": labour,
                "text": ("In attesa di pagamento: un collega revisiona la scheda e invia al cliente per email il preventivo "
                         "e le istruzioni di pagamento; i ricambi partono alla conferma del pagamento.") if it else
                        ("Awaiting payment: a colleague reviews the work order and emails the customer the quote and the "
                         "payment instructions; the parts ship once the payment is confirmed."),
                "say_en": "A colleague will review your case and email you the quote and the payment instructions shortly; "
                          "we ship the parts as soon as the payment is confirmed."}

    def _ship_to(self) -> str:
        m = self.machine
        if m:
            return f"{m['customer']}, {m['city']} ({m['country']})" + (" · indirizzo in anagrafica" if self.lang == "it" else " · address on file")
        return "indirizzo da chiedere al cliente" if self.lang == "it" else "address to ask the customer"

    async def _confirm_outcome_parts(self) -> list[str]:
        done = []
        if self.diagnosis and self.diagnosis.outcome:
            for code in self.diagnosis.outcome.parts:
                if code in self.cards and self.cards[code]["status"] == "proposed":
                    self.cards[code]["status"] = "confirmed"
                    await self.emit({"type": "part_status", "code": code, "status": "confirmed"})
                    done.append(code)
        return done

    # ------------------------------------------------------------------ emitters
    async def _on_clear(self, turn_id: int, text: str) -> None:
        said = self.turns.get(turn_id, {}).get("raw", "")
        if said and {c.code for c in extract_codes(text)} - {c.code for c in extract_codes(said)}:
            text = ""                                   # the small model invented a code: better no clear version
        if turn_id in self.turns:
            self.turns[turn_id]["clear"] = text
        await self.emit({"type": "clear", "turn_id": turn_id, "text": text})

    async def _agent(self, text: str) -> None:
        await self.emit({"type": "agent", "text": text, "at": round(time.monotonic() - self.started, 1)})

    async def _emit_context(self) -> None:
        await self.emit({"type": "context", "model_id": self.model_id,
                         "model": VOCAB.model_names.get(self.model_id), "family": self.family,
                         "edition": self.edition, "groups": self.groups, "serial": self.serial,
                         "symptoms": self._symptom_menu()})

    async def _emit_vocab(self, vocab) -> None:
        await self.emit({"type": "vocabulary", "phase": vocab.phase, "count": len(vocab.keyterms),
                         "reason": vocab.reason, "sample": vocab.keyterms[:14]})
        await self._agent(f"Vocabolario fase {vocab.phase}: {len(vocab.keyterms)} termini ({vocab.reason})" if self.lang == "it"
                          else f"Vocabulary phase {vocab.phase}: {len(vocab.keyterms)} keyterms ({vocab.reason})")

    async def _emit_diagnosis(self) -> None:
        if self.diagnosis:
            view = self.diagnosis.view(self.lang)
            step_ids = [st["id"] for st in self.diagnosis.symptom["steps"]]
            view["doc"] = {"page": f"symptoms/{self.diagnosis.symptom['id']}.md",
                           "anchor": f"passo-{step_ids.index(self.diagnosis.current) + 1}" if self.diagnosis.current else "procedura"}
            view["pending"] = [{"id": x, "title": DEFECTS.symptoms[x][f"symptom_{self.lang}"]} for x in self.pending_symptoms]
            view["alternatives"] = [x for x in self._symptom_menu() if x["id"] != self.diagnosis.symptom["id"]]
            if self.diagnosis.outcome:
                view["next"] = self._next_step()
            await self.emit({"type": "diagnosis", **view})

    async def _emit_summary(self) -> None:
        confirmed = [c for c in self.cards.values() if c["status"] == "confirmed"]
        await self.emit({"type": "summary", "summary": {
            "duration_s": round(time.monotonic() - self.started),
            "machine": VOCAB.model_names.get(self.model_id) or self.family, "edition": self.edition, "serial": self.serial,
            "symptom": self.diagnosis.symptom[f"symptom_{self.lang}"] if self.diagnosis else None,
            "steps": self.diagnosis.view(self.lang)["history"] if self.diagnosis else [],
            "maintenance_skipped": bool(self.diagnosis and self.diagnosis.maintenance_flags),
            "outcome": self.outcome,
            "next": self._next_step() if self.diagnosis and self.diagnosis.outcome else None,
            "booking": self._slot_view(self.booking) if self.booking else None,
            "notes": self.notes,
            "voice_agent": self.voice,
            "machine_record": self.machine,
            "parts_confirmed": [{"code": c["code"], "description": c["description"], "price_eur": c["price_eur"],
                                 "stock": c["stock"], **self.charge_for(c["code"])} for c in confirmed],
            "parts_proposed": [{"code": c["code"], "description": c["description"], "price_eur": c["price_eur"],
                                "compatible": c.get("compatible", True),
                                "in_outcome": bool(self.diagnosis and self.diagnosis.outcome and c["code"] in self.diagnosis.outcome.parts),
                                **self.charge_for(c["code"])} for c in self.cards.values() if c["status"] == "proposed"],
            "parts_dismissed": [c["code"] for c in self.cards.values() if c["status"] == "dismissed"],
            "transcript": [self.turns[k] for k in sorted(self.turns)],
            "diarization_check": self._diarization_report(),
        }})
