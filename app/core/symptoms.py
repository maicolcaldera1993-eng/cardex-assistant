"""Known-defects files: find the symptom a customer is describing and walk the
step-by-step procedure. The operator chooses every branch; this module never
decides an outcome by itself.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz

DEFECTS_DIR = Path(__file__).resolve().parents[2] / "data" / "kb" / "defects"
OUTCOMES = ("remote", "part_diy", "part_with_support", "technician")


@dataclass
class Outcome:
    kind: str
    parts: list[str] = field(default_factory=list)


@dataclass
class SymptomHit:
    symptom_id: str
    family: str
    score: float
    matched: str


def parse_then(then: str) -> Outcome | str:
    """'outcome:part_diy:GE-2140,GE-2210' -> Outcome; anything else is a step id."""
    if not then.startswith("outcome:"):
        return then
    _, kind, *rest = then.split(":")
    assert kind in OUTCOMES, then
    return Outcome(kind, rest[0].split(",") if rest else [])


class DefectsLibrary:
    def __init__(self, directory: Path = DEFECTS_DIR):
        self.symptoms: dict[str, dict] = {}
        self.family_of: dict[str, str] = {}
        for f in sorted(directory.glob("*.json")):
            doc = json.loads(f.read_text(encoding="utf-8"))
            for s in doc["symptoms"]:
                s["_steps"] = {st["id"]: st for st in s["steps"]}
                self.symptoms[s["id"]] = s
                self.family_of[s["id"]] = doc["family"]

    def match(self, text: str, model_id: str | None = None, family: str | None = None,
              threshold: float = 0.86) -> SymptomHit | None:
        """Best symptom whose spoken forms appear in the text. Restricted to the model when known,
        otherwise to the family file, otherwise every file."""
        t = " " + re.sub(r"[^\w\sàèéìòù']", " ", text.lower()) + " "
        best: SymptomHit | None = None
        for sid, s in self.symptoms.items():
            if model_id and model_id not in s["models"]:
                continue
            if family and not model_id and self.family_of[sid].lower() != family.lower() \
                    and not any(m.startswith(family.lower()) for m in s["models"]):
                continue
            for form in s["spoken_forms"]:
                f = form.lower()
                if f" {f} " in t or f" {f}" in t and len(f) > 6:
                    score = 0.90 + min(len(f), 30) / 300          # longer exact phrases win
                else:
                    words = [w for w in f.split() if len(w) > 3]
                    if len(words) >= 2 and all(f" {w}" in t for w in words):
                        score = 0.88                              # "caffè esce slavato" for "caffè slavato"
                    elif len(f) >= 8:
                        score = fuzz.partial_ratio(f, t) / 100 * 0.92
                    else:
                        continue
                if score >= threshold and (best is None or score > best.score):
                    best = SymptomHit(sid, self.family_of[sid], round(score, 3), form)
        return best

    def start(self, symptom_id: str) -> "Diagnosis":
        return Diagnosis(self.symptoms[symptom_id])


class Diagnosis:
    """State of one guided procedure. `answer(i)` follows branch i of the current step."""

    def __init__(self, symptom: dict):
        self.symptom = symptom
        self.current: str | None = symptom["start"]
        self.outcome: Outcome | None = None
        self.history: list[dict] = []          # [{step, branch_label_it, branch_label_en}]
        self.maintenance_flags: list[str] = [] # step ids that revealed skipped maintenance
        self.suggested_parts: list[str] = []   # consumables suggested along the way

    @property
    def step(self) -> dict | None:
        return self.symptom["_steps"][self.current] if self.current else None

    def answer(self, branch_index: int) -> Outcome | dict:
        assert self.current, "diagnosis already closed"
        st = self.step
        br = st["branches"][branch_index]
        self.history.append({"step": st["id"], "kind": st["kind"], "text_it": st["text_it"], "text_en": st["text_en"],
                             "answer_it": br["label_it"], "answer_en": br["label_en"]})
        if st.get("maintenance") and branch_index == 0:
            self.maintenance_flags.append(st["id"])
            for p in st.get("parts", []):
                if p not in self.suggested_parts:
                    self.suggested_parts.append(p)
        nxt = parse_then(br["then"])
        if isinstance(nxt, Outcome):
            self.outcome, self.current = nxt, None
            return nxt
        self.current = nxt
        return self.step

    def view(self, lang: str = "it") -> dict:
        """What the operator's panel shows right now."""
        s = self.symptom
        base = {"symptom_id": s["id"], "symptom": s[f"symptom_{lang}"], "group": s["group"],
                "history": [{"text": h[f"text_{lang}"], "answer": h[f"answer_{lang}"]} for h in self.history],
                "maintenance_skipped": bool(self.maintenance_flags), "suggested_parts": self.suggested_parts}
        if self.outcome:
            return {**base, "done": True, "outcome": self.outcome.kind, "parts": self.outcome.parts}
        st = self.step
        return {**base, "done": False,
                "step": {"id": st["id"], "kind": st["kind"], "text": st[f"text_{lang}"],
                         "say_in_english": st["text_en"], "note": st.get(f"note_{lang}"),
                         "branches": [b[f"label_{lang}"] for b in st["branches"]]}}
