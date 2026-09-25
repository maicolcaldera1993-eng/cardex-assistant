"""Automatic first-line agent: the same defects files, part cards and calendar as the operator mode, but the
assistant asks the questions itself (text-to-speech) and reads the customer's answers to follow the procedure.
The operator's panel keeps showing every decision, so a human can watch (and later take over).

State machine, one state per thing the assistant is waiting for:
  greet -> problem -> step ... -> (serial) -> outcome -> (slot) -> closing -> bye
"""
from __future__ import annotations

import asyncio
import re
from typing import Callable

from ..core.symptoms import content_words

DEBOUNCE_S = 1.2           # the customer stopped talking this long ago: answer now
DEBOUNCE_LONG_S = 2.8      # ...unless the sentence looks unfinished ("No alarm" | "But it is cold.")
MAX_ATTEMPTS = 2           # misunderstood twice: spell the options out / move on
_END = re.compile(r"[.!?…]\s*$")

YES = {"yes", "yeah", "yep", "correct", "exactly", "fixed", "works", "working", "better", "good", "true", "perfect",
       "solved", "normal", "great", "sì", "si", "funziona", "risolto", "esatto", "giusto", "certo", "sí", "ja", "oui"}
ACK = {"ok", "okay", "sure", "alright", "fine", "please", "book", "go", "ahead", "right", "do", "it"}   # "ok, book it"
NO = {"no", "nope", "not", "never", "nothing", "still", "same", "doesn't", "dont", "don't", "isn't", "cannot", "can't",
      "cant", "unchanged", "worse", "dead", "damaged", "broken", "ancora", "niente", "nulla", "rotto", "rotta", "uguale"}
BYE = {"bye", "goodbye", "thanks", "thank", "that's all", "nothing else", "no thanks", "all good"}

DIGIT_WORDS = {"zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
               "seven": "7", "eight": "8", "nine": "9"}

GREETING = ("Sereni service, this is the automatic assistant. Which machine are you calling about, and what is it doing?")


def polarity(text: str) -> int:
    """+1 for a yes-like text, -1 for a no-like one, 0 when unclear ("okay, I did it, still weak" is not a yes)."""
    w = set(re.findall(r"[a-zàèéìòùí']+", text.lower()))
    y, n = len(w & YES), len(w & NO)
    return 0 if y == n else (1 if y > n else -1)


def affirmative(text: str) -> bool:
    """Did they agree? 'yes', 'ok book it', 'sure' count; anything with a no-word does not."""
    w = set(re.findall(r"[a-zàèéìòùí']+", text.lower()))
    return not (w & NO) and bool(w & (YES | ACK))


def digits_in(text: str) -> str:
    """'zero four one, three zero two' or '041302' -> '041302' (only when it looks like a serial)."""
    t = text.lower()
    for w, d in DIGIT_WORDS.items():
        t = re.sub(rf"\b{w}\b", d, t)
    digits = re.sub(r"\D", "", t)
    return digits if 5 <= len(digits) <= 8 else ""


def for_customer(text: str) -> str:
    """The steps are written for an operator who relays them; the assistant talks to the customer directly."""
    t = re.sub(r"^Have them ", "Please ", text)
    t = re.sub(r"\bhave them\b", "please", t)
    t = re.sub(r"\bHave the customer\b", "Please", t)
    t = re.sub(r"\bCan the customer\b", "Can you", t)
    t = re.sub(r"\bthe customer\b", "you", t)
    return t


_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
          "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
          "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
          "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
ORDINALS = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4}
# a word on one side in the answer and the other side in the label: they disagree (on/off, open/closed...)
ANTONYMS = [("on", "off"), ("open", "closed"), ("full", "empty"), ("hot", "cold"), ("weak", "strong"), ("yes", "no"),
            ("clicks", "silent"), ("drains", "stays"), ("flat", "domed"),
            ("acceso", "spento"), ("accesa", "spenta"), ("aperto", "chiuso"), ("pieno", "vuoto"), ("caldo", "freddo"),
            ("sì", "no"), ("forte", "debole")]
_SIDES = {w: i for pair in ANTONYMS for i, w in enumerate(pair)}
_PAIR = {w: pair for pair in ANTONYMS for w in pair}


def _negated(words: list[str]) -> set[str]:
    """Content words within three tokens after a negation ('not from the group' -> {'group'})."""
    out: set[str] = set()
    for k, w in enumerate(words):
        if w in ("not", "no", "never", "without", "isn't", "doesn't", "don't", "nor"):
            out |= content_words(" ".join(words[k + 1:k + 4]))
    return out


def numbers_in(text: str) -> set[str]:
    """Numbers said in words or digits: 'one hundred ten volts' -> {'110'}, 'at one point two' -> {'1.2'}."""
    out: set[str] = set()
    toks = re.findall(r"[a-z]+|\d+(?:\.\d+)?", text.lower())
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        if re.fullmatch(r"\d+(?:\.\d+)?", t):
            out.add(t.rstrip("0").rstrip(".") if "." in t else t)
            i += 1
            continue
        if t in _UNITS:
            val, j, seen, expect = 0, i, False, "any"          # "twenty" may take a unit, "fifteen" ends the number
            while j < n and (toks[j] in _UNITS or toks[j] in ("hundred", "and")):
                w = toks[j]
                if w == "hundred":
                    val = (val or 1) * 100
                    expect = "any"
                elif w == "and":
                    if expect != "any":
                        break
                else:
                    v = _UNITS[w]
                    if expect == "unit" and not (1 <= v <= 9):
                        break
                    if expect == "none":
                        break
                    val += v
                    expect = "unit" if 20 <= v <= 90 else "none"
                seen = seen or w != "and"
                j += 1
            if j + 1 < n and toks[j] == "point" and toks[j + 1] in _UNITS and _UNITS[toks[j + 1]] < 10:
                dec = []
                j += 1
                while j < n and toks[j] in _UNITS and _UNITS[toks[j]] < 10:
                    dec.append(str(_UNITS[toks[j]]))
                    j += 1
                out.add(f"{val}.{''.join(dec)}")
            elif seen:
                out.add(str(val))
            i = j
            continue
        i += 1
    return out


def classify_branch(text: str, branches: list[dict], similarities: Callable[[str, list[str]], list[float]] | None = None,
                    question: str = "") -> tuple[int | None, float]:
    """Which branch did the customer's answer pick? Meaning (embedding similarity with the branch labels) plus cheap
    signals that the embedding misses: numbers ('110 volts'), on/off-style antonyms, yes/no polarity, shared words,
    and 'the first one' after the options were read out. Returns (index, confidence) or (None, best score)."""
    labels = [b["label_en"] for b in branches]
    words = re.findall(r"[a-zàèéìòùí']+", text.lower())
    # "the first one", "the second", "la prima": an ordinal is a choice only as a short reply, not inside a sentence
    # ("book the first slot" is not option 1)
    if len(words) <= 4 or re.search(r"\b(first|second|third|fourth|fifth)\s+(one|option)\b", text.lower()):
        for w in words:
            if w in ORDINALS and ORDINALS[w] < len(labels):
                return ORDINALS[w], 1.0
    sims = similarities(text, labels) if similarities else [0.0] * len(labels)
    # yes/no counts only as an answer at the start ("No, still cold", "Yes, I hear it"), not inside a description
    # ("lights and buttons are on, but there are no alarms" is not a "no")
    # ... a "yes" also at the end ("... the boiler is full. It works."), where a "no" is usually a description ("no steam")
    tw, tn, pol_t = content_words(text), numbers_in(text), polarity(" ".join(words[:3]))
    if pol_t == 0 and polarity(" ".join(words[-3:])) > 0 and polarity(text) >= 0:
        pol_t = 1
    # "not from the group above": the words right after a negation count against a label that affirms them,
    # and for a label that negates them too ("Clicks, but no heat")
    negated = _negated(words)
    tw = tw - negated
    q_numbers = numbers_in(question) if question else set()
    def label_polarity(lab: str) -> int:
        # the label's yes/no is its first word ("No click"), or a "yes" anywhere ("Cleaned: fixed"); a "no" inside a
        # label describes ("Clicks, but no heat")
        p = polarity(lab.split()[0] if lab.split() else "")
        return 1 if p == 0 and polarity(lab) > 0 else p

    pols = [label_polarity(lab) for lab in labels]
    scores = []
    for k, (lab, sim) in enumerate(zip(labels, sims)):
        lw, ln, lwords = content_words(lab), numbers_in(lab), set(re.findall(r"[a-z']+", lab.lower()))
        l_neg = _negated(re.findall(r"[a-z']+", lab.lower()))
        s = sim
        if lw:
            s += 0.12 * len(lw & tw) / len(lw)
            s -= 0.15 * len((lw & negated) - l_neg)
            s += 0.15 * len(negated & l_neg)
        if ln and tn:
            # share of the label's numbers the customer said ("MB2, 230 V" vs "MB2, 110 V": the 2 alone is not enough)
            s += 0.5 * len(ln & tn) / len(ln) if ln & tn else -0.2
        for w in lwords & set(_SIDES):
            if w in words:
                s += 0.1                                          # same side of an on/off pair
            elif any(o in words for o in _PAIR[w] if o != w):
                s -= 0.3                                          # the opposite side
        pol_l = pols[k]
        if pol_t and pol_l:
            s += 0.2 if pol_t == pol_l else -0.2
        elif pol_t and -pol_t in pols and pol_t not in pols:
            s += 0.2          # "Yes, I hear the click": the other option is the explicit "No click", so this one is the yes
        if pol_l > 0 and len(lwords) <= 2 and q_numbers & tn:
            s += 0.5                                              # "Is it at 1.2 bar?" - "it is at 1.2": yes
        scores.append(s)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    best = order[0]
    margin = scores[best] - (scores[order[1]] if len(order) > 1 else 0.0)
    if scores[best] < 0.35 or margin < 0.08:
        return None, round(scores[best], 3)
    return best, round(scores[best], 3)


class AutoAgent:
    def __init__(self, session, tts, similarities: Callable[[str, list[str]], list[float]] | None = None):
        self.s = session
        self.tts = tts
        self.similarities = similarities
        self.state = "greet"
        self.buffer: list[str] = []
        self.attempts = 0
        self.slot_i = 0
        self.asked_serial = False
        self.speaking = False
        self.closing = False
        self._acting = False
        self._waited_more = False       # an unclear answer got one extra pause before the options are read out
        self._acked_serial = False
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------ voice
    async def say(self, text: str) -> None:
        try:
            key, seconds = await self.tts.synth(text)
            url = f"/api/tts/{key}.mp3"
        except Exception as e:  # noqa: BLE001 - no voice: the sentence still shows on screen
            key, seconds, url = "", 0.0, ""
            self.s._log_decision("tts_error", error=f"{type(e).__name__}: {e}")
        self.speaking = True
        await self.s.emit({"type": "speak", "id": key, "url": url, "text": text, "seconds": seconds})
        self.s._log_decision("agent_said", state=self.state, text=text)

    async def spoken(self) -> None:
        """The browser finished playing the last sentence."""
        self.speaking = False
        if self.closing:
            return await self.s.end()
        if self.buffer:
            self._arm()                                     # they answered before the sentence had finished playing

    # ------------------------------------------------------------------ listening
    async def start(self) -> None:
        await self.say(GREETING)
        self.state = "problem"

    def heard(self, text: str) -> None:
        """A final piece of what the customer said; act once they have paused. A piece without a full stop, or one
        the turn detector was not sure about, is probably followed by more: wait longer."""
        if self.closing:
            return
        self.buffer.append(text)
        sure = bool(_END.search(text)) and getattr(self.s, "last_eot_confidence", 1.0) >= 0.85
        self._arm(DEBOUNCE_S if sure else DEBOUNCE_LONG_S)

    def still_talking(self) -> None:
        """A partial transcript: the customer has not finished the sentence, do not answer yet."""
        if self._task and not self._acting:
            self._task.cancel()
            self._task = None

    def _arm(self, delay: float = DEBOUNCE_S) -> None:
        if self._task and not self._acting:
            self._task.cancel()
        if not self._acting:
            self._task = asyncio.create_task(self._later(delay))

    async def _later(self, delay: float = DEBOUNCE_S) -> None:
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        if self.speaking:
            return                                          # the customer's words arrive once the assistant is done
        text = " ".join(self.buffer).strip()
        self.buffer.clear()
        if not text:
            return
        self._acting = True                                 # a running answer is never cancelled by new words
        try:
            await self.act(text)
        finally:
            self._acting = False
            self._task = None
            if self.buffer and not self.speaking:
                self._arm()                                 # words that came in meanwhile

    # ------------------------------------------------------------------ the dialogue
    async def act(self, text: str) -> None:
        self.s._log_decision("agent_heard", state=self.state, text=text)
        handler = getattr(self, f"_in_{self.state}", None)
        if handler:
            await handler(text)

    def _step(self):
        d = self.s.diagnosis
        return d.step if d and d.current else None

    async def _ask_step(self, lead: str = "") -> None:
        st = self._step()
        self.state = "step"
        self.attempts = 0
        self._waited_more = False
        text = for_customer(st["text_en"])
        if st["kind"] == "do":
            text += " Tell me when you have done it, and what happened."
        await self.say((lead + " " + text).strip())

    async def _in_problem(self, text: str) -> None:
        if self._step():
            return await self._ask_step("Let's check.")
        # nothing recognised while the sentence was being said: read the whole answer once more
        await self.s._detect_symptom([text], semantic=True)
        if self._step():
            return await self._ask_step("Let's check.")
        if self.s.cards and not self.s.diagnosis:
            # they named a part: read what we know about it and offer to close
            c = list(self.s.cards.values())[-1]
            self.state = "closing"
            return await self.say(c["say_en"] + " Is there anything else?")
        self.attempts += 1
        if self.attempts == 1:
            return await self.say("I didn't catch the problem. In a few words: what is the machine doing, or not doing?")
        if self.attempts == 2:
            return await self.say("For example: weak coffee, a leak at the group, no heat, weak steam, wrong doses, "
                                  "or the machine is dead. Which one is closest?")
        self.state = "closing"
        self.closing = True
        await self.say("I'm sorry, I can't place this one. I'll pass you to an operator, who will call you back. Goodbye.")

    async def _in_step(self, text: str) -> None:
        st = self._step()
        if not st:
            return await self._after_procedure()
        # the question's numbers help only for a real question ("at 1.2 bar?"), not for a "5 cycles" instruction
        i, conf = classify_branch(text, st["branches"], self.similarities, question=st["text_en"] if st["kind"] == "ask" else "")
        self.s._log_decision("branch", step=st["id"], text=text, chosen=i, confidence=conf)
        if i is None:
            if digits_in(text) and self.s.machine and not self._acked_serial:
                # they gave the serial number instead: fine, note it and ask the step again
                self._acked_serial = True
                return await self.say(f"Thank you, I have your machine on file. {for_customer(st['text_en'])}")
            if not self._waited_more:
                # "No alarm." may well continue with "But it is cold.": give them a moment before asking again
                self._waited_more = True
                self.buffer.insert(0, text)
                return self._arm(DEBOUNCE_LONG_S)
            self.attempts += 1
            options = " or ".join(f"'{b['label_en']}'" for b in st["branches"])
            if self.attempts <= MAX_ATTEMPTS:
                return await self.say(f"Sorry, I didn't get that. Is it {options}?")
            self.state = "closing"
            self.closing = True
            return await self.say("I'll pass this to an operator, who will call you back. Goodbye.")
        self.attempts = 0
        self._waited_more = False
        self.s.diagnosis.answer(i)
        if self.s.diagnosis.outcome:
            await self.s._on_outcome(self.s.diagnosis.outcome)
            return await self._after_procedure()
        await self.s._emit_diagnosis()
        await self._ask_step()

    async def _after_procedure(self) -> None:
        """The procedure has an outcome: warranty needs the serial, then parts, then the calendar."""
        n = self.s._next_step()
        if n["kind"] != "remote" and not self.s.machine and not self.asked_serial:
            self.asked_serial = True
            self.state = "serial"
            self.attempts = 0
            return await self.say("Before we go on: can you give me the serial number? It's on the plate at the back of the machine.")
        parts = ""
        if n["parts"]:
            items = []
            for c in n["parts"]:
                d = (c.get("delivery") or [{}])[0]
                where = d.get("from", "").replace("FI-01 ", "").replace("NL-01 ", "")
                items.append(f"{c.get('description_en') or c['description']} ({c['code']}), {c['price_eur']:.0f} euros" +
                             (f", from {where} in {d['days']} working days" if d else ""))
            parts = " The parts are: " + "; ".join(items) + "."
        b = n.get("booking")
        if b and b["slots"] and not b["booked"]:
            self.slot_i = 0
            self.state = "slot"
            slot = b["slots"][0]
            what = "our technician can come" if b["kind"] == "onsite" else "we can call you back for the fitting"
            return await self.say(f"{n['say_en']}{parts} The first free slot is {slot['label_en']}: {what} then. Shall I book it?")
        self.state = "closing"
        await self.say(f"{n['say_en']}{parts} Is there anything else I can help you with?")

    async def _in_serial(self, text: str) -> None:
        digits = digits_in(text)
        if digits and not self.s.machine:
            await self.s._set_serial(digits)
        if self.s.machine or self.attempts >= 1:
            if not self.s.machine:
                await self.say("I couldn't find that serial number, we'll check it later.")
            return await self._after_procedure()
        self.attempts += 1
        await self.say("Sorry, I didn't get the number. Please say it digit by digit.")

    async def _in_slot(self, text: str) -> None:
        n = self.s._next_step()
        b = n.get("booking") or {}
        slots = b.get("slots") or []
        if affirmative(text) and self.slot_i < len(slots):
            slot = slots[self.slot_i]
            await self.s.control({"action": "book_slot", "id": slot["id"]})
            self.state = "closing"
            return await self.say(f"Booked: {slot['label_en']}, with {slot['technician']}. You'll get a confirmation by email. "
                                  "Is there anything else I can help you with?")
        self.slot_i += 1
        if self.slot_i < len(slots):
            slot = slots[self.slot_i]
            return await self.say(f"The next one is {slot['label_en']}. Does that work?")
        self.state = "closing"
        await self.say("No problem, we'll call you back to arrange it. Is there anything else I can help you with?")

    async def _in_closing(self, text: str) -> None:
        low = text.lower()
        if polarity(text) < 0 or any(k in low for k in BYE):
            self.closing = True
            return await self.say("Thank you for calling Sereni. Goodbye.")
        # something else: maybe a new fault was described (the detector may have opened it already)
        self.state = "problem"
        self.attempts = 0
        await self._in_problem(text)
