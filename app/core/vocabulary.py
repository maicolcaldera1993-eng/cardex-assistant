"""The key terms every Voice Agent session listens for, and the model names Cardex prints.

AssemblyAI accepts at most 100 key terms per session, 50 characters each. A session is configured once, when the
call opens, so the list is the manufacturer's own vocabulary: model and edition names, then the trade words
customers use in English and the Italian ones that survive inside English sentences. Part codes are not listed:
a catalogue has hundreds, and spoken codes are rebuilt by app/core/normalizer.py.
"""
from __future__ import annotations

import json
from pathlib import Path

LEXICON = Path(__file__).resolve().parents[1] / "lexicon" / "pronunciation.json"
MAX_TERMS = 100
MAX_CHARS = 50

JARGON = [
    # english trade words the customer uses
    "group gasket", "shower screen", "portafilter", "blind filter", "backflush", "steam wand", "steam tip",
    "heating element", "level probe", "pressurestat", "safety valve", "anti-vacuum valve", "expansion valve",
    "check valve", "flowmeter", "fill solenoid", "three-way solenoid", "control board", "touchpad", "rotary pump",
    "vibration pump", "drip tray", "burrs", "hopper", "doser", "descaler", "crema",
    # italian words that survive inside english sentences
    "doccetta", "sottocoppa", "portafiltro", "caldaia", "pressostato", "centralina", "pulsantiera", "macine",
    "Sereni", "Cardex",
]


class VocabularyManager:
    def __init__(self, lexicon_path: Path = LEXICON):
        lex = json.loads(lexicon_path.read_text(encoding="utf-8"))
        self.model_names = {mid: m["name"] for mid, m in lex["models"].items()}
        self.editions = [e["name"] for e in lex["editions"].values()]
        self.keyterms = self._cap(list(self.model_names.values()) + self.editions + JARGON)

    @staticmethod
    def _cap(terms: list[str]) -> list[str]:
        out, seen = [], set()
        for t in terms:
            if t and len(t) <= MAX_CHARS and t.lower() not in seen:
                seen.add(t.lower())
                out.append(t)
            if len(out) == MAX_TERMS:
                break
        return out
