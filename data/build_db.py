"""Builds the fictional ERP database data/sereni.db from build_catalog.py data,
plus the generated product sheets in data/kb/parts/. Also refreshes catalog.json
and models.json.

    .venv/Scripts/python data/build_db.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import build_catalog as bc  # noqa: E402
from part_notes import NOTES  # noqa: E402

DB = HERE / "sereni.db"
KB = HERE / "kb"

SUPPLIERS = [
    ("guarnital", "Guarnital Modena", "Modena", "IT", 5),
    ("valvotecnica", "Valvotecnica Brianza", "Monza", "IT", 7),
    ("rotopompe", "Rotopompe Padova", "Padova", "IT", 10),
    ("termores", "Termoresistenze Vicenza", "Vicenza", "IT", 12),
    ("elettra", "Elettra Schede Bologna", "Bologna", "IT", 15),
    ("inoxlucca", "Inox Lavorazioni Lucca", "Lucca", "IT", 20),
    ("macprecisa", "Macinatura Precisa Torino", "Torino", "IT", 14),
    ("ottonevaldelsa", "Fonderia Ottone Valdelsa", "Poggibonsi", "IT", 25),
    ("caldaietoscane", "Caldaie Toscane", "Prato", "IT", 30),
]

WAREHOUSES = ["FI-01 Firenze", "NL-01 Rotterdam hub"]

MODEL_GROUPS = {m[0]: max(m[5], 1) for m in bc.MODELS}
PER_GROUP_KEYWORDS = ("sottocoppa", "doccetta", "portadoccia", "elettrovalvola gruppo", "gigleur", "preinfusione",
                      "camera", "corpo gruppo", "kit revisione gruppo", "sonda temperatura gruppo", "camicia gruppo",
                      "tubo rame scambiatore", "flussometro", "turbina", "sensore hall", "pulsantiera", "pannello touch",
                      "bobina elettrovalvola", "caldaia caffè", "resistenza caldaia caffè", "caldaietta", "portafiltro")


def h(s: str, n: int) -> int:
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % n


def supplier_for(p: dict) -> str:
    d = p["description_it"].lower()
    g = p["group"]
    if g == "MC":
        return "macprecisa"
    if any(k in d for k in ("guarnizione", "or ", "oring", "gommino", "tenute", "membrana", "isolante", "kit or")):
        return "guarnital"
    if any(k in d for k in ("elettrovalvola", "valvola", "rubinetto", "joystick", "miscelatore", "riduttore", "by-pass")):
        return "valvotecnica"
    if any(k in d for k in ("pompa", "motore", "giunto", "condensatore", "fascetta")):
        return "rotopompe"
    if "resistenza" in d or "termostato" in d:
        return "termores"
    if g == "EL" or any(k in d for k in ("sonda", "trasduttore", "flussometro", "sensore", "led")):
        return "elettra"
    if g == "CR" or any(k in d for k in ("pannello", "griglia", "vaschetta", "lancia", "terminale", "doccetta", "inox")):
        return "inoxlucca"
    if any(k in d for k in ("caldaia", "scambiatore", "coibentazione")):
        return "caldaietoscane"
    return "ottonevaldelsa"


def specs_for(p: dict) -> list[tuple[str, str]]:
    d = p["description_it"]
    out = []
    if p["voltage"]:
        out.append(("tensione", p["voltage"]))
    m = re.search(r"(\d+)\s*W\b", d)
    if m:
        out.append(("potenza", f"{m.group(1)} W"))
    m = re.search(r"(\d+(?:,\d+)?)\s*mm", d)
    if m:
        out.append(("misura", f"{m.group(1)} mm"))
    m = re.search(r"(\d+(?:,\d+)?)\s*(?:L\b|L/h)", d)
    if m:
        out.append(("capacità" if "L/h" not in d else "portata", m.group(0)))
    m = re.search(r"(\d+(?:,\d+)?(?:–\d+(?:,\d+)?)?)\s*bar", d)
    if m:
        out.append(("pressione", f"{m.group(1)} bar"))
    for mat in ("inox", "ottone", "rame", "EPDM", "silicone", "teflon", "policarbonato", "alluminio", "acciaio temprato", "fibra"):
        if mat.lower() in d.lower():
            out.append(("materiale", mat))
            break
    m = re.search(r"\(kit (?:di )?(\d+)\)|\(kit (\d+)\)|barattolo (\d+)", d)
    if m:
        out.append(("confezione", next(g for g in m.groups() if g) + " pz"))
    return out


def qty_for(p: dict, model_id: str) -> int:
    d = p["description_it"].lower()
    if any(k in d for k in PER_GROUP_KEYWORDS) and "kit" not in d.split("(")[0]:
        return MODEL_GROUPS[model_id]
    return 1


def orders_for(p: dict) -> int:
    base = {1: 900, 2: 300, 3: 90, 4: 25, 5: 5}[p["order_rank"]]
    return base + h(p["code"], base // 2 + 1)


def build_db() -> None:
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.executescript("""
    CREATE TABLE models (id TEXT PRIMARY KEY, name TEXT, family TEXT, year INTEGER, type TEXT, groups INTEGER, notes TEXT);
    CREATE TABLE editions (id TEXT PRIMARY KEY, name TEXT, finish TEXT, notes TEXT);
    CREATE TABLE edition_models (edition_id TEXT, model_id TEXT);
    CREATE TABLE suppliers (id TEXT PRIMARY KEY, name TEXT, city TEXT, country TEXT, lead_time_days INTEGER);
    CREATE TABLE parts (code TEXT PRIMARY KEY, group_code TEXT, description_it TEXT, description_en TEXT,
                        unit TEXT, weight_g INTEGER, supplier_id TEXT, mounting_notes TEXT, notes TEXT);
    CREATE TABLE part_specs (code TEXT, key TEXT, value TEXT);
    CREATE TABLE compatibility (code TEXT, model_id TEXT, quantity_per_machine INTEGER);
    CREATE TABLE supersessions (old_code TEXT, new_code TEXT, since TEXT, requires_code TEXT, note TEXT);
    CREATE TABLE stock (code TEXT, warehouse TEXT, quantity INTEGER, updated_at TEXT);
    CREATE TABLE prices (code TEXT, list_price_eur REAL, valid_from TEXT, valid_to TEXT);
    CREATE TABLE order_stats (code TEXT PRIMARY KEY, orders_last_12m INTEGER);
    CREATE TABLE documents (id TEXT PRIMARY KEY, kind TEXT, model_id TEXT, family TEXT, code TEXT, path TEXT, title TEXT, internal INTEGER);
    CREATE INDEX ix_compat_model ON compatibility(model_id);
    """)
    for (i, n, f, y, t, g, aliases) in bc.MODELS:
        c.execute("INSERT INTO models VALUES (?,?,?,?,?,?,?)", (i, n, f, y, t, g, None))
    for e in bc.EDITIONS:
        eid = e["name"].lower()
        c.execute("INSERT INTO editions VALUES (?,?,?,?)", (eid, e["name"], e["finish"], "Finitura crema; cambia solo carrozzeria, manico e manopole."))
        for m in e["models"]:
            c.execute("INSERT INTO edition_models VALUES (?,?)", (eid, m))
    c.executemany("INSERT INTO suppliers VALUES (?,?,?,?,?)", SUPPLIERS)

    for p in bc.PARTS:
        notes = NOTES.get(p["code"], {})
        weight = {1: 30, 2: 120, 3: 250, 4: 600, 5: 4000}[p["order_rank"]] + h(p["code"] + "w", 40)
        c.execute("INSERT INTO parts VALUES (?,?,?,?,?,?,?,?,?)", (
            p["code"], p["group"], p["description_it"], p["description_en"], "pz", weight,
            supplier_for(p), notes.get("mounting"), notes.get("notes") or p["note"]))
        for k, v in specs_for(p):
            c.execute("INSERT INTO part_specs VALUES (?,?,?)", (p["code"], k, v))
        for m in p["models"]:
            c.execute("INSERT INTO compatibility VALUES (?,?,?)", (p["code"], m, qty_for(p, m)))
        fi = round(p["stock"] * 0.6)
        nl = p["stock"] - fi if p["order_rank"] <= 4 else 0
        c.execute("INSERT INTO stock VALUES (?,?,?,?)", (p["code"], WAREHOUSES[0], fi + (p["stock"] - fi - nl), "2026-09-15"))
        c.execute("INSERT INTO stock VALUES (?,?,?,?)", (p["code"], WAREHOUSES[1], nl, "2026-09-15"))
        c.execute("INSERT INTO prices VALUES (?,?,?,?)", (p["code"], p["price_eur"], "2026-01-01", None))
        c.execute("INSERT INTO order_stats VALUES (?,?)", (p["code"], orders_for(p)))
        c.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)", (
            f"sheet-{p['code']}", "part_sheet", None, None, p["code"], f"kb/parts/{p['code']}.md",
            f"Scheda prodotto {p['code']}", 0))

    c.execute("INSERT INTO supersessions VALUES (?,?,?,?,?)",
              ("EL-3010", "EL-3012", "2025-03-01", "EL-3036", "Centralina v1 fuori produzione. Sulle macchine 2024 serve il cablaggio adattatore EL-3036."))
    c.execute("INSERT INTO supersessions VALUES (?,?,?,?,?)",
              ("EL-3011", "EL-3012", "2025-04-15", None, "Primo lotto v2 con bug del conteggio flussometro. Sostituzione diretta."))
    c.execute("INSERT INTO supersessions VALUES (?,?,?,?,?)",
              ("CA-1300", "CA-1300", None, None, None))  # placeholder removed below
    c.execute("DELETE FROM supersessions WHERE old_code = new_code")

    for (i, n, f, *_rest) in bc.MODELS:
        c.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                  (f"manual-{i}", "manual", i, f, None, f"kb/manuals/{i}.md", f"Libretto d'uso e manutenzione {n}", 0))
    for fam in sorted({m[2] for m in bc.MODELS}):
        c.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                  (f"defects-{fam.lower()}", "defects", None, fam, None, f"kb/defects/{fam.lower()}.json",
                   f"Fascicolo difetti noti famiglia {fam}", 1))
    con.commit()
    con.close()


def write_lexicon() -> None:
    """Cardex's own pronunciation lexicon: how customers say and how the ASR mis-hears
    model, edition and part names. Application knowledge, deliberately kept out of the ERP."""
    out = Path(__file__).resolve().parents[1] / "app" / "lexicon"
    out.mkdir(parents=True, exist_ok=True)
    lex = {
        "models": {i: {"name": n, "spoken": [a for a in al if a.startswith(("la ", "il ", "un ", "the "))],
                       "misheard": [a for a in al if not a.startswith(("la ", "il ", "un ", "the "))]}
                   for (i, n, f, y, t, g, al) in bc.MODELS},
        "editions": {e["name"].lower(): {"name": e["name"], "spoken": e["aliases"]} for e in bc.EDITIONS},
        "parts": {p["code"]: {"it": p["aliases_it"], "en": p["aliases_en"]} for p in bc.PARTS if p["aliases_it"] or p["aliases_en"]},
    }
    (out / "pronunciation.json").write_text(json.dumps(lex, ensure_ascii=False, indent=2), encoding="utf-8")


def write_part_sheets() -> None:
    """Static product sheets, Italian and English, same anchors (caratteristiche, compatibilita, sostituisce,
    montaggio, note). Live stock, prices and lead times are read from the database at call time."""
    from part_notes import NOTES_EN  # noqa: PLC0415
    out = KB / "parts"
    out.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    models = {r["id"]: r["name"] for r in con.execute("SELECT id, name FROM models")}
    T = {
        "it": {"static": "_Scheda statica. Giacenze, prezzo e tempi di consegna aggiornati: vedere il gestionale._",
               "superseded": "SOSTITUITO", "by": "da", "since": "dal", "requires": "Richiede anche", "field": "Campo", "value": "Valore",
               "group": "Gruppo", "supplier": "Fornitore", "lead": "lead time", "days": "giorni", "weight": "Peso",
               "compat": "Compatibilità", "per_machine": "per macchina", "replaces": "Sostituisce", "req": "richiede",
               "mount": "Montaggio", "notes": "Note del service",
               "mount_default": "Sostituzione standard: vedere il libretto del modello, sezione manutenzione. In caso di dubbio chiedere supporto al service.",
               "no_notes": "Nessuna nota."},
        "en": {"static": "_Static sheet. Current stock, price and delivery times: see the ERP._",
               "superseded": "SUPERSEDED", "by": "by", "since": "since", "requires": "Also requires", "field": "Field", "value": "Value",
               "group": "Group", "supplier": "Supplier", "lead": "lead time", "days": "days", "weight": "Weight",
               "compat": "Compatibility", "per_machine": "per machine", "replaces": "Replaces", "req": "requires",
               "mount": "Fitting", "notes": "Service notes",
               "mount_default": "Standard replacement: see the model's manual, maintenance section. When in doubt ask the service desk.",
               "no_notes": "No notes."},
    }
    SPEC_EN = {"tensione": "voltage", "potenza": "power", "misura": "size", "capacità": "capacity", "portata": "flow rate",
               "pressione": "pressure", "materiale": "material", "confezione": "pack"}
    for p in con.execute("SELECT p.*, s.name AS supplier, s.city, s.lead_time_days FROM parts p JOIN suppliers s ON s.id = p.supplier_id ORDER BY code"):
        code = p["code"]
        specs = con.execute("SELECT key, value FROM part_specs WHERE code=?", (code,)).fetchall()
        compat = con.execute("SELECT model_id, quantity_per_machine FROM compatibility WHERE code=?", (code,)).fetchall()
        sup_new = con.execute("SELECT * FROM supersessions WHERE old_code=?", (code,)).fetchone()
        sup_old = con.execute("SELECT * FROM supersessions WHERE new_code=?", (code,)).fetchall()
        for lang in ("it", "en"):
            t = T[lang]
            desc, other = (p["description_it"], p["description_en"]) if lang == "it" else (p["description_en"], p["description_it"])
            notes_lang = NOTES_EN.get(code, {}) if lang == "en" else {}
            mounting = notes_lang.get("mounting") if lang == "en" else p["mounting_notes"]
            notes = notes_lang.get("notes") if lang == "en" else p["notes"]
            if lang == "en" and not mounting and p["mounting_notes"]:
                mounting = p["mounting_notes"] + " *(service note, Italian)*"
            if lang == "en" and not notes and p["notes"]:
                notes = p["notes"] + " *(service note, Italian)*"
            lines = [f"# {code} — {desc}", "", f"*{other}*", "", t["static"], ""]
            if sup_new:
                lines += [f"> **{t['superseded']}** {t['by']} **{sup_new['new_code']}** {t['since']} {sup_new['since']}." +
                          (f" {t['requires']} **{sup_new['requires_code']}**." if sup_new['requires_code'] else "") +
                          (f" {sup_new['note']}" if lang == "it" else ""), ""]
            lines += [f"| {t['field']} | {t['value']} |", "|---|---|", f"| {t['group']} | {p['group_code']} |",
                      f"| {t['supplier']} | {p['supplier']} ({p['city']}), {t['lead']} {p['lead_time_days']} {t['days']} |",
                      f"| {t['weight']} | {p['weight_g']} g |"]
            for sp in specs:
                key = sp["key"] if lang == "it" else SPEC_EN.get(sp["key"], sp["key"])
                lines.append(f"| {key.capitalize()} | {sp['value']} |")
            lines += ["", f"## {t['compat']} {{#compatibilita}}", ""]
            for r in compat:
                lines.append(f"- {models[r['model_id']]}: {r['quantity_per_machine']} {t['per_machine']}")
            if sup_old:
                lines += ["", f"## {t['replaces']} {{#sostituisce}}", ""]
                for r in sup_old:
                    lines.append(f"- {r['old_code']}" + (f" ({t['req']} {r['requires_code']})" if r['requires_code'] else ""))
            lines += ["", f"## {t['mount']} {{#montaggio}}", "", mounting or t["mount_default"]]
            lines += ["", f"## {t['notes']} {{#note}}", "", notes or t["no_notes"]]
            name = f"{code}.md" if lang == "it" else f"{code}.en.md"
            (out / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    con.close()


if __name__ == "__main__":
    bc.validate()
    bc.main()
    build_db()
    write_lexicon()
    write_part_sheets()
    con = sqlite3.connect(DB)
    for t in ("models", "parts", "compatibility", "supersessions", "stock", "documents", "part_specs"):
        print(f"{t}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
    print("part sheets:", len(list((KB / "parts").glob("*.md"))))
