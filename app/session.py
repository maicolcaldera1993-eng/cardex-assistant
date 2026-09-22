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
from .core.semantic import AMBIGUITY_GAP, SECTION_THRESHOLD, SYMPTOM_THRESHOLD, SemanticIndex
from .core.symptoms import DefectsLibrary, Diagnosis, parse_then, Outcome
from .core.vocabulary import VocabularyManager
from .llm.clarify import Clarifier

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
DUETS = SAMPLES / "duet"
MAX_SESSION_SECONDS = int(os.getenv("MAX_SESSION_SECONDS", "300"))
INACTIVITY_TIMEOUT = int(os.getenv("INACTIVITY_TIMEOUT_SECONDS", "60"))
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

_SERIAL = re.compile(r"(?:serial(?: number)?|matricola)\D{0,15}((?:\d[\s\-]?){5,8})", re.I)


class CallSession:
    def __init__(self, api_key: str, emit: Emit, *, source: str = "mic", lang: str = "it"):
        self.api_key, self.emit, self.source, self.lang = api_key, emit, source, lang
        single = CUSTOMER if source == "mic" else _manifest_single(source)      # duet: two real voices, no single role
        self.duet: dict | None = None
        self.duet_playing = False
        self.duet_last_done = -10.0
        self.duet_windows: list[tuple[float, float]] = []
        self.diarization_agrees: list[tuple[str, str | None]] = []   # (role from timing, label from AssemblyAI)
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
        self.diagnosis: Diagnosis | None = None
        self.pending_symptoms: list[str] = []
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
                if self.duet:
                    await self.emit({"type": "duet_script", "id": self.duet["id"], "lines": self.duet["lines"]})
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
            if self.duet_playing:
                continue                      # the recorded customer is talking: the operator's mic stays out of the stream
            await self.asr.send_audio(chunk)
            self.stream_ms += len(chunk) / 32          # 16 kHz, 16-bit mono: 32 bytes per millisecond of audio

    async def play_duet_line(self, n: int) -> None:
        """Streams one recorded customer line into the same AssemblyAI session, at real-time pace, while the
        browser plays it through the speakers for the operator to hear. Two real voices, one stream."""
        if not self.duet or self.duet_playing or self._closing:
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
            self.duet_windows.append((start_ms, self.stream_ms))   # where, in stream time, the recorded customer spoke
            self.duet_playing = False
            self.duet_last_done = time.monotonic()
            await self.emit({"type": "duet", "state": "done", "n": n})

    def _diarization_report(self) -> dict | None:
        """Rehearsal only: did AssemblyAI's speaker labels agree with the roles we know from timing?"""
        if not self.diarization_agrees:
            return None
        by_role: dict[str, dict[str, int]] = {}
        for role, label in self.diarization_agrees:
            by_role.setdefault(role, {})[label or "PENDING"] = by_role.setdefault(role, {}).get(label or "PENDING", 0) + 1
        return by_role

    def _duet_role(self, words: list[dict]) -> str | None:
        """In rehearsal mode roles come from timing, not from diarization: a turn whose words fall inside a
        recorded-clip window is the customer, anything else is the operator at the microphone."""
        if not words:
            return None
        mid = (words[0].get("start", 0) + words[-1].get("end", 0)) / 2
        for a, b in self.duet_windows:
            if a - 400 <= mid <= b + 400:
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

    async def _on_turn(self, msg: dict) -> None:
        tid = msg.get("turn_order", 0)
        text = (msg.get("transcript") or "").strip()
        if not text:
            return
        if not msg.get("end_of_turn"):
            await self.emit({"type": "turn", "id": tid, "final": False, "text": text})
            return
        words = msg.get("words") or []
        role, label = self.roles.role_for(msg.get("speaker_label"))
        if self.duet:
            timed = self._duet_role(words)
            if timed:
                role = timed
                self.diarization_agrees.append((timed, msg.get("speaker_label")))
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
        if self.assistant_on:
            # the whole utterance is re-read every time it grows: "the code is..." [4 s] "GE-2140" is one thought
            # codes need the whole utterance (a code can straddle a pause); meaning is read on what was just said,
            # the last two fragments, otherwise a long utterance dilutes it
            recent = [canonicalize_codes(f)[0] for f in utt["fragments"][-2:]]
            if len(recent) == 2:
                recent = [recent[-1], " ".join(recent)]          # what was just said, then with its predecessor for context
            await self._assist(utt["id"], utt["text"], role, utt["confs"][-1], recent, utt)

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
            self.serial = re.sub(r"\D", "", m.group(1))
        if changed:
            await self._emit_context()

        if not await self._detect_symptom(recent):
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
        if not codes:
            cards += CATALOG.search_description(recent[0], model_id=self.model_id, family=self.family, groups=self.groups)
        await self._add_cards(cards, tid, source="voice")
        for c in cards:
            if c.reason in ("exact", "near-code", "description") and c.compatible:
                await self._open_doc(f"part/{c.code}", "code" if c.reason != "description" else "description")
                break
        await self._maybe_reload_vocabulary()

    # ------------------------------------------------------------------ meaning and documents
    async def _detect_symptom(self, texts: list[str]) -> bool:
        """Which known fault is this person describing? Meaning first (any language), exact phrases as a tie-breaker.
        Only the symptoms that apply to the machine being discussed are candidates."""
        exact = DEFECTS.match(texts[-1], model_id=self.model_id, family=self.family)
        chosen, heard, options = None, None, []
        if exact:
            chosen, heard = exact.symptom_id, exact.matched          # an exact spoken phrase is strong evidence
        elif SEMANTIC.ready:
            fam = CATALOG.family_models(self.family) if self.family and not self.model_id else None
            allowed = SEMANTIC.ids_for("symptom", self.model_id, fam)
            best: dict[str, object] = {}
            for q in texts:                                          # the last fragment alone, then with context
                for m in SEMANTIC.search(q, allowed=allowed, k=3):
                    if m.node_id not in best or m.score > best[m.node_id].score:
                        best[m.node_id] = m
            ms = sorted(best.values(), key=lambda m: m.score, reverse=True)
            if ms and SEMANTIC.nodes[ms[0].node_id].get("decoy"):
                ms = []                                              # "we have a problem with the machine": not a symptom yet
            ms = [m for m in ms if not SEMANTIC.nodes[m.node_id].get("decoy") and m.score >= SYMPTOM_THRESHOLD][:2]
            if ms:
                ids = [m.node_id.split("/", 1)[1] for m in ms]
                if len(ms) == 2 and ms[0].score - ms[1].score < AMBIGUITY_GAP:
                    options = ms
                else:
                    chosen, heard = ids[0], f"≈ {ms[0].ref}, {ms[0].score:.2f}"
        active = self.diagnosis.symptom["id"] if self.diagnosis else None

        if options:
            key = tuple(sorted(m.node_id for m in options))
            if key not in self.offered_choices and not (self.diagnosis and not self.diagnosis.outcome):
                self.offered_choices.add(key)
                await self.emit({"type": "symptom_choice", "options": [
                    {"symptom_id": m.node_id.split("/", 1)[1], "score": m.score,
                     "title": DEFECTS.symptoms[m.node_id.split("/", 1)[1]][f"symptom_{self.lang}"]} for m in options]})
                await self._agent("Due guasti possibili: scegli quello giusto nel pannello." if self.lang == "it"
                                  else "Two possible faults: pick the right one in the panel.")
            return True
        if not chosen:
            return False
        if chosen == active:
            return True
        if self.diagnosis and not self.diagnosis.outcome:
            if chosen not in self.pending_symptoms:
                self.pending_symptoms.append(chosen)
                await self._agent(f"Secondo sintomo in coda: {DEFECTS.symptoms[chosen][f'symptom_{self.lang}']}" if self.lang == "it"
                                  else f"Second symptom queued: {DEFECTS.symptoms[chosen]['symptom_en']}")
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
            "diarization_check": self._diarization_report(),
        }})
