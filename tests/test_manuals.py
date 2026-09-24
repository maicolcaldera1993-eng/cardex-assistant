"""Every model has a manual in Italian and English; the English headings carry the Italian anchors; every part
code a manual quotes exists in the ERP and fits that model."""
import re
import sqlite3
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANUALS = ROOT / "data" / "kb" / "manuals"
con = sqlite3.connect(ROOT / "data" / "sereni.db")
MODELS = sorted(r[0] for r in con.execute("SELECT id FROM models"))
COMPAT: dict[str, set[str]] = {}
for code, mid in con.execute("SELECT code, model_id FROM compatibility"):
    COMPAT.setdefault(code, set()).add(mid)


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


@pytest.mark.parametrize("mid", MODELS)
def test_manual_in_both_languages_with_shared_anchors(mid):
    it, en = MANUALS / f"{mid}.md", MANUALS / f"{mid}.en.md"
    assert it.exists() and en.exists()
    it_anchors = [slug(re.sub(r"^\d+\.\s*", "", m.group(2))) for m in re.finditer(r"^(#{2,3})\s+(.*)$", it.read_text(encoding="utf-8"), re.M)]
    en_anchors = re.findall(r"^#{2,3} .*\{#([a-z0-9-]+)\}\s*$", en.read_text(encoding="utf-8"), re.M)
    assert it_anchors == en_anchors


@pytest.mark.parametrize("mid", MODELS)
def test_manual_quotes_only_parts_that_fit(mid):
    for f in (MANUALS / f"{mid}.md", MANUALS / f"{mid}.en.md"):
        codes = set(re.findall(r"\b[A-Z]{2}-\d{4}\b", f.read_text(encoding="utf-8")))
        wrong = sorted(c for c in codes if mid not in COMPAT.get(c, set()))
        assert not wrong, f"{f.name}: {wrong}"
