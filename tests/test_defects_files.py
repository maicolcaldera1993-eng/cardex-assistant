"""Every defects file must be a closed graph over the ERP: each branch leads to an existing step or to a valid
outcome, each part code exists and fits at least one of the symptom's machines, each step is reachable from
the start, and both languages are filled in."""
import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILES = sorted((ROOT / "data" / "kb" / "defects").glob("*.json"))
con = sqlite3.connect(ROOT / "data" / "sereni.db")
MODELS = {r[0] for r in con.execute("SELECT id FROM models")}
COMPAT: dict[str, set[str]] = {}
for code, mid in con.execute("SELECT code, model_id FROM compatibility"):
    COMPAT.setdefault(code, set()).add(mid)
OUTCOMES = {"remote", "part_diy", "part_with_support", "technician"}


def symptoms():
    for f in FILES:
        doc = json.loads(f.read_text(encoding="utf-8"))
        for s in doc["symptoms"]:
            yield pytest.param(doc["family"], s, id=s["id"])


def test_every_family_with_machines_has_a_file():
    families = {json.loads(f.read_text(encoding="utf-8"))["family"] for f in FILES}
    covered = {m for f in FILES for s in json.loads(f.read_text(encoding="utf-8"))["symptoms"] for m in s["models"]}
    assert {"Marea", "Onda", "Monda"} <= families
    assert covered == MODELS, f"models without any procedure: {MODELS - covered}"


def test_symptom_ids_are_unique():
    ids = [s["id"] for f in FILES for s in json.loads(f.read_text(encoding="utf-8"))["symptoms"]]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("family,s", list(symptoms()))
def test_symptom_is_a_closed_graph(family, s):
    assert set(s["models"]) <= MODELS
    for k in ("symptom_it", "symptom_en", "group", "start"):
        assert s.get(k), k
    assert len(s["spoken_forms"]) >= 5
    steps = {st["id"]: st for st in s["steps"]}
    assert len(steps) == len(s["steps"]), "duplicate step ids"
    assert s["start"] in steps
    reached, todo = set(), [s["start"]]
    for st in s["steps"]:
        assert st["kind"] in ("ask", "do")
        assert st["text_it"] and st["text_en"] and st["branches"]
        for p in st.get("parts", []):
            assert p in COMPAT, p
        for b in st["branches"]:
            assert b["label_it"] and b["label_en"]
            then = b["then"]
            if then.startswith("outcome:"):
                _, kind, *rest = then.split(":")
                assert kind in OUTCOMES, then
                if kind.startswith("part"):
                    assert rest and rest[0], f"{then}: parts missing"
                    for code in rest[0].split(","):
                        assert code in COMPAT, f"{code} not in the ERP"
                        assert COMPAT[code] & set(s["models"]), f"{code} fits none of {s['models']}"
            else:
                assert then in steps, f"{st['id']} -> {then}: no such step"
    while todo:
        cur = todo.pop()
        if cur in reached:
            continue
        reached.add(cur)
        todo += [b["then"] for b in steps[cur]["branches"] if not b["then"].startswith("outcome:")]
    assert reached == set(steps), f"unreachable steps: {set(steps) - reached}"
