"""Read-only access to the Sereni ERP (SQLite) plus part search.

Search order for something the customer said:
  1. exact code                       -> one card, or the replacement if superseded
  2. near code (one digit off, swap)  -> up to two candidates, ranked
  3. description / spoken alias       -> up to two candidates, ranked
Always restricted to the detected model when there is one, boosted by the
functional group being discussed and by how often the part is ordered.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz
from rapidfuzz.distance import DamerauLevenshtein

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "sereni.db"
LEXICON = ROOT / "app" / "lexicon" / "pronunciation.json"


_MODEL_WORDS = {"marea", "giglio", "onda", "monda", "evo", "plus", "digit", "mb2", "mb3", "vaniglia"}


@dataclass
class PartCard:
    code: str
    description_it: str
    description_en: str
    group: str
    score: float
    reason: str                         # "exact", "near-code", "description", "replacement"
    price_eur: float | None = None
    stock: dict[str, int] = field(default_factory=dict)
    compatible: bool = True             # with the detected model
    superseded_by: str | None = None
    requires: str | None = None
    note: str | None = None


class Catalog:
    def __init__(self, db_path: Path = DB_PATH, lexicon_path: Path = LEXICON):
        self.con = sqlite3.connect(db_path, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.spoken = json.loads(lexicon_path.read_text(encoding="utf-8"))["parts"]
        self._parts = {r["code"]: dict(r) for r in self.con.execute("SELECT * FROM parts")}
        self._orders = {r["code"]: r["orders_last_12m"] for r in self.con.execute("SELECT * FROM order_stats")}
        self._compat: dict[str, set[str]] = {}
        for r in self.con.execute("SELECT code, model_id FROM compatibility"):
            self._compat.setdefault(r["code"], set()).add(r["model_id"])
        self._max_orders = max(self._orders.values())

    # -- lookups ---------------------------------------------------------------
    def exists(self, code: str) -> bool:
        return code in self._parts

    def codes_for(self, model_id: str | None = None, family_models: list[str] | None = None, group: str | None = None) -> list[str]:
        models = {model_id} if model_id else set(family_models or [])
        out = []
        for code, p in self._parts.items():
            if models and not (self._compat[code] & models):
                continue
            if group and p["group_code"] != group:
                continue
            out.append(code)
        return out

    def family_models(self, family: str) -> list[str]:
        return [r["id"] for r in self.con.execute("SELECT id FROM models WHERE family=?", (family,))]

    def card(self, code: str, score: float, reason: str, model_id: str | None = None) -> PartCard:
        p = self._parts[code]
        price = self.con.execute("SELECT list_price_eur FROM prices WHERE code=? AND valid_to IS NULL", (code,)).fetchone()
        stock = {r["warehouse"]: r["quantity"] for r in self.con.execute("SELECT warehouse, quantity FROM stock WHERE code=?", (code,))}
        sup = self.con.execute("SELECT new_code, requires_code, note FROM supersessions WHERE old_code=?", (code,)).fetchone()
        return PartCard(code=code, description_it=p["description_it"], description_en=p["description_en"],
                        group=p["group_code"], score=round(score, 3), reason=reason,
                        price_eur=price[0] if price else None, stock=stock,
                        compatible=(model_id in self._compat[code]) if model_id else True,
                        superseded_by=sup["new_code"] if sup else None,
                        requires=sup["requires_code"] if sup and sup["requires_code"] and (not model_id or model_id in self._compat[sup["requires_code"]]) else None,
                        note=(sup["note"] if sup else None) or p["notes"])

    def _prior(self, code: str, groups: list[str]) -> float:
        boost = 0.05 * (self._orders[code] / self._max_orders)
        if groups and self._parts[code]["group_code"] in groups:
            boost += 0.05
        return boost

    # -- search by code ----------------------------------------------------------
    def search_code(self, candidate: str, model_id: str | None = None, family: str | None = None,
                    groups: list[str] | None = None, min_confidence: float | None = None) -> list[PartCard]:
        """candidate is canonical ('GE-2140') or weak ('GE-214'). Returns 0, 1 or 2 cards (3 with a replacement)."""
        groups = groups or []
        fam_models = self.family_models(family) if family and not model_id else None
        scope = set(self.codes_for(model_id, fam_models))
        cards: list[PartCard] = []
        if candidate in self._parts:
            cards.append(self.card(candidate, 1.0, "exact", model_id))
        prefix, _, digits = candidate.partition("-")
        near: list[tuple[float, str]] = []
        for code in self._parts:
            if code == candidate or not code.startswith(prefix + "-"):
                continue
            d = DamerauLevenshtein.distance(digits, code[3:])
            if d > 1:
                continue
            s = 0.80 + self._prior(code, groups)
            if scope and code not in scope:
                s -= 0.25
            if candidate in self._parts:
                # same kind of part as the code that was heard (gasket vs gasket) is the likelier slip
                s += 0.10 * fuzz.token_set_ratio(self._parts[candidate]["description_it"], self._parts[code]["description_it"]) / 100
            near.append((s, code))
        near.sort(reverse=True)
        exact_ok = bool(cards) and cards[0].compatible
        unsure = min_confidence is not None and min_confidence < 0.7
        if not cards:
            cards += [self.card(c, s, "near-code", model_id) for s, c in near[:2]]
        elif not exact_ok or unsure:
            # the code exists but does not fit this machine, or the ASR was unsure: show the best neighbour too
            cards += [self.card(c, s, "near-code", model_id) for s, c in near[:1] if (not scope or c in scope)]
        out = []
        for c in cards:
            out.append(c)
            if c.superseded_by:
                out.append(self.card(c.superseded_by, c.score, "replacement", model_id))
                # the adapter harness is only needed on the machines it fits (2024 builds)
                if c.requires and (not model_id or model_id in self._compat[c.requires]):
                    out.append(self.card(c.requires, c.score, "replacement", model_id))
        seen: set[str] = set()
        unique = []
        for c in sorted(out, key=lambda x: x.reason != "replacement" and x.reason != "exact"):  # keep exact + replacement first
            if c.code not in seen:
                seen.add(c.code)
                unique.append(c)
        return unique

    # -- search by words ---------------------------------------------------------
    def search_description(self, text: str, model_id: str | None = None, family: str | None = None,
                           groups: list[str] | None = None, threshold: float = 0.78) -> list[PartCard]:
        groups = groups or []
        fam_models = self.family_models(family) if family and not model_id else None
        text_l = text.lower()
        scored: list[tuple[float, str]] = []
        for code in self.codes_for(model_id, fam_models):
            best = 0.0
            for alias in self.spoken.get(code, {}).get("it", []) + self.spoken.get(code, {}).get("en", []):
                # "Onda group gasket" must also match a plain "group gasket" once the scope is the Onda
                a = " ".join(w for w in alias.lower().split() if w not in _MODEL_WORDS)
                if len(a) < 5:
                    continue
                if a in text_l:
                    best = max(best, 0.80 + min(len(a), 30) / 300)
                else:
                    best = max(best, fuzz.partial_ratio(a, text_l) / 100 * 0.85)
            if best >= threshold:
                scored.append((best + self._prior(code, groups), code))
        scored.sort(reverse=True)
        return [self.card(c, s, "description", model_id) for s, c in scored[:2]]
