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
from part_notes import NOTES, NOTES_EN  # noqa: E402

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

# Installed base: the serial number is the key that unlocks build year, warranty and history.
# serial, model, edition, built (YYYY-MM), voltage, customer, city, country, installed, warranty_until, notes
MACHINES = [
    ("047219", "marea-2-plus", "vaniglia", "2025-04", "230V", "Café Berlin", "Hamburg", "DE", "2025-05-12", "2027-05-12", "Water softener installed at delivery."),
    ("041188", "marea-2", None, "2024-03", "230V", "Bar Centrale", "Lucca", "IT", "2024-04-02", "2026-04-02", "2024 build: control board v1, needs adapter EL-3036 with EL-3012."),
    ("041302", "marea-2", None, "2024-06", "110V", "Espresso Corner", "Chicago", "US", "2024-08-15", "2026-08-15", None),
    ("052710", "marea-2-evo", None, "2026-02", "400V", "Hotel Excelsior", "Vienna", "AT", "2026-03-01", "2028-03-01", None),
    ("043377", "giglio-1", None, "2024-09", "230V", "Galata Kahve", "Istanbul", "TR", "2024-10-20", "2026-10-20", "Very hard water: filter cartridge every month."),
    ("051040", "giglio-1-plus", "vaniglia", "2026-01", "230V", "Pastelería Sol", "Valencia", "ES", "2026-01-25", "2028-01-25", None),
    ("044801", "onda-mb2", None, "2024-11", "230V", "Kaffeehaus Nord", "Berlin", "DE", "2024-12-05", "2026-12-05", None),
    ("049155", "onda-mb3", None, "2025-07", "400V", "Roastery 21", "Rotterdam", "NL", "2025-08-01", "2027-08-01", None),
    ("053002", "onda-mb2-evo", None, "2026-03", "230V", "Bar Sol", "Valencia", "ES", "2026-04-10", "2028-04-10", None),
    ("G24-0177", "monda-65", None, "2024-05", "230V", "Café Berlin", "Hamburg", "DE", "2024-06-01", "2026-06-01", None),
    ("G25-0412", "monda-65-digit", None, "2025-09", "230V", "Bar Sol", "Valencia", "ES", "2025-10-03", "2027-10-03", None),
    ("048530", "marea-2-plus", None, "2025-06", "230V", "Kaffeehaus Nord", "Berlin", "DE", "2025-07-01", "2027-07-01", None),
    ("050904", "marea-2", None, "2025-11", "230V", "Pastelería Sol", "Valencia", "ES", "2025-12-09", "2027-12-09", "Hard water area: no softener fitted."),
]
# the service price list: charged only out of warranty (fictional)
SERVICE_PRICES = [
    ("SERVICE-CALL", "Videochiamata con il service (fino a 30 min)", "Service video call (up to 30 min)", 35.00),
    ("TECH-VISIT", "Uscita del tecnico (prezzo fisso)", "Technician's visit (fixed call-out)", 80.00),
    ("SHIP-EU", "Spedizione ricambi, Unione Europea", "Parts shipping, European Union", 9.90),
    ("SHIP-WORLD", "Spedizione ricambi, fuori UE", "Parts shipping, outside the EU", 29.00),
]

# the address quotes and payment instructions go to, one per customer (fictional)
CONTACT_EMAILS = {
    "Café Berlin": "service@cafe-berlin-hamburg.de", "Bar Centrale": "info@barcentrale-lucca.it",
    "Espresso Corner": "dave@espresso-corner-chicago.com", "Hotel Excelsior": "fb.manager@excelsior-vienna.at",
    "Galata Kahve": "info@galatakahve-istanbul.com", "Pastelería Sol": "luca@pasteleriasol-valencia.es",
    "Kaffeehaus Nord": "klaus@kaffeehausnord-berlin.de", "Roastery 21": "hello@roastery21-rotterdam.nl",
    "Bar Sol": "info@barsol-valencia.es",
}
MACHINE_ORDERS = [
    ("047219", "2025-09-18", "GE-2140", 2), ("047219", "2025-09-18", "CR-6052", 1), ("047219", "2026-03-02", "VA-5015", 1),
    ("041188", "2025-02-11", "GE-2210", 2), ("041188", "2025-11-20", "CA-1230", 1),
    ("043377", "2025-05-05", "ID-4061", 3), ("043377", "2026-01-14", "CA-1190", 1),
    ("044801", "2025-10-10", "GE-2410", 2), ("G24-0177", "2025-12-01", "MC-7010", 1),
    ("048530", "2026-02-03", "CR-6052", 2), ("041302", "2025-06-30", "GE-2140", 1), ("041302", "2025-06-30", "CR-6052", 2),
]

# Fictional service calendar: one zone per country of the installed base, plus the remote service line in Florence.
# Slots are day offsets from "today" (working days only, computed at query time), so the calendar never goes stale.
ONSITE = "09:00-12:00,14:00-17:00"
SERVICE_ZONES = [
    ("REMOTE", "Service line, Florence", "remote", "Sereni service desk (video call)", "09:30-10:00,11:00-11:30,15:00-15:30,16:30-17:00"),
    ("IT", "Italy", "onsite", "Sereni technician, Florence", ONSITE),
    ("DE", "Germany, Hamburg hub", "onsite", "Markus Weber, Hamburg", ONSITE),
    ("AT", "Austria, partner service Vienna", "onsite", "Partner service Wien", ONSITE),
    ("ES", "Spain, Valencia", "onsite", "Servicio técnico Valencia", ONSITE),
    ("NL", "Benelux, Rotterdam hub", "onsite", "Rotterdam hub technician", ONSITE),
    ("US", "USA, Chicago", "onsite", "Sereni USA, Chicago", ONSITE),
    ("TR", "Turkey, partner Istanbul", "onsite", "Partner service Istanbul", ONSITE),
]
# how full each calendar is over the next two weeks (a busy partner in Vienna, a quiet one in Florence)
SERVICE_LOAD = {"REMOTE": 0.35, "IT": 0.3, "DE": 0.6, "AT": 0.75, "ES": 0.4, "NL": 0.45, "US": 0.5, "TR": 0.65}


def service_busy_rows() -> list[tuple[str, int, int]]:
    import random
    rows = []
    for zone, _, _, _, times in SERVICE_ZONES:
        rnd = random.Random(f"sereni-{zone}")            # fixed seed: the same calendar on every rebuild
        n_slots = len(times.split(","))
        for off in range(1, 15):
            for i in range(n_slots):
                if rnd.random() < SERVICE_LOAD[zone]:
                    rows.append((zone, off, i))
    return rows


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
                        unit TEXT, weight_g INTEGER, supplier_id TEXT, mounting_notes TEXT, notes TEXT, notes_en TEXT);
    CREATE TABLE part_specs (code TEXT, key TEXT, value TEXT);
    CREATE TABLE compatibility (code TEXT, model_id TEXT, quantity_per_machine INTEGER);
    CREATE TABLE supersessions (old_code TEXT, new_code TEXT, since TEXT, requires_code TEXT, note TEXT, note_en TEXT);
    CREATE TABLE stock (code TEXT, warehouse TEXT, quantity INTEGER, updated_at TEXT);
    CREATE TABLE prices (code TEXT, list_price_eur REAL, valid_from TEXT, valid_to TEXT);
    CREATE TABLE order_stats (code TEXT PRIMARY KEY, orders_last_12m INTEGER);
    CREATE TABLE documents (id TEXT PRIMARY KEY, kind TEXT, model_id TEXT, family TEXT, code TEXT, path TEXT, title TEXT, internal INTEGER);
    CREATE TABLE machines (serial TEXT PRIMARY KEY, model_id TEXT, edition TEXT, built TEXT, voltage TEXT, customer TEXT,
                           city TEXT, country TEXT, installed TEXT, warranty_until TEXT, notes TEXT, contact_email TEXT);
    CREATE TABLE machine_orders (serial TEXT, ordered_on TEXT, code TEXT, qty INTEGER);
    CREATE TABLE service_zones (zone TEXT PRIMARY KEY, name TEXT, kind TEXT, technician TEXT, slot_times TEXT);
    CREATE TABLE service_prices (code TEXT PRIMARY KEY, description_it TEXT, description_en TEXT, price_eur REAL);
    CREATE TABLE service_busy (zone TEXT, day_offset INTEGER, slot INTEGER);
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
    c.executemany("INSERT INTO machines VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [m + (CONTACT_EMAILS.get(m[5]),) for m in MACHINES])
    c.executemany("INSERT INTO machine_orders VALUES (?,?,?,?)", MACHINE_ORDERS)
    c.executemany("INSERT INTO service_zones VALUES (?,?,?,?,?)", SERVICE_ZONES)
    c.executemany("INSERT INTO service_prices VALUES (?,?,?,?)", SERVICE_PRICES)
    c.executemany("INSERT INTO service_busy VALUES (?,?,?)", service_busy_rows())

    for p in bc.PARTS:
        notes = NOTES.get(p["code"], {})
        weight = {1: 30, 2: 120, 3: 250, 4: 600, 5: 4000}[p["order_rank"]] + h(p["code"] + "w", 40)
        c.execute("INSERT INTO parts VALUES (?,?,?,?,?,?,?,?,?,?)", (
            p["code"], p["group"], p["description_it"], p["description_en"], "pz", weight,
            supplier_for(p), notes.get("mounting"), notes.get("notes") or p["note"],
            NOTES_EN.get(p["code"], {}).get("notes") or p["note"]))
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

    c.execute("INSERT INTO supersessions VALUES (?,?,?,?,?,?)",
              ("EL-3010", "EL-3012", "2025-03-01", "EL-3036", "Centralina v1 fuori produzione. Sulle macchine 2024 serve il cablaggio adattatore EL-3036.",
               "Control board v1 discontinued. 2024 machines also need the adapter harness EL-3036."))
    c.execute("INSERT INTO supersessions VALUES (?,?,?,?,?,?)",
              ("EL-3011", "EL-3012", "2025-04-15", None, "Primo lotto v2 con bug del conteggio flussometro. Sostituzione diretta.",
               "First v2 batch with a flowmeter counting bug. Direct replacement."))
    c.execute("INSERT INTO supersessions VALUES (?,?,?,?,?,?)",
              ("CA-1300", "CA-1300", None, None, None, None))  # placeholder removed below
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
