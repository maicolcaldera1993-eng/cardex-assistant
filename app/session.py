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
from .core.normalizer import extract_codes
from .core.roles import CUSTOMER, OPERATOR, RoleTracker
from .core.symptoms import DefectsLibrary, Diagnosis, parse_then, Outcome
from .core.vocabulary import VocabularyManager
from .llm.clarify import Clarifier

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
MAX_SESSION_SECONDS = int(os.getenv("MAX_SESSION_SECONDS", "300"))
INACTIVITY_TIMEOUT = int(os.getenv("INACTIVITY_TIMEOUT_SECONDS", "60"))
CHUNK_MS = 50

# Loaded once, shared by every session (read-only).
CATALOG = Catalog()
CONTEXT = ContextDetector()
DEFECTS = DefectsLibrary()
VOCAB = VocabularyManager(CATALOG)

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

_SERIAL = re.compile(r"(?:serial(?: number)?|matricola)\D{0,15}((?:\d[\s\-]?){5,8})", re.I)


class CallSession:
    def __init__(self, api_key: str, emit: Emit, *, source: str = "mic", lang: str = "it"):
        self.api_key, self.emit, self.source, self.lang = api_key, emit, source, lang
        single = CUSTOMER if source == "mic" else _manifest_single(source)
        self.roles = RoleTracker(single_speaker_role=single)
        self.assistant_on, self.clarify_on = True, True
        self.model_id: str | None = None
        self.family: str | None = None
        self.edition: str | None = None
        self.groups: list[str] = []
        self.serial: str | None = None
        self.diagnosis: Diagnosis | None = None
        self.pending_symptoms: list[str] = []
        self.other_models: list[str] = []
        self.last_vocab_at = 0.0
        self.vocab_trigger: tuple | None = None
        self.cards: dict[str, dict] = {}
        self.turns: dict[int, dict] = {}
        self.vocab_phase = 0
        self.vocab_key: tuple | None = None
        self.outcome: dict | None = None
        self.started = time.monotonic()
        self.asr: AssemblyAIStream | None = None
        self.audio_q: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=400)
        self.clarifier = Clarifier(api_key, lang, self._on_clear)
        self._closing = False

    # ------------------------------------------------------------------ lifecycle
    async def run(self) -> None:
        vocab = VOCAB.build()
        self.vocab_phase, self.vocab_key = 1, (None, None, None, ())
        try:
            async with AssemblyAIStream(self.api_key, keyterms=vocab.keyterms, prompt=vocab.prompt,
                                        inactivity_timeout=INACTIVITY_TIMEOUT) as asr:
                self.asr = asr
                self.clarifier.start()
                await self.emit({"type": "session", "state": "open", "source": self.source, "lang": self.lang,
                                 "limits": {"max_seconds": MAX_SESSION_SECONDS}})
                await self._emit_vocab(vocab)
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
        await asyncio.sleep(MAX_SESSION_SECONDS)
        await self._agent("Limite di durata della demo raggiunto: chiudo la chiamata." if self.lang == "it"
                          else "Demo time limit reached: closing the call.")
        await self.end()

    async def end(self) -> None:
        if not self._closing and self.asr:
            self._closing = True
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
            await self.asr.send_audio(chunk)

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
            await self.asr.send_audio(pcm[i:i + step])
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
                tid = rev.get("turn_order")
                if tid in self.turns and rev.get("speaker_label"):
                    role, label = self.roles.role_for(rev["speaker_label"])
                    self.turns[tid].update(role=role, speaker=label)
        elif t == "Termination":
            await self._agent(f"Sessione chiusa: {msg.get('audio_duration_seconds')} s di audio." if self.lang == "it"
                              else f"Session closed: {msg.get('audio_duration_seconds')} s of audio.")
        elif t == "Error" or "error" in msg:
            await self.emit({"type": "error", "text": json.dumps(msg)[:300]})

    async def _on_turn(self, msg: dict) -> None:
        tid = msg.get("turn_order", 0)
        text = (msg.get("transcript") or "").strip()
        if not text:
            return
        final = bool(msg.get("end_of_turn"))
        role, label = (self.roles.role_for(msg.get("speaker_label")) if final
                       else (self.turns.get(tid, {}).get("role") or "?", msg.get("speaker_label")))
        words = msg.get("words") or []
        min_conf = round(min((w.get("confidence", 1.0) for w in words), default=1.0), 2)
        await self.emit({"type": "turn", "id": tid, "final": final, "text": text, "role": role,
                         "speaker": label, "min_conf": min_conf})
        if not final:
            return
        self.turns[tid] = {"id": tid, "text": text, "role": role, "speaker": label, "clear": None,
                           "at": round(time.monotonic() - self.started, 1)}
        if role == CUSTOMER and self.clarify_on:
            self.clarifier.submit(tid, text)
        if self.assistant_on:
            await self._assist(tid, text, role, min_conf)

    # ------------------------------------------------------------------ the assistant
    async def _assist(self, tid: int, text: str, role: str, min_conf: float) -> None:
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
            self.serial = re.sub(r"\D", "", m.group(1))
        if changed:
            await self._emit_context()

        if True:  # both voices: early diarization is shaky, and operators restate the symptom
            s = DEFECTS.match(text, model_id=self.model_id, family=self.family)
            if s and not (self.diagnosis and self.diagnosis.symptom["id"] == s.symptom_id):
                if self.diagnosis and not self.diagnosis.outcome:
                    if s.symptom_id not in self.pending_symptoms:
                        self.pending_symptoms.append(s.symptom_id)
                        await self._agent(f"Secondo sintomo in coda: {DEFECTS.symptoms[s.symptom_id][f'symptom_{self.lang}']}"
                                          if self.lang == "it" else
                                          f"Second symptom queued: {DEFECTS.symptoms[s.symptom_id]['symptom_en']}")
                else:
                    await self._start_diagnosis(s.symptom_id, s.matched)

        cards = []
        codes = extract_codes(text)
        for c in codes:
            cards += CATALOG.search_code(c.code, model_id=self.model_id, family=self.family, groups=self.groups,
                                         min_confidence=min_conf if c.exact_shape else 0.0)
        if not codes:
            cards += CATALOG.search_description(text, model_id=self.model_id, family=self.family, groups=self.groups)
        await self._add_cards(cards, tid, source="voice")
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

    async def _add_cards(self, cards, tid: int | None, source: str) -> None:
        new = []
        for c in cards:
            if c.code in self.cards:
                continue
            d = asdict(c)
            d.update(status="proposed", source=source, turn_id=tid,
                     description=d[f"description_{self.lang}"])
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
            await self._emit_diagnosis()
            if self.diagnosis.outcome:
                await self._on_outcome(self.diagnosis.outcome)
        elif a == "start_symptom" and msg.get("symptom_id") in DEFECTS.symptoms:
            await self._start_diagnosis(msg["symptom_id"])
            await self._maybe_reload_vocabulary()
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

    async def _on_outcome(self, outcome: Outcome) -> None:
        self.outcome = {"kind": outcome.kind, "parts": outcome.parts, "by": "procedure"}
        label = {"remote": "risolto da remoto", "part_diy": "ricambio, montaggio in autonomia",
                 "part_with_support": "ricambio con supporto del service", "technician": "tecnico"}[outcome.kind] \
            if self.lang == "it" else outcome.kind.replace("_", " ")
        await self._agent(f"Esito della procedura: {label}" + (f" ({', '.join(outcome.parts)})" if outcome.parts else "")
                          if self.lang == "it" else
                          f"Procedure outcome: {label}" + (f" ({', '.join(outcome.parts)})" if outcome.parts else ""))
        cards = [CATALOG.card(code, 0.95, "procedure", self.model_id) for code in outcome.parts if CATALOG.exists(code)]
        await self._add_cards(cards, None, source="procedure")
        if self.pending_symptoms:
            await self._start_diagnosis(self.pending_symptoms.pop(0))
            await self._maybe_reload_vocabulary()

    # ------------------------------------------------------------------ emitters
    async def _on_clear(self, turn_id: int, text: str) -> None:
        if turn_id in self.turns:
            self.turns[turn_id]["clear"] = text
        await self.emit({"type": "clear", "turn_id": turn_id, "text": text})

    async def _agent(self, text: str) -> None:
        await self.emit({"type": "agent", "text": text, "at": round(time.monotonic() - self.started, 1)})

    async def _emit_context(self) -> None:
        await self.emit({"type": "context", "model_id": self.model_id,
                         "model": VOCAB.model_names.get(self.model_id), "family": self.family,
                         "edition": self.edition, "groups": self.groups, "serial": self.serial})

    async def _emit_vocab(self, vocab) -> None:
        await self.emit({"type": "vocabulary", "phase": vocab.phase, "count": len(vocab.keyterms),
                         "reason": vocab.reason, "sample": vocab.keyterms[:14]})
        await self._agent(f"Vocabolario fase {vocab.phase}: {len(vocab.keyterms)} termini ({vocab.reason})" if self.lang == "it"
                          else f"Vocabulary phase {vocab.phase}: {len(vocab.keyterms)} keyterms ({vocab.reason})")

    async def _emit_diagnosis(self) -> None:
        if self.diagnosis:
            await self.emit({"type": "diagnosis", **self.diagnosis.view(self.lang)})

    async def _emit_summary(self) -> None:
        confirmed = [c for c in self.cards.values() if c["status"] == "confirmed"]
        await self.emit({"type": "summary", "summary": {
            "duration_s": round(time.monotonic() - self.started),
            "machine": VOCAB.model_names.get(self.model_id) or self.family, "edition": self.edition, "serial": self.serial,
            "symptom": self.diagnosis.symptom[f"symptom_{self.lang}"] if self.diagnosis else None,
            "steps": self.diagnosis.view(self.lang)["history"] if self.diagnosis else [],
            "maintenance_skipped": bool(self.diagnosis and self.diagnosis.maintenance_flags),
            "outcome": self.outcome,
            "parts_confirmed": [{"code": c["code"], "description": c["description"], "price_eur": c["price_eur"],
                                 "stock": c["stock"]} for c in confirmed],
            "parts_proposed": [{"code": c["code"], "description": c["description"], "price_eur": c["price_eur"]}
                               for c in self.cards.values() if c["status"] == "proposed"],
            "parts_dismissed": [c["code"] for c in self.cards.values() if c["status"] == "dismissed"],
            "transcript": [self.turns[k] for k in sorted(self.turns)],
        }})
