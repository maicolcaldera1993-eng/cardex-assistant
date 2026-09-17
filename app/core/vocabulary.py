"""The 100 keyterm slots, reloaded as the call moves on.

AssemblyAI accepts at most 100 keyterms per session (50 characters each) and lets
us replace them mid-stream with UpdateConfiguration. A catalog has thousands of
codes, so the slots follow the conversation:

  phase 1  nothing known     model names, edition, functional groups, trade jargon
  phase 2  model known       that model's most-ordered part codes, its names, jargon
  phase 3  group or symptom  the codes of that group first, the symptom's codes, then the rest
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .catalog import Catalog

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

BASE_PROMPT = (
    "Technical support phone call for Sereni, an Italian maker of professional espresso machines. "
    "An Italian help-desk operator and a foreign customer speak English with strong accents and mix in Italian words. "
    "Machine models are Marea, Giglio, Onda and Monda, with a Vaniglia edition. "
    "Part codes are two letters, a dash and four digits, such as GE-2140."
)


@dataclass
class Vocabulary:
    phase: int
    keyterms: list[str]
    prompt: str
    reason: str


class VocabularyManager:
    def __init__(self, catalog: Catalog, lexicon_path: Path = LEXICON):
        self.catalog = catalog
        lex = json.loads(lexicon_path.read_text(encoding="utf-8"))
        self.model_names = {mid: m["name"] for mid, m in lex["models"].items()}
        self.editions = [e["name"] for e in lex["editions"].values()]

    def _by_orders(self, codes: list[str]) -> list[str]:
        return sorted(codes, key=lambda c: -self.catalog._orders[c])

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

    def build(self, model_id: str | None = None, family: str | None = None, group: str | None = None,
              symptom_parts: list[str] | None = None) -> Vocabulary:
        names = list(self.model_names.values()) + self.editions
        if not model_id and not family:
            return Vocabulary(1, self._cap(names + JARGON), BASE_PROMPT, "call opened: manufacturer vocabulary")

        fam_models = self.catalog.family_models(family) if family and not model_id else None
        scope = self.catalog.codes_for(model_id, fam_models)
        label = self.model_names.get(model_id) or family
        own_names = [self.model_names[model_id]] if model_id else [n for n in names if family and n.startswith(family)]
        other_names = [n for n in names if n not in own_names]

        if not group and not symptom_parts:
            terms = own_names + self._by_orders(scope)[:70] + other_names + JARGON
            return Vocabulary(2, self._cap(terms), f"{BASE_PROMPT} The customer has a {label}.",
                              f"machine detected: {label}")

        first = [c for c in (symptom_parts or []) if c in scope]
        in_group = [c for c in self._by_orders(scope) if group and c.startswith(group + "-") and c not in first]
        rest = [c for c in self._by_orders(scope) if c not in first and c not in in_group]
        terms = own_names + first + in_group[:60] + rest[:30] + other_names + JARGON
        topic = f" They are discussing the {group} group." if group else ""
        return Vocabulary(3, self._cap(terms), f"{BASE_PROMPT} The customer has a {label}.{topic}",
                          f"topic narrowed: {label}" + (f", group {group}" if group else "") +
                          (f", {len(first)} symptom parts" if first else ""))
