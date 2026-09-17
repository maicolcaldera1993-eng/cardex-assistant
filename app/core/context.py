"""What is the call about? Detects the machine model (or at least its family), the
colour edition and the functional group from a transcript turn.

Model names are Italian words that foreign customers mispronounce and the ASR
mis-hears ("giggly one plus", "Honda MB2", "Monday 65"). The lexicon of expected
variants is Cardex's own (app/lexicon/pronunciation.json), not the customer's ERP.
Pure logic, no I/O beyond loading the lexicon.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .normalizer import words_to_digits

LEXICON = Path(__file__).resolve().parents[1] / "lexicon" / "pronunciation.json"

# How each family name comes out of the ASR when spoken with a foreign accent.
FAMILY_VARIANTS = {
    "marea": ["marea", "maria", "mariah", "marie", "marya", "mareya", "maraya"],
    "giglio": ["giglio", "giggly", "jiggly", "gigli", "gilio", "jiglio", "gigly", "gigleo", "giglo", "jilio"],
    "onda": ["onda", "honda", "anda", "ondah"],
    "monda": ["monda", "monday", "mondo", "manda", "munda"],
}
SUFFIX_VARIANTS = {"evo": ["evo", "ivo", "eevo", "evil"], "digit": ["digit", "digital", "digits"], "plus": ["plus", "pluss"]}
EDITION_WORDS = {"vaniglia": ["vaniglia", "vanilla", "vaniglia edition", "vanilja"]}
ARTICLES = ("the ", "la ", "il ", "un ", "una ", "a ", "an ")

GROUP_KEYWORDS = {
    "GE": ["gruppo", "portafiltro", "doccetta", "sottocoppa", "guarnizione del gruppo", "erogazione", "filtro cieco",
           "group", "portafilter", "shower screen", "gasket", "basket", "brew", "shot", "crema"],
    "CA": ["caldaia", "resistenza", "sonda", "livello", "pressostato", "valvola di sicurezza", "antidepressione", "non scalda",
           "boiler", "heating element", "level probe", "pressurestat", "safety valve", "vacuum", "not heating"],
    "ID": ["pompa", "flussometro", "valvola di espansione", "ritegno", "carico", "scarico", "tubo", "raccordo",
           "pump", "flowmeter", "expansion valve", "check valve", "fill", "drain", "hose", "fitting"],
    "VA": ["vapore", "lancia", "acqua calda", "miscelatore", "steam", "wand", "hot water", "milk"],
    "EL": ["centralina", "scheda", "pulsantiera", "tasto", "display", "fusibile", "bobina", "teleruttore",
           "control board", "touchpad", "keypad", "button", "fuse", "coil", "contactor"],
    "CR": ["pannello", "vaschetta", "griglia", "scaldatazze", "panel", "drip tray", "cup warmer", "tamper"],
    "MC": ["macine", "macinacaffè", "macinino", "dosatore", "campana", "burrs", "grinder", "doser", "hopper", "grind"],
}
GRINDER_HINTS = GROUP_KEYWORDS["MC"]
MACHINE_HINTS = GROUP_KEYWORDS["CA"] + GROUP_KEYWORDS["VA"] + ["gruppo", "group", "portafilter", "portafiltro"]


@dataclass
class ContextHit:
    model_id: str | None = None      # exact model, e.g. "marea-2-plus"
    family: str | None = None        # "Marea" even when the version was not said
    edition: str | None = None       # "vaniglia"
    groups: list[str] = field(default_factory=list)
    matched: str | None = None       # the words that triggered the model hit
    via_variant: bool = False        # True when a mis-hearing variant was used ("honda mb2")


def _strip_article(s: str) -> str:
    for a in ARTICLES:
        if s.startswith(a):
            return s[len(a):]
    return s


class ContextDetector:
    def __init__(self, lexicon_path: Path = LEXICON):
        lex = json.loads(lexicon_path.read_text(encoding="utf-8"))
        self.models = lex["models"]
        self.alias_to_model: dict[str, tuple[str, bool]] = {}   # alias -> (model_id, via_variant)
        self.family_words: dict[str, tuple[str, bool]] = {}     # word -> (family key, via_variant)
        self.family_of: dict[str, str] = {}
        self.suffix_to_models: dict[str, list[str]] = {}
        for mid, m in self.models.items():
            canon = words_to_digits(m["name"])                   # "marea 2 plus", "onda mb2 evo"
            fam, _, suffix = canon.partition(" ")
            self.family_of[mid] = fam
            self.suffix_to_models.setdefault(suffix, []).append(mid)
            for fam_word in FAMILY_VARIANTS[fam]:
                for suf in self._suffix_variants(suffix):
                    self.alias_to_model.setdefault(f"{fam_word} {suf}", (mid, fam_word != fam or suf != suffix))
            for extra in m.get("spoken", []) + m.get("misheard", []):
                self.alias_to_model.setdefault(_strip_article(words_to_digits(extra)), (mid, True))
        for fam, words in FAMILY_VARIANTS.items():
            for w in words:
                self.family_words[w] = (fam, w != fam)
        self._aliases = sorted(self.alias_to_model, key=len, reverse=True)

    @staticmethod
    def _suffix_variants(suffix: str) -> list[str]:
        out = {suffix}
        for word, variants in SUFFIX_VARIANTS.items():
            for s in list(out):
                if re.search(rf"\b{word}\b", s):
                    out |= {re.sub(rf"\b{word}\b", v, s) for v in variants}
        return sorted(out)

    def detect(self, text: str) -> ContextHit:
        norm = " " + words_to_digits(text) + " "
        hit = ContextHit()
        hit.groups = [g for g, kws in GROUP_KEYWORDS.items() if any(f" {k}" in norm.replace("'", " ") for k in kws)]
        for ed, words in EDITION_WORDS.items():
            if any(re.search(rf"\b{re.escape(w)}\b", norm) for w in words):
                hit.edition = ed
        for alias in self._aliases:                               # longest first: "marea 2 plus" before "marea 2"
            if re.search(rf"\b{re.escape(alias)}\b", norm):
                mid, via = self.alias_to_model[alias]
                hit.model_id, hit.matched, hit.via_variant = mid, alias, via
                hit.family = self.family_of[mid].capitalize()
                break
        if hit.model_id is None:
            for word, (fam, via) in self.family_words.items():
                if re.search(rf"\b{word}\b", norm):
                    # "vanilla" sentences often contain nothing else; "monday" is also a day: need a machine-ish context
                    if word in ("monday", "mondo", "maria", "marie", "manda") and not (hit.groups or re.search(rf"\b{word}\s+\d", norm)):
                        continue
                    hit.family, hit.matched, hit.via_variant = fam.capitalize(), word, via
                    break
        # Onda / Monda differ by one consonant: let the topic break the tie when no version was heard.
        if hit.model_id is None and hit.family in ("Onda", "Monda"):
            grinder = any(f" {k}" in norm for k in GRINDER_HINTS)
            machine = any(f" {k}" in norm for k in MACHINE_HINTS)
            if grinder and not machine:
                hit.family = "Monda"
            elif machine and not grinder:
                hit.family = "Onda"
        return hit
