"""Builds the linked knowledge base the assistant navigates.

Every document is cut into SECTIONS with an anchor. Every section is a node that knows
which machines it belongs to (edges come from the ERP and the defects files, never from
text similarity). Output:

  data/kb/symptoms/<id>.md   one page per known symptom, generated from the defects files
  data/kb/index.json         the section index: id, kind, page, anchor, title, models, group,
                             parts, refs (the short texts the semantic matcher compares against)

    .venv/Scripts/python data/build_wiki.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

HERE = Path(__file__).parent
KB = HERE / "kb"
OUTCOME_IT = {"remote": "risolto da remoto", "part_diy": "ricambio, lo monta il cliente",
              "part_with_support": "ricambio con supporto del service", "technician": "tecnico"}


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", re.sub(r"[|*_`>#]", " ", text)).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?:;])\s+", flat) if len(s.strip()) > 25]


def manual_sections(path: Path, model_id: str) -> list[dict]:
    out, title, buf, level = [], None, [], 0
    lines = path.read_text(encoding="utf-8").splitlines()

    def flush():
        if title and "".join(buf).strip():
            body = "\n".join(buf).strip()
            topics = [t.strip() for m in re.finditer(r"<!--\s*topics:(.*?)-->", body, re.S) for t in re.split(r"[;,]", m.group(1)) if t.strip()]
            body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
            out.append({"id": f"manual/{model_id}#{slug(title)}", "kind": "manual", "page": f"manuals/{model_id}.md",
                        "anchor": slug(title), "title": title, "models": [model_id], "group": None, "parts":
                        sorted(set(re.findall(r"\b[A-Z]{2}-\d{4}\b", body))),
                        "refs": [title] + topics + sentences(body)[:12], "n_topics": len(topics)})

    for ln in lines:
        m = re.match(r"^(#{2,3})\s+(.*)", ln)
        if m:
            flush()
            title, buf, level = re.sub(r"^\d+\.\s*", "", m.group(2)).strip(), [], len(m.group(1))
        else:
            buf.append(ln)
    flush()
    return out


OUTCOME_EN = {"remote": "fixed remotely", "part_diy": "part, fitted by the customer",
              "part_with_support": "part with service support", "technician": "technician"}


def symptom_page(s: dict, family: str, part_desc: dict[str, str], lang: str = "it") -> str:
    """One page per known symptom, in Italian or English, with the SAME anchors in both languages
    (procedura, passo-1, passo-2...) so the panel can point at the current step whatever the language."""
    it = lang == "it"
    title, other = (s["symptom_it"], s["symptom_en"]) if it else (s["symptom_en"], s["symptom_it"])
    L = [f"# {title}", "", f"*{other}*", "",
         (f"Fascicolo difetti noti, famiglia {family}. Documento interno al service." if it else
          f"Known-defects file, {family} family. Internal service document."), "",
         ("## Come lo descrivono i clienti {#descrizioni}" if it else "## How customers describe it {#descrizioni}"), "",
         ", ".join(f"«{f}»" for f in s["spoken_forms"][:14]), "",
         ("## Procedura {#procedura}" if it else "## Procedure {#procedura}"), ""]
    for n, st in enumerate(s["steps"], 1):
        kind = ("Chiedere" if st["kind"] == "ask" else "Far fare") if it else ("Ask" if st["kind"] == "ask" else "Have them do")
        L += [f"### {n}. {kind}: {st['text_it'] if it else st['text_en']} {{#passo-{n}}}", "",
              f"*{st['text_en'] if it else st['text_it']}*", ""]
        note = st.get("note_it" if it else "note_en")
        if note:
            L += [f"> {note}", ""]
        for b in st["branches"]:
            then = b["then"]
            if then.startswith("outcome:"):
                _, kind_o, *rest = then.split(":")
                codes = rest[0].split(",") if rest else []
                tail = f"**{(OUTCOME_IT if it else OUTCOME_EN)[kind_o]}**" + \
                    (": " + ", ".join(f"{c} ({part_desc.get(c, '?')})" for c in codes) if codes else "")
            else:
                idx = next(i for i, x in enumerate(s["steps"], 1) if x["id"] == then)
                tail = f"vai al passo {idx}" if it else f"go to step {idx}"
            L.append(f"- {b['label_it'] if it else b['label_en']} → {tail}")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    con = sqlite3.connect(HERE / "sereni.db")
    part_desc = {c: d for c, d in con.execute("SELECT code, description_it FROM parts")}
    part_desc_en = {c: d for c, d in con.execute("SELECT code, description_en FROM parts")}
    compat: dict[str, list[str]] = {}
    for code, mid in con.execute("SELECT code, model_id FROM compatibility"):
        compat.setdefault(code, []).append(mid)
    index: list[dict] = []

    for f in sorted((KB / "manuals").glob("*.md")):
        if f.name.endswith(".en.md"):
            continue                                   # English twins share the Italian index
        index += manual_sections(f, f.stem)

    (KB / "symptoms").mkdir(exist_ok=True)
    for f in sorted((KB / "defects").glob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        for s in doc["symptoms"]:
            (KB / "symptoms" / f"{s['id']}.md").write_text(symptom_page(s, doc["family"], part_desc), encoding="utf-8")
            (KB / "symptoms" / f"{s['id']}.en.md").write_text(symptom_page(s, doc["family"], part_desc_en, "en"), encoding="utf-8")
            parts = sorted({c for st in s["steps"] for b in st["branches"] if b["then"].startswith("outcome:")
                            for c in (b["then"].split(":")[2].split(",") if b["then"].count(":") > 1 else [])})
            index.append({"id": f"symptom/{s['id']}", "kind": "symptom", "page": f"symptoms/{s['id']}.md", "anchor": "procedura",
                          "title": s["symptom_it"], "title_en": s["symptom_en"], "models": s["models"], "group": s["group"],
                          "parts": parts, "refs": [s["symptom_en"], s["symptom_it"]] + s["spoken_forms"]})

    # A decoy: generic "something is wrong" talk lands here instead of on a real symptom.
    index.append({"id": "symptom/_generic", "kind": "symptom", "page": None, "anchor": None, "title": "(generico)",
                  "title_en": "(generic)", "models": [m for n in index if n["kind"] == "symptom" for m in n["models"]],
                  "group": None, "parts": [], "decoy": True, "refs": [
                      "we have a problem with our coffee machine", "the machine has a problem", "something is wrong with the machine",
                      "the coffee machine is not working properly", "I am calling about the espresso machine", "we need help with the machine",
                      "abbiamo un problema con la macchina del caffè", "la macchina non funziona bene", "chiamo per la macchina",
                      "c'è qualcosa che non va con la macchina", "hello good morning this is the bar calling", "we have an issue since two weeks",
                      "the coffee is not good anymore", "il caffè non è più buono", "the coffee is bad",
                      "what is your problem", "what is the problem", "which is the problem", "tell me the problem",
                      "we have a problem with the machine since two weeks", "qual è il problema", "mi dica il problema"]})
    for f in sorted((KB / "parts").glob("*.md")):
        if f.name.endswith(".en.md"):
            continue
        code = f.stem
        index.append({"id": f"part/{code}", "kind": "part", "page": f"parts/{code}.md", "anchor": "montaggio",
                      "title": f"{code} — {part_desc.get(code, '')}", "models": compat.get(code, []),
                      "group": code[:2], "parts": [code], "refs": []})

    (KB / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    kinds: dict[str, int] = {}
    for n in index:
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    print(f"{len(index)} sections:", kinds)


if __name__ == "__main__":
    main()
