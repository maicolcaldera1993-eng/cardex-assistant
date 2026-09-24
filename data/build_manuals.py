"""User manuals for every Sereni model, Italian and English with shared anchors (the English headings carry the
Italian slug, so a section opened in one language is the same section in the other). The Marea 2 Plus manual is
hand-written and left alone; the others are built here from one template per family and the model's data.
Every part code quoted must exist in the ERP for that model (checked in tests/test_manuals.py).

    .venv/Scripts/python data/build_manuals.py
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

OUT = Path(__file__).parent / "kb" / "manuals"
HAND_WRITTEN = {"marea-2-plus"}


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


# ------------------------------------------------------------------ model data
HX = {  # heat-exchanger machines: Marea and Giglio
    "marea-2": dict(
        name="Marea 2", year=2024, groups=2, cups=400, boiler_it="11 L, rame", boiler_en="11 L, copper",
        element_it="3000 W 230 V (CA-1180); 3000 W 110 V (CA-1181); 4500 W 400 V trifase (CA-1182)",
        element_en="3000 W 230 V (CA-1180); 3000 W 110 V (CA-1181); 4500 W 400 V three-phase (CA-1182)",
        pump_it="rotativa 100 L/h con motore 165 W (ID-4010, ID-4015)", pump_en="rotary 100 L/h with 165 W motor (ID-4010, ID-4015)",
        control_it="pressostato (CA-1240), caldaia a 1,1-1,2 bar", control_en="pressurestat (CA-1240), boiler at 1.1-1.2 bar",
        pad_it="pulsantiera a membrana a sei tasti (EL-3030)", pad_en="six-button membrane touchpad (EL-3030)",
        board_it="Centralina v1 (EL-3010), sostituita dalla v2 rev.B (EL-3012) con il cablaggio adattatore EL-3036.",
        board_en="Control board v1 (EL-3010), replaced by v2 rev.B (EL-3012) with the adapter harness EL-3036.",
        size="78 × 55 × 53 cm, 60 kg", steam_valve="VA-5015", gasket="GE-2140", screen="GE-2150", kit="GE-2210",
        diff_it="È il modello base della gamma: pulsantiera a membrana, centralina v1, senza PID. La Marea 2 Plus (2025) aggiunge PID e pulsantiera capacitiva.",
        diff_en="The entry model of the range: membrane touchpad, v1 control board, no PID. The Marea 2 Plus (2025) adds PID and a capacitive touchpad."),
    "marea-2-evo": dict(
        name="Marea 2 Evo", year=2026, groups=2, cups=450, boiler_it="11 L, rame coibentato (CA-1350)", boiler_en="11 L, insulated copper (CA-1350)",
        element_it="3500 W 230 V (CA-1185); 3500 W 110 V (CA-1186); 5000 W 400 V trifase (CA-1187)",
        element_en="3500 W 230 V (CA-1185); 3500 W 110 V (CA-1186); 5000 W 400 V three-phase (CA-1187)",
        pump_it="rotativa 100 L/h con motore 165 W (ID-4010, ID-4015)", pump_en="rotary 100 L/h with 165 W motor (ID-4010, ID-4015)",
        control_it="controllo PID con sonda PT100 (CA-1291), niente pressostato", control_en="PID control with PT100 probe (CA-1291), no pressurestat",
        pad_it="pulsantiera capacitiva con display OLED (EL-3032) e display TFT da 2,8\" (EL-3040)",
        pad_en="capacitive touchpad with OLED display (EL-3032) and 2.8\" TFT display (EL-3040)",
        board_it="Centralina v3 con uscita display (EL-3013).", board_en="Control board v3 with display output (EL-3013).",
        size="78 × 55 × 53 cm, 64 kg", steam_valve="VA-5015", gasket="GE-2140", screen="GE-2150", kit="GE-2210",
        diff_it="Rispetto alla Marea 2 Plus: caldaia coibentata, controllo PID della caldaia senza pressostato, display, sensore di livello della vaschetta (EL-3101).",
        diff_en="Compared with the Marea 2 Plus: insulated boiler, PID boiler control with no pressurestat, display, drip tray level sensor (EL-3101)."),
    "giglio-1": dict(
        name="Giglio 1", year=2024, groups=1, cups=150, boiler_it="5 L, rame", boiler_en="5 L, copper",
        element_it="1800 W 230 V (CA-1190); 1500 W 110 V (CA-1191)", element_en="1800 W 230 V (CA-1190); 1500 W 110 V (CA-1191)",
        pump_it="a vibrazione 48 W (ID-4020 a 230 V, ID-4021 a 110 V)", pump_en="vibration pump 48 W (ID-4020 at 230 V, ID-4021 at 110 V)",
        control_it="pressostato (CA-1240), caldaia a 1,1-1,2 bar", control_en="pressurestat (CA-1240), boiler at 1.1-1.2 bar",
        pad_it="pulsantiera a membrana a sei tasti (EL-3030)", pad_en="six-button membrane touchpad (EL-3030)",
        board_it="Centralina v1 (EL-3010), sostituita dalla v2 rev.B (EL-3012) con il cablaggio adattatore EL-3036.",
        board_en="Control board v1 (EL-3010), replaced by v2 rev.B (EL-3012) with the adapter harness EL-3036.",
        size="45 × 52 × 48 cm, 36 kg", steam_valve="VA-5015", gasket="GE-2140", screen="GE-2150", kit="GE-2210",
        diff_it="La compatta a un gruppo: stesso gruppo e stesse guarnizioni della Marea, caldaia piccola e pompa a vibrazione. La Giglio 1 Plus (2026) ha pompa rotativa.",
        diff_en="The compact one-group machine: same group and gaskets as the Marea, small boiler and vibration pump. The Giglio 1 Plus (2026) has a rotary pump."),
    "giglio-1-plus": dict(
        name="Giglio 1 Plus", year=2026, groups=1, cups=180, boiler_it="5 L, rame", boiler_en="5 L, copper",
        element_it="1800 W 230 V (CA-1190); 1500 W 110 V (CA-1191)", element_en="1800 W 230 V (CA-1190); 1500 W 110 V (CA-1191)",
        pump_it="rotativa 100 L/h con motore 165 W (ID-4010, ID-4015)", pump_en="rotary 100 L/h with 165 W motor (ID-4010, ID-4015)",
        control_it="pressostato (CA-1240), caldaia a 1,1-1,2 bar", control_en="pressurestat (CA-1240), boiler at 1.1-1.2 bar",
        pad_it="pulsantiera capacitiva a sei tasti (EL-3031)", pad_en="six-button capacitive touchpad (EL-3031)",
        board_it="Centralina v2 rev.B (EL-3012); il primo lotto 2025 montava la v2 (EL-3011), sostituibile direttamente.",
        board_en="Control board v2 rev.B (EL-3012); the first 2025 batch had v2 (EL-3011), a direct replacement.",
        size="45 × 52 × 48 cm, 39 kg", steam_valve="VA-5015", gasket="GE-2140", screen="GE-2150", kit="GE-2210",
        diff_it="Rispetto alla Giglio 1: pompa rotativa silenziosa, pulsantiera capacitiva, centralina v2. Disponibile in edizione Vaniglia (finitura crema, manopola VA-5018).",
        diff_en="Compared with the Giglio 1: quiet rotary pump, capacitive touchpad, v2 control board. Available in the Vaniglia edition (cream finish, knob VA-5018)."),
}

MB = {  # multi-boiler machines: Onda
    "onda-mb2": dict(
        name="Onda MB2", year=2024, groups=2, cups=500, steam_it="7 L inox (CA-1323)", steam_en="7 L stainless (CA-1323)",
        steam_el_it="3200 W 230 V (CA-1200); 3200 W 110 V (CA-1201)", steam_el_en="3200 W 230 V (CA-1200); 3200 W 110 V (CA-1201)",
        pump="ID-4010", pump_desc_it="rotativa 100 L/h", pump_desc_en="rotary 100 L/h",
        pad_it="pulsantiera retroilluminata a cinque tasti per gruppo (EL-3033)", pad_en="backlit five-button touchpad per group (EL-3033)",
        board="EL-3020", size="82 × 58 × 55 cm, 78 kg", grid="CR-6034",
        diff_it="Caldaia vapore e una caldaietta caffè per gruppo, ognuna con il suo PID: temperatura del caffè indipendente per gruppo.",
        diff_en="A steam boiler plus one small coffee boiler per group, each with its own PID: coffee temperature set per group."),
    "onda-mb3": dict(
        name="Onda MB3", year=2025, groups=3, cups=700, steam_it="10 L inox (CA-1324)", steam_en="10 L stainless (CA-1324)",
        steam_el_it="4800 W 400 V trifase (CA-1202); 4800 W 230 V (CA-1203)", steam_el_en="4800 W 400 V three-phase (CA-1202); 4800 W 230 V (CA-1203)",
        pump="ID-4011", pump_desc_it="rotativa 150 L/h", pump_desc_en="rotary 150 L/h",
        pad_it="pulsantiera retroilluminata a cinque tasti per gruppo (EL-3033)", pad_en="backlit five-button touchpad per group (EL-3033)",
        board="EL-3020", size="106 × 58 × 55 cm, 96 kg", grid="CR-6034",
        diff_it="La Onda a tre gruppi: stessa elettronica della MB2, caldaia vapore da 10 litri e pompa più grande.",
        diff_en="The three-group Onda: same electronics as the MB2, 10-litre steam boiler and a larger pump."),
    "onda-mb2-evo": dict(
        name="Onda MB2 Evo", year=2026, groups=2, cups=500, steam_it="7 L inox coibentata (CA-1323, CA-1350)", steam_en="7 L insulated stainless (CA-1323, CA-1350)",
        steam_el_it="3200 W 230 V (CA-1200); 3200 W 110 V (CA-1201)", steam_el_en="3200 W 230 V (CA-1200); 3200 W 110 V (CA-1201)",
        pump="ID-4010", pump_desc_it="rotativa 100 L/h", pump_desc_en="rotary 100 L/h",
        pad_it="pannello touch per gruppo (EL-3034) e display touch da 5\" (EL-3041)", pad_en="per-group touch panel (EL-3034) and 5\" touch display (EL-3041)",
        board="EL-3021", size="82 × 58 × 55 cm, 81 kg", grid="CR-6033",
        diff_it="Rispetto alla MB2: bilance integrate sotto ogni gruppo (EL-3095, celle EL-3096), display touch, sensore di livello della vaschetta (EL-3101), caldaia vapore coibentata.",
        diff_en="Compared with the MB2: built-in scales under each group (EL-3095, load cells EL-3096), touch display, drip tray level sensor (EL-3101), insulated steam boiler."),
}

GR = {  # grinders: Monda
    "monda-65": dict(
        name="Monda 65", year=2024, dosing_it="dosatore a camera con stella a sei settori e leva (MC-7030)",
        dosing_en="chamber doser with six-sector star and lever (MC-7030)", switch="MC-7070", size="21 × 38 × 62 cm, 13 kg",
        diff_it="Il macinacaffè con dosatore: si macina nella camera e si dosa a leva, una tacca della stella per ogni dose.",
        diff_en="The doser grinder: it grinds into the chamber and doses with the lever, one star sector per dose."),
    "monda-65-digit": dict(
        name="Monda 65 Digit", year=2025, dosing_it="dosaggio a tempo con display e tasti (MC-7060, MC-7061), avvio con la forcella (MC-7062)",
        dosing_en="timed dosing with display and buttons (MC-7060, MC-7061), started by the portafilter fork (MC-7062)", switch="MC-7062",
        size="21 × 38 × 62 cm, 14 kg",
        diff_it="Il macinacaffè on demand: niente dosatore, macina direttamente nel portafiltro per il tempo impostato.",
        diff_en="The on-demand grinder: no doser, it grinds straight into the portafilter for the set time."),
}

HELP_IT = ("Help desk Sereni: lun-ven 8-18 CET, in italiano e inglese; anche assistente vocale automatico. Tenere a portata di mano: "
           "modello, matricola, anno, tensione, e la fattura dell'ultimo ricambio se si cita un codice.")
HELP_EN = ("Sereni help desk: Mon-Fri 8-18 CET, in Italian and English; also an automatic voice assistant. Have ready: model, "
           "serial number, year, voltage, and the invoice of the last part if you quote a code.")


def h(level: int, it: str, en: str, lang: str) -> str:
    """Heading: Italian text, or English text carrying the Italian anchor."""
    bare_it = re.sub(r"^\d+\.\s*", "", it)
    return f"{'#' * level} {it}" if lang == "it" else f"{'#' * level} {en} {{#{slug(bare_it)}}}"


def topics(it: str, en: str) -> str:
    return f"<!-- topics: {en}; {it} -->"


# ------------------------------------------------------------------ espresso machines (Marea, Giglio, Onda)
def espresso(mid: str, d: dict, multi: bool, lang: str) -> str:
    it = lang == "it"
    L = []
    if multi:
        kind_it, kind_en = f"{d['groups']} gruppi, multi-caldaia, PID per gruppo", f"{d['groups']} groups, multi-boiler, PID per group"
    else:
        kind_it = f"{d['groups']} {'gruppo' if d['groups'] == 1 else 'gruppi'}, scambiatore di calore, dosatura volumetrica"
        kind_en = f"{d['groups']} group{'s' if d['groups'] > 1 else ''}, heat exchanger, volumetric dosing"
    L.append(f"# Sereni {d['name']} — " + ("Libretto d'uso e manutenzione" if it else "User and maintenance manual"))
    L.append("")
    L.append((f"Sereni Macchine da Caffè S.r.l., Firenze. Edizione {d['year']}, rev. 1. Conservare con la macchina." if it else
              f"Sereni Macchine da Caffè S.r.l., Florence. {d['year']} edition, rev. 1. Keep with the machine."))
    L.append((f"Modello: {d['name']} ({kind_it})." if it else f"Model: {d['name']} ({kind_en})."))
    L.append("")

    # 1. description
    L.append(h(2, "1. Descrizione", "1. Description", lang))
    L.append(topics("com'è fatta la macchina, come funziona", "what machine is this, how it works"))
    L.append("")
    if multi:
        L.append((f"La {d['name']} è una macchina professionale per locali ad alto volume, fino a {d['cups']} caffè al giorno. "
                  f"Una caldaia vapore da {d['steam_it'].split(' (')[0]} produce vapore e acqua calda; ogni gruppo ha la sua caldaietta caffè "
                  "da 0,8 L (CA-1325) con resistenza da 800 W e sonda PT100, e un mantello riscaldato sul gruppo. La temperatura si imposta "
                  f"gruppo per gruppo dal pannello. Pompa {d['pump_desc_it']}, elettrovalvole a 24 V." if it else
                  f"The {d['name']} is a professional machine for high-volume venues, up to {d['cups']} coffees a day. A steam boiler "
                  "produces steam and hot water; each group has its own 0.8 L coffee boiler (CA-1325) with an 800 W element and a PT100 "
                  f"probe, and a heated jacket on the group. Temperature is set group by group on the panel. {d['pump_desc_en'].capitalize()} pump, 24 V solenoids."))
    else:
        L.append((f"La {d['name']} è una macchina professionale per bar fino a {d['cups']} caffè al giorno. Una caldaia da "
                  f"{d['boiler_it'].split(' (')[0]} produce vapore e acqua calda; l'acqua per il caffè passa in uno scambiatore per gruppo "
                  "immerso nella caldaia e arriva al gruppo a 92-94 °C. Dosatura volumetrica con quattro dosi programmabili per gruppo." if it else
                  f"The {d['name']} is a professional machine for bars up to {d['cups']} coffees a day. A boiler produces steam and hot "
                  "water; the brewing water runs through one heat exchanger per group inside the boiler and reaches the group at 92-94 °C. "
                  "Volumetric dosing with four programmable doses per group."))
    L.append("")
    L.append(d["diff_it"] if it else d["diff_en"])
    L.append("")

    # 2. technical data
    L.append(h(2, "2. Dati tecnici", "2. Technical data", lang))
    L.append(topics("dati tecnici, tensione, potenza, matricola, targhetta",
                    "technical data, voltage, power, boiler size, pump pressure, serial number plate, where is the serial number"))
    L.append("")
    L.append("| | |")
    L.append("|---|---|")
    rows_it, rows_en = [("Gruppi", str(d["groups"]))], [("Groups", str(d["groups"]))]
    if multi:
        rows_it += [("Caldaia vapore", d["steam_it"]),
                    ("Resistenza vapore", d["steam_el_it"]),
                    ("Caldaiette caffè", "0,8 L per gruppo (CA-1325), resistenza 800 W (CA-1210 a 230 V, CA-1211 a 110 V)"),
                    ("Controllo", "PID con sonde PT100 (caldaia CA-1291, gruppo GE-2220), trasduttore di pressione vapore (CA-1245)"),
                    ("Pompa", f"{d['pump_desc_it']} ({d['pump']}), motore 165 W (ID-4015)"),
                    ("Elettronica", f"centralina {d['board']}, alimentatore 24 V (EL-3057), {d['pad_it']}")]
        rows_en += [("Steam boiler", d["steam_en"]), ("Steam element", d["steam_el_en"]),
                    ("Coffee boilers", "0.8 L per group (CA-1325), 800 W element (CA-1210 at 230 V, CA-1211 at 110 V)"),
                    ("Control", "PID with PT100 probes (boiler CA-1291, group GE-2220), steam pressure transducer (CA-1245)"),
                    ("Pump", f"{d['pump_desc_en']} ({d['pump']}), 165 W motor (ID-4015)"),
                    ("Electronics", f"control board {d['board']}, 24 V power supply (EL-3057), {d['pad_en']}")]
    else:
        rows_it += [("Caldaia", d["boiler_it"]),
                    ("Resistenza", d["element_it"]), ("Pompa", d["pump_it"]), ("Pressione caldaia", d["control_it"]),
                    ("Elettronica", d["board_it"] + " " + d["pad_it"].capitalize() + ".")]
        rows_en += [("Boiler", d["boiler_en"]),
                    ("Element", d["element_en"]), ("Pump", d["pump_en"]), ("Boiler pressure", d["control_en"]),
                    ("Electronics", d["board_en"] + " " + d["pad_en"].capitalize() + ".")]
    rows_it += [("Pressione pompa", "9 bar (regolabile sul by-pass)"),
                ("Allacciamento idrico", "3/8\", pressione di rete 2-4 bar; sopra 4 bar usare il riduttore ID-4110"),
                ("Scarico", "tubo 20 mm (ID-4086)"), ("Dimensioni", d["size"]), ("Matricola", "targhetta sotto la vaschetta di scarico, a destra")]
    rows_en += [("Pump pressure", "9 bar (set on the bypass)"),
                ("Water connection", "3/8\", mains pressure 2-4 bar; above 4 bar fit the reducer ID-4110"),
                ("Drain", "20 mm hose (ID-4086)"), ("Size", d["size"]), ("Serial number", "plate under the drip tray, on the right")]
    for k, v in (rows_it if it else rows_en):
        L.append(f"| {k} | {v} |")
    L.append("")

    # 3. installation
    L.append(h(2, "3. Installazione", "3. Installation", lang))
    L.append(topics("installazione, allacciamento acqua, durezza dell'acqua, addolcitore, prima accensione",
                    "installation, water connection, water hardness, softener, first start-up"))
    L.append("")
    L.append(("Solo personale autorizzato. Acqua di rete con durezza inferiore a 8 °f oppure con addolcitore: **la garanzia non copre i danni "
              "da calcare.** Verificare la tensione di targa prima del collegamento. " + (
                  "Alla prima accensione si riempie prima la caldaia vapore, poi le caldaiette dei gruppi (circa 6 minuti); ogni gruppo è pronto quando "
                  "il suo pannello smette di lampeggiare." if multi else
                  "Alla prima accensione la caldaia si riempie automaticamente (circa 4 minuti); attendere 1,1 bar sul manometro prima di erogare. "
                  "Il sibilo della valvola antidepressione nei primi minuti è normale.")) if it else
             ("Authorised staff only. Mains water below 8 °f hardness, or a softener: **the warranty does not cover scale damage.** Check the "
              "rated voltage before connecting. " + (
                  "At first start-up the steam boiler fills first, then the group boilers (about 6 minutes); each group is ready when its panel "
                  "stops flashing." if multi else
                  "At first start-up the boiler fills automatically (about 4 minutes); wait for 1.1 bar on the gauge before brewing. A hiss from "
                  "the anti-vacuum valve in the first minutes is normal.")))
    L.append("")

    # 4. daily use
    L.append(h(2, "4. Uso quotidiano", "4. Daily use", lang))
    L.append(topics("uso quotidiano, accensione, programmare le dosi, tasti, vapore, acqua calda",
                    "daily use, switching on, how to program the doses, buttons, steam, hot water"))
    L.append("")
    if it:
        L.append("- **Accensione**: interruttore generale" + (" acceso; pronta in 25-30 minuti." if multi else " in posizione 1 (solo carico acqua), poi 2 (riscaldamento). Pronta in 20-25 minuti."))
        L.append("- **Erogazione**: portafiltro agganciato al centro, tasto dose.")
        L.append("- **Programmazione dosi**: tenere premuto il tasto continuo 5 secondi finché lampeggia, avviare la dose, premere lo stesso tasto alla quantità voluta.")
        if multi:
            L.append("- **Temperatura**: dal pannello di ogni gruppo, tasti + e −; valore consigliato 93 °C.")
            L.append("- **Vapore**: leva joystick in alto per vapore pieno, in basso per vapore a impulsi; purgare 2 secondi prima e dopo.")
            L.append("- **Caldaia vapore**: si può spegnere dal pannello (icona vapore) nelle ore di poco lavoro.")
            if mid == "onda-mb2-evo":
                L.append("- **Bilance**: il peso della tazza compare sul pannello del gruppo; la dose può fermarsi a peso. Menu Bilancia, tasto Tara, a vaschetta vuota.")
        else:
            L.append("- **Vapore**: aprire il rubinetto, purgare 2 secondi, immergere la lancia. Dopo l'uso purgare e pulire con panno umido.")
        L.append("- **Acqua calda**: tasto acqua calda.")
    else:
        L.append("- **Switching on**: main switch" + (" on; ready in 25-30 minutes." if multi else " to position 1 (fill only), then 2 (heating). Ready in 20-25 minutes."))
        L.append("- **Brewing**: portafilter locked to the centre, dose button.")
        L.append("- **Programming doses**: hold the continuous button 5 seconds until it flashes, start the dose, press the same button at the desired amount.")
        if multi:
            L.append("- **Temperature**: on each group's panel, + and − buttons; recommended 93 °C.")
            L.append("- **Steam**: joystick up for full steam, down for pulsed steam; purge 2 seconds before and after.")
            L.append("- **Steam boiler**: can be switched off from the panel (steam icon) in quiet hours.")
            if mid == "onda-mb2-evo":
                L.append("- **Scales**: the cup weight shows on the group panel; the dose can stop by weight. Scales menu, Tare button, with the tray empty.")
        else:
            L.append("- **Steam**: open the tap, purge 2 seconds, dip the wand. After use purge and wipe with a damp cloth.")
        L.append("- **Hot water**: hot water button.")
    L.append("")

    # 5. routine maintenance
    gasket, screen, kit = (("GE-2410", "GE-2151", "GE-2211") if multi else (d["gasket"], d["screen"], d["kit"]))
    L.append(h(2, "5. Manutenzione ordinaria", "5. Routine maintenance", lang))
    L.append(topics("manutenzione ordinaria, pulizia, cosa deve fare l'utente", "routine maintenance, what the user must do, cleaning schedule"))
    L.append("")
    L.append("Tutto ciò che segue è a carico dell'utente. Nove chiamate di assistenza su dieci nascono da una di queste operazioni saltata." if it else
             "Everything below is the user's job. Nine service calls out of ten come from one of these being skipped.")
    L.append("")
    L.append(h(3, "Ogni giorno, a fine servizio", "Every day, at closing time", lang))
    L.append(topics("pulizia giornaliera, lavaggio dei gruppi con filtro cieco e pastiglia, ogni quanto si lava",
                    "daily cleaning, backflush, clean the groups with the blind filter and a tablet, how often to clean, detergent"))
    if it:
        L.append("1. **Lavaggio dei gruppi con filtro cieco (GE-2193) e pastiglia (CR-6052)**: una pastiglia nel filtro cieco, 5 cicli da 10 secondi con il tasto continuo, poi 5 cicli senza pastiglia. Per ogni gruppo.")
        L.append("2. Portafiltri e filtri in acqua calda con pastiglia per 20 minuti, risciacquo.")
        L.append("3. Lancia vapore: purgare e pulire; svitare e sciacquare il terminale (VA-5025) una volta a settimana.")
        L.append("4. Svuotare e lavare vaschetta e griglia" + (f" ({d['grid']})." if multi else "."))
    else:
        L.append("1. **Backflush the groups with the blind filter (GE-2193) and a tablet (CR-6052)**: one tablet in the blind filter, 5 cycles of 10 seconds with the continuous button, then 5 cycles without the tablet. On each group.")
        L.append("2. Portafilters and baskets in hot water with a tablet for 20 minutes, rinse.")
        L.append("3. Steam wand: purge and wipe; unscrew and rinse the tip (VA-5025) once a week.")
        L.append("4. Empty and wash the drip tray and grid" + (f" ({d['grid']})." if multi else "."))
    L.append("")
    L.append(h(3, "Ogni settimana", "Every week", lang))
    L.append(topics("pulizia settimanale, spazzolare la doccetta, aggancio del portafiltro", "weekly cleaning, brush the shower screen, check how the portafilter locks"))
    L.append(f"- Spazzolare la doccetta con la spazzola gruppo (CR-6051) senza smontarla.\n- Controllare l'aggancio del portafiltro: se arriva oltre il centro, la guarnizione ({gasket}) è da cambiare." if it else
             f"- Brush the shower screen with the group brush (CR-6051) without removing it.\n- Check how the portafilter locks: if it goes past the centre, the gasket ({gasket}) needs replacing.")
    L.append("")
    L.append(h(3, "Ogni mese", "Every month", lang))
    L.append(topics("manutenzione mensile, smontare e decalcificare le doccette, cartuccia del filtro", "monthly maintenance, remove and descale the shower screens, water filter cartridge"))
    L.append(f"- Smontare le doccette (vite centrale) e lasciarle 20 minuti nel decalcificante; sostituire se deformate ({screen}).\n- Controllare la cartuccia del filtro d'ingresso (ID-4061); sostituirla ogni 3 mesi, ogni mese con acqua dura." if it else
             f"- Remove the shower screens (centre screw) and leave them 20 minutes in descaler; replace if deformed ({screen}).\n- Check the inlet filter cartridge (ID-4061); replace it every 3 months, every month with hard water.")
    L.append("")
    L.append(h(3, "Ogni 6-12 mesi", "Every 6-12 months", lang))
    L.append(topics("sostituire le guarnizioni sottocoppa, ogni quanto si cambia la guarnizione", "replace the group gaskets, how often to change the gasket, steam valve seals"))
    steam_seals = "VA-5019" if multi else d["steam_valve"]
    L.append(f"- Sostituire le guarnizioni sottocoppa ({gasket}) o montare il kit gruppo ({kit}). Operazione da 10 minuti, vedere la scheda del ricambio.\n- Sostituire il kit guarnizioni del {'joystick' if multi else 'rubinetto'} vapore ({steam_seals}) se gocciola." if it else
             f"- Replace the group gaskets ({gasket}) or fit the group service kit ({kit}). A 10-minute job, see the part sheet.\n- Replace the steam {'joystick' if multi else 'valve'} seal kit ({steam_seals}) if it drips.")
    L.append("")
    L.append(h(3, "Ogni 2 anni, a cura del service", "Every 2 years, by the service network", lang))
    L.append(topics("revisione biennale, valvola di sicurezza, decalcificazione caldaia", "two-year service, safety valve, anti-vacuum valve, level probe, boiler descaling"))
    probe = "CA-1231" if multi else "CA-1230"
    safety = "CA-1251" if multi else "CA-1250"
    L.append(f"- Valvola di sicurezza ({safety}), valvola antidepressione (CA-1260), sonda di livello ({probe}), decalcificazione delle caldaie." if it else
             f"- Safety valve ({safety}), anti-vacuum valve (CA-1260), level probe ({probe}), descaling of the boilers.")
    L.append("")

    # 6. signals
    L.append(h(2, "6. Spie e segnali", "6. Lights and signals", lang))
    L.append(topics("spie, led che lampeggiano, allarmi, allarme livello, errori sul pannello",
                    "warning lights, flashing LEDs, alarms, level alarm, error codes, what does the blinking mean"))
    L.append("")
    L.append("| Segnale | Significato | Cosa fare |" if it else "| Signal | Meaning | What to do |")
    L.append("|---|---|---|")
    if multi:
        sig = [("Tutti i pannelli lampeggiano", "allarme livello caldaia vapore", "verificare il rubinetto dell'acqua; se persiste, chiamare il service",
                "All panels flashing", "steam boiler level alarm", "check the water tap; if it persists, call service"),
               ("PRB sul pannello di un gruppo", "errore sonda di temperatura", "chiamare il service",
                "PRB on a group panel", "temperature probe error", "call service"),
               ("Temperatura del gruppo che non sale", "caldaietta non scalda o termostato di sicurezza scattato", "vedere il fascicolo o chiamare il service",
                "Group temperature not rising", "group boiler not heating or safety thermostat tripped", "call service"),
               ("Pressione vapore 0,0 con icona accesa", "caldaia vapore non scalda", "chiamare il service",
                "Steam pressure 0.0 with the icon lit", "steam boiler not heating", "call service")]
        if mid == "onda-mb2-evo":
            sig.append(("Peso che oscilla a vaschetta vuota", "bilancia da tarare o cella di carico", "menu Bilancia, Tara",
                        "Weight jumping with an empty tray", "scale to tare, or load cell", "Scales menu, Tare"))
    else:
        sig = [("Led dei tasti lampeggiano insieme", "allarme livello: la caldaia non si è riempita in 3 minuti", "verificare il rubinetto dell'acqua; spegnere e riaccendere; se persiste, chiamare il service",
                "All button LEDs flashing together", "level alarm: the boiler did not fill within 3 minutes", "check the water tap; switch off and on; if it persists, call service"),
               ("Led del tasto lampeggia durante la dose", "allarme flussometro", "erogare in continuo; se la dose non si ferma, service",
                "A button LED flashes during the dose", "flowmeter alarm", "brew with the continuous button; if the dose does not stop, service"),
               ("Sibilo breve all'accensione", "valvola antidepressione", "normale se smette entro 5 minuti",
                "Short hiss at start-up", "anti-vacuum valve", "normal if it stops within 5 minutes")]
    sig.append(("Sfiato dalla valvola di sicurezza", "pressione oltre il limite", "spegnere, chiamare il service",
                "Venting from the safety valve", "pressure over the limit", "switch off, call service"))
    for row in sig:
        L.append("| " + " | ".join(row[:3] if it else row[3:]) + " |")
    L.append("")

    # 7. what not to do
    L.append(h(2, "7. Cosa non fare", "7. What not to do", lang))
    L.append(topics("cosa non fare, avvertenze", "what not to do, warnings, never adjust the safety valve, do not run without water"))
    L.append("")
    L.append("- Non far funzionare la macchina con l'acqua chiusa.\n- Non regolare la valvola di sicurezza.\n- Non usare detergenti diversi dalle pastiglie CR-6052 nei gruppi.\n"
             "- Non sostituire resistenze, pompa o centralina senza il service in linea.\n- Non lasciare la lancia vapore immersa nel latte." if it else
             "- Do not run the machine with the water off.\n- Do not adjust the safety valve.\n- Do not use any detergent other than CR-6052 tablets in the groups.\n"
             "- Do not replace elements, pump or control board without service on the line.\n- Do not leave the steam wand in the milk.")
    L.append("")

    # 8. consumables
    L.append(h(2, "8. Ricambi di consumo consigliati a magazzino del cliente", "8. Consumables to keep in stock", lang))
    L.append(topics("ricambi da tenere a magazzino, consumabili consigliati", "spare parts to keep in stock, consumables, recommended spares"))
    L.append("")
    n = d["groups"]
    L.append(f"{gasket} guarnizione sottocoppa ({n}), {screen} doccetta ({n}), GE-2193 filtro cieco (1), CR-6052 pastiglie (1 barattolo), "
             f"{steam_seals} kit guarnizioni vapore (1), VA-5025 terminale vapore (1), ID-4061 cartuccia filtro (1), EL-3060 fusibili (1 kit)." if it else
             f"{gasket} group gasket ({n}), {screen} shower screen ({n}), GE-2193 blind filter (1), CR-6052 tablets (1 jar), "
             f"{steam_seals} steam seal kit (1), VA-5025 steam tip (1), ID-4061 filter cartridge (1), EL-3060 fuses (1 kit).")
    L.append("")

    # 9. support
    L.append(h(2, "9. Assistenza", "9. Support", lang))
    L.append(topics("come contattare l'assistenza, orari, cosa tenere pronto", "how to contact support, opening hours, what to have ready when calling"))
    L.append("")
    L.append(HELP_IT if it else HELP_EN)
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ grinders (Monda)
def grinder(mid: str, d: dict, lang: str) -> str:
    it = lang == "it"
    digit = mid.endswith("digit")
    L = [f"# Sereni {d['name']} — " + ("Libretto d'uso e manutenzione" if it else "User and maintenance manual"), "",
         (f"Sereni Macchine da Caffè S.r.l., Firenze. Edizione {d['year']}, rev. 1. Conservare con il macinacaffè." if it else
          f"Sereni Macchine da Caffè S.r.l., Florence. {d['year']} edition, rev. 1. Keep with the grinder."),
         (f"Modello: {d['name']} (macinacaffè professionale, macine piane da 65 mm)." if it else
          f"Model: {d['name']} (professional grinder, 65 mm flat burrs)."), ""]

    L += [h(2, "1. Descrizione", "1. Description", lang), topics("com'è fatto il macinacaffè, come funziona", "what grinder is this, how it works"), ""]
    L.append((f"Macinacaffè per bar con macine piane in acciaio temprato da 65 mm (MC-7010), motore da 350 W, tramoggia da 1,2 kg (MC-7040). "
              f"Dosatura: {d['dosing_it']}." if it else
              f"Bar grinder with 65 mm hardened steel flat burrs (MC-7010), 350 W motor, 1.2 kg hopper (MC-7040). Dosing: {d['dosing_en']}."))
    L += ["", d["diff_it"] if it else d["diff_en"], ""]

    L += [h(2, "2. Dati tecnici", "2. Technical data", lang),
          topics("dati tecnici, tensione, potenza, matricola, targhetta", "technical data, voltage, power, serial number plate, where is the serial number"),
          "", "| | |", "|---|---|"]
    rows = ([("Macine", "piane 65 mm acciaio temprato (MC-7010), viti MC-7011"), ("Motore", "350 W, 230 V (MC-7020) o 110 V (MC-7021), condensatore MC-7025"),
             ("Tramoggia", "1,2 kg (MC-7040), saracinesca MC-7041"), ("Dosatura", d["dosing_it"]), ("Dimensioni", d["size"]),
             ("Matricola", "targhetta sotto la base, formato G + anno + numero (es. G24-0177)")] if it else
            [("Burrs", "65 mm flat, hardened steel (MC-7010), screws MC-7011"), ("Motor", "350 W, 230 V (MC-7020) or 110 V (MC-7021), capacitor MC-7025"),
             ("Hopper", "1.2 kg (MC-7040), shutter MC-7041"), ("Dosing", d["dosing_en"]), ("Size", d["size"]),
             ("Serial number", "plate under the base, format G + year + number (e.g. G24-0177)")])
    L += [f"| {k} | {v} |" for k, v in rows] + [""]

    L += [h(2, "3. Installazione", "3. Installation", lang), topics("installazione, collegamento, primo avvio", "installation, connection, first start-up"), ""]
    L.append("Appoggiare su un piano stabile con i piedini antivibranti (MC-7080). Verificare la tensione di targa. Al primo avvio macinare e buttare "
             "200 g di caffè per assestare le macine." if it else
             "Place on a stable counter on the anti-vibration feet (MC-7080). Check the rated voltage. At first start-up grind and discard 200 g of "
             "coffee to bed in the burrs.")
    L.append("")

    L += [h(2, "4. Uso quotidiano", "4. Daily use", lang),
          topics("uso quotidiano, regolare la macinatura, dosare", "daily use, how to adjust the grind, dosing"), ""]
    if it:
        L.append("- **Regolazione della macinatura**: ghiera (MC-7075), in senso orario più fine. Muovere di una tacca alla volta, a motore acceso.")
        L.append("- **Dosatura**: " + ("tenere premuto il tasto della dose sul display per cambiare il tempo; il portafiltro sulla forcella avvia la macinatura." if digit else
                                       "macinare nella camera, poi una tirata di leva per dose; non lasciare più di dieci dosi nella camera."))
    else:
        L.append("- **Grind adjustment**: collar (MC-7075), clockwise for finer. Move one notch at a time, with the motor running.")
        L.append("- **Dosing**: " + ("hold the dose button on the display to change the time; the portafilter on the fork starts grinding." if digit else
                                     "grind into the chamber, then one pull of the lever per dose; do not keep more than ten doses in the chamber."))
    L.append("")

    L += [h(2, "5. Manutenzione ordinaria", "5. Routine maintenance", lang),
          topics("manutenzione ordinaria, pulizia, cosa deve fare l'utente", "routine maintenance, what the user must do, cleaning schedule"), ""]
    L += [h(3, "Ogni giorno, a fine servizio", "Every day, at closing time", lang),
          topics("pulizia giornaliera", "daily cleaning")]
    L.append(("- Svuotare " + ("lo scivolo (MC-7063) e la forcella" if digit else "il dosatore") + " e pulire con il pennello, senza acqua.") if it else
             ("- Empty " + ("the chute (MC-7063) and the fork" if digit else "the doser") + " and brush clean, no water."))
    L += ["", h(3, "Ogni settimana", "Every week", lang), topics("pulizia settimanale, tramoggia", "weekly cleaning, hopper")]
    L.append("- Svuotare e lavare la tramoggia (acqua tiepida, asciugare bene)." if it else "- Empty and wash the hopper (lukewarm water, dry well).")
    L += ["", h(3, "Ogni mese", "Every month", lang), topics("pulizia delle macine", "clean the burrs")]
    L.append("- Chiudere la saracinesca, svitare la ghiera e pulire macine e camera con il pennello." if it else
             "- Close the shutter, unscrew the collar and brush the burrs and the chamber clean.")
    L += ["", h(3, "Ogni 12 mesi o 800 kg", "Every 12 months or 800 kg", lang), topics("sostituire le macine, ogni quanto si cambiano le macine", "replace the burrs, how often to change the burrs")]
    L.append("- Sostituire le macine (MC-7010) e le viti (MC-7011). Operazione da 20 minuti, vedere la scheda del ricambio." if it else
             "- Replace the burrs (MC-7010) and screws (MC-7011). A 20-minute job, see the part sheet.")
    L.append("")

    L += [h(2, "6. Spie e segnali", "6. Lights and signals", lang), topics("spie, rumori, allarmi", "warning lights, noises, alarms"), "",
          "| Segnale | Significato | Cosa fare |" if it else "| Signal | Meaning | What to do |", "|---|---|---|"]
    sig = [("Il motore ronza e non gira", "macine bloccate da un corpo estraneo", "spegnere e pulire la camera",
            "Motor hums and does not turn", "burrs jammed by a foreign object", "switch off and clear the chamber"),
           ("Odore di bruciato", "motore surriscaldato", "spegnere, chiamare il service",
            "Burning smell", "motor overheating", "switch off, call service"),
           ("Rumore metallico", "viti delle macine allentate o macine scheggiate", "fermarlo subito",
            "Metallic noise", "loose burr screws or chipped burrs", "stop it at once")]
    if digit:
        sig.append(("Display spento", "fusibile o scheda elettronica", "controllare il fusibile sotto la base",
                    "Display off", "fuse or electronic board", "check the fuse under the base"))
    L += ["| " + " | ".join(r[:3] if it else r[3:]) + " |" for r in sig] + [""]

    L += [h(2, "7. Cosa non fare", "7. What not to do", lang), topics("cosa non fare, avvertenze", "what not to do, warnings"), ""]
    L.append("- Non lavare le macine con acqua.\n- Non regolare la ghiera a motore fermo con caffè nella camera.\n- Non macinare chicchi caramellati o aromatizzati." if it else
             "- Do not wash the burrs with water.\n- Do not turn the collar with the motor off and coffee in the chamber.\n- Do not grind caramelised or flavoured beans.")
    L.append("")

    L += [h(2, "8. Ricambi di consumo consigliati a magazzino del cliente", "8. Consumables to keep in stock", lang),
          topics("ricambi da tenere a magazzino", "spare parts to keep in stock"), ""]
    L.append("MC-7010 coppia di macine (1), MC-7011 viti macine (1 kit), MC-7076 guarnizione ghiera (1), EL-3060 fusibili (1 kit)." if it else
             "MC-7010 pair of burrs (1), MC-7011 burr screws (1 kit), MC-7076 collar gasket (1), EL-3060 fuses (1 kit).")
    L.append("")
    L += [h(2, "9. Assistenza", "9. Support", lang), topics("come contattare l'assistenza", "how to contact support"), "", HELP_IT if it else HELP_EN]
    return "\n".join(L) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for mid, d in HX.items():
        for lang in ("it", "en"):
            (OUT / f"{mid}{'' if lang == 'it' else '.en'}.md").write_text(espresso(mid, d, False, lang), encoding="utf-8")
            n += 1
    for mid, d in MB.items():
        for lang in ("it", "en"):
            (OUT / f"{mid}{'' if lang == 'it' else '.en'}.md").write_text(espresso(mid, d, True, lang), encoding="utf-8")
            n += 1
    for mid, d in GR.items():
        for lang in ("it", "en"):
            (OUT / f"{mid}{'' if lang == 'it' else '.en'}.md").write_text(grinder(mid, d, lang), encoding="utf-8")
            n += 1
    print(f"manuals: {n} files ({len(HX) + len(MB) + len(GR)} models x 2 languages); hand-written kept: {sorted(HAND_WRITTEN)}")


if __name__ == "__main__":
    main()
