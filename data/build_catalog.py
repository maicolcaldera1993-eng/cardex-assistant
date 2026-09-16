"""Builds data/catalog.json and data/models.json for the fictional manufacturer
"Sereni Macchine da Caffè" (Firenze).

The data is hand-written here rather than in raw JSON so that compatibility
sets, trap pairs and supersessions stay readable and reviewable. Run:

    python data/build_catalog.py

Fields per part (see docs): code, group, family_scope, models, description_it,
description_en, aliases_it, aliases_en, voltage, supersedes, superseded_by,
price_eur, stock, order_rank (1 = ordered every day ... 5 = rarely).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

MODELS = [
    # id, name, family, year, type, groups, aliases (expected mis-spellings / spoken forms)
    ("marea-2", "Marea 2", "Marea", 2024, "heat-exchanger, 2 groups, volumetric", 2,
     ["Maria 2", "Mariah 2", "Marie 2", "la Marea due", "the Marea two", "Marea due"]),
    ("marea-2-plus", "Marea 2 Plus", "Marea", 2025, "heat-exchanger, 2 groups, volumetric, PID", 2,
     ["Maria 2 Plus", "Mariah 2 Plus", "la Marea due plus", "the Marea two plus"]),
    ("marea-2-evo", "Marea 2 Evo", "Marea", 2026, "heat-exchanger, 2 groups, volumetric, display", 2,
     ["Maria 2 Evo", "Mariah 2 Evo", "la Marea due evo", "the Marea two evo", "Marea 2 Ivo"]),
    ("giglio-1", "Giglio 1", "Giglio", 2024, "compact heat-exchanger, 1 group, vibration pump", 1,
     ["giggly 1", "jiggly 1", "Gigli 1", "Gilio 1", "Jiglio 1", "il Giglio uno", "the giggly one"]),
    ("giglio-1-plus", "Giglio 1 Plus", "Giglio", 2026, "compact heat-exchanger, 1 group, rotary pump", 1,
     ["giggly 1 Plus", "jiggly 1 Plus", "Gigli 1 Plus", "il Giglio uno plus", "the giggly one plus"]),
    ("onda-mb2", "Onda MB2", "Onda", 2024, "multi-boiler, 2 groups, PID", 2,
     ["Honda MB2", "Anda MB2", "Onda M B 2", "la Onda emme bi due", "the Onda M B two"]),
    ("onda-mb3", "Onda MB3", "Onda", 2025, "multi-boiler, 3 groups, PID", 3,
     ["Honda MB3", "Anda MB3", "Onda M B 3", "la Onda emme bi tre", "the Onda M B three"]),
    ("onda-mb2-evo", "Onda MB2 Evo", "Onda", 2026, "multi-boiler, 2 groups, built-in scales, touch display", 2,
     ["Honda MB2 Evo", "Onda M B 2 Evo", "la Onda emme bi due evo", "the Onda M B two evo"]),
    ("monda-65", "Monda 65", "Monda", 2024, "grinder, 65 mm flat burrs, doser", 0,
     ["Monday 65", "Mondo 65", "la Monda sessantacinque", "the Monda sixty-five", "Manda 65"]),
    ("monda-65-digit", "Monda 65 Digit", "Monda", 2025, "grinder, 65 mm flat burrs, timed dosing, display", 0,
     ["Monday 65 Digit", "Mondo 65 Digit", "la Monda sessantacinque digit", "the Monda sixty-five digit"]),
]

EDITIONS = [
    {"name": "Vaniglia", "finish": "cream", "models": ["marea-2-plus", "giglio-1-plus"],
     "aliases": ["vanilla", "Vanilla edition", "edizione vaniglia", "la crema"]},
]

# Compatibility sets ---------------------------------------------------------
MAREA = ["marea-2", "marea-2-plus", "marea-2-evo"]
MAREA_OLD = ["marea-2", "marea-2-plus"]          # share boiler and heating element
GIGLIO = ["giglio-1", "giglio-1-plus"]
HX = MAREA + GIGLIO                              # same group head, same gaskets
ONDA = ["onda-mb2", "onda-mb3", "onda-mb2-evo"]
ONDA_OLD = ["onda-mb2", "onda-mb3"]              # share electronics
MACHINES = HX + ONDA
VOLUMETRIC = MAREA + ["giglio-1-plus"] + ONDA    # have a flowmeter
ROTARY = MAREA + ["giglio-1-plus"] + ONDA
PRESSOSTAT = ["marea-2", "marea-2-plus"] + GIGLIO
MONDA = ["monda-65", "monda-65-digit"]
ALL = MACHINES + MONDA

PARTS: list[dict] = []


def P(code, group, it, en, models, price, stock, rank,
      ait=(), aen=(), voltage=None, supersedes=None, superseded_by=None, note=None):
    PARTS.append({
        "code": code,
        "group": group,
        "models": list(models),
        "description_it": it,
        "description_en": en,
        "aliases_it": list(ait),
        "aliases_en": list(aen),
        "voltage": voltage,
        "supersedes": supersedes,
        "superseded_by": superseded_by,
        "price_eur": price,
        "stock": stock,
        "order_rank": rank,
        "note": note,
    })


# --------------------------------------------------------------------------
# GE — gruppo erogatore / group head
# --------------------------------------------------------------------------
P("GE-2140", "GE", "Guarnizione sottocoppa 8,5 mm, gruppo Marea/Giglio", "Group head gasket 8.5 mm, Marea/Giglio group",
  HX, 4.20, 480, 1, ["gomma del gruppo", "guarnizione del gruppo", "guarnizione portafiltro"], ["group gasket", "portafilter gasket", "the rubber ring on the group"])
P("GE-2141", "GE", "Guarnizione sottocoppa 8 mm sottile, gruppo Marea/Giglio", "Group head gasket 8 mm thin, Marea/Giglio group",
  HX, 4.20, 120, 3, ["guarnizione sottile"], ["thin group gasket"], note="Use when the portafilter locks too far right with the 8.5 mm gasket.")
P("GE-2410", "GE", "Guarnizione sottocoppa 9 mm, gruppo Onda", "Group head gasket 9 mm, Onda group",
  ONDA, 5.60, 210, 1, ["gomma del gruppo Onda"], ["Onda group gasket"], note="Trap pair with GE-2140: one digit swapped, different machine.")
P("GE-2150", "GE", "Doccetta inox 57 mm, gruppo Marea/Giglio", "Shower screen stainless 57 mm, Marea/Giglio group",
  HX, 6.80, 350, 1, ["doccia", "il disco forato", "filtro doccia"], ["shower screen", "dispersion screen", "the holed disc"])
P("GE-2151", "GE", "Doccetta inox 58,5 mm, gruppo Onda", "Shower screen stainless 58.5 mm, Onda group",
  ONDA, 8.40, 140, 2, ["doccia Onda"], ["Onda shower screen"])
P("GE-2152", "GE", "Vite doccetta M6 inox", "Shower screen screw M6 stainless",
  MACHINES, 0.90, 900, 3, ["vite della doccia"], ["shower screen screw"])
P("GE-2155", "GE", "Portadoccia (diffusore) ottone, gruppo Marea/Giglio", "Shower holder (diffuser) brass, Marea/Giglio group",
  HX, 14.50, 90, 3, ["diffusore", "portadoccetta"], ["diffuser", "shower holder", "dispersion block"])
P("GE-2156", "GE", "Portadoccia (diffusore) ottone, gruppo Onda", "Shower holder (diffuser) brass, Onda group",
  ONDA, 16.90, 45, 4, ["diffusore Onda"], ["Onda diffuser"])
P("GE-2160", "GE", "Elettrovalvola gruppo 3 vie completa 230 V", "Group solenoid valve 3-way complete 230 V",
  HX, 84.00, 40, 2, ["elettrovalvola del gruppo", "valvola tre vie"], ["three-way solenoid", "group solenoid valve"], voltage="230V")
P("GE-2161", "GE", "Elettrovalvola gruppo 3 vie completa 110 V", "Group solenoid valve 3-way complete 110 V",
  HX, 84.00, 18, 3, ["elettrovalvola del gruppo 110"], ["three-way solenoid 110 volt"], voltage="110V")
P("GE-2162", "GE", "Elettrovalvola gruppo 3 vie completa 24 V, Onda", "Group solenoid valve 3-way complete 24 V, Onda",
  ONDA, 92.00, 25, 2, ["elettrovalvola gruppo Onda"], ["Onda group solenoid"], voltage="24V", note="Onda machines run solenoids at 24 V from the control board.")
P("GE-2165", "GE", "Corpo elettrovalvola 3 vie senza bobina", "3-way solenoid valve body without coil",
  MACHINES, 52.00, 30, 4, ["corpo valvola"], ["valve body"])
P("GE-2170", "GE", "Gigleur 0,6 mm ingresso gruppo", "Group inlet jet (gicleur) 0.6 mm",
  HX, 3.10, 200, 3, ["gicleur", "restrittore", "ugello del gruppo"], ["gicleur", "flow restrictor", "group jet"])
P("GE-2171", "GE", "Gigleur 0,8 mm ingresso gruppo", "Group inlet jet (gicleur) 0.8 mm",
  HX, 3.10, 150, 4, ["gicleur zero otto"], ["gicleur zero point eight"])
P("GE-2175", "GE", "Camera di preinfusione, gruppo Onda", "Pre-infusion chamber, Onda group",
  ONDA, 38.00, 20, 4, ["camera preinfusione"], ["pre-infusion chamber"])
P("GE-2176", "GE", "OR camera di preinfusione Onda (kit 5)", "Pre-infusion chamber O-ring, Onda (kit of 5)",
  ONDA, 6.50, 80, 3, ["oring preinfusione"], ["pre-infusion o-ring"])
P("GE-2180", "GE", "Portafiltro completo 2 vie, manico nero, Marea/Giglio", "Portafilter complete 2-spout, black handle, Marea/Giglio",
  HX, 46.00, 60, 2, ["portafiltro doppio", "portafiltro due tazze"], ["double portafilter", "two-spout portafilter"])
P("GE-2181", "GE", "Portafiltro completo 1 via, manico nero, Marea/Giglio", "Portafilter complete 1-spout, black handle, Marea/Giglio",
  HX, 44.00, 35, 3, ["portafiltro singolo", "portafiltro una tazza"], ["single portafilter", "one-spout portafilter"], note="Trap: one digit from GE-2180, same group, different part.")
P("GE-2182", "GE", "Portafiltro completo 2 vie, manico nero, Onda", "Portafilter complete 2-spout, black handle, Onda",
  ONDA, 54.00, 40, 2, ["portafiltro doppio Onda"], ["Onda double portafilter"])
P("GE-2183", "GE", "Portafiltro senza fondo (naked), Onda", "Bottomless (naked) portafilter, Onda",
  ONDA, 58.00, 15, 4, ["portafiltro nudo", "portafiltro senza beccuccio"], ["naked portafilter", "bottomless portafilter"])
P("GE-2185", "GE", "Manico portafiltro nero con vite", "Portafilter handle black with screw",
  MACHINES, 9.90, 150, 3, ["manico del portafiltro"], ["portafilter handle"])
P("GE-2186", "GE", "Manico portafiltro crema, edizione Vaniglia", "Portafilter handle cream, Vaniglia edition",
  ["marea-2-plus", "giglio-1-plus"], 12.90, 30, 4, ["manico vaniglia", "manico crema"], ["vanilla handle", "cream handle"])
P("GE-2190", "GE", "Filtro 2 tazze 14 g", "Filter basket 2 cups 14 g",
  MACHINES, 5.20, 300, 2, ["cestello doppio", "filtro doppio"], ["double basket", "two-cup basket"])
P("GE-2191", "GE", "Filtro 2 tazze 18 g", "Filter basket 2 cups 18 g",
  MACHINES, 5.20, 260, 2, ["cestello diciotto grammi"], ["eighteen gram basket"])
P("GE-2192", "GE", "Filtro 1 tazza 7 g", "Filter basket 1 cup 7 g",
  MACHINES, 4.80, 200, 3, ["cestello singolo", "filtro singolo"], ["single basket", "one-cup basket"])
P("GE-2193", "GE", "Filtro cieco per pulizia", "Blind filter (backflush disc)",
  MACHINES, 4.50, 220, 2, ["filtro cieco", "cieco per il lavaggio"], ["blind basket", "backflush disc", "blank filter"])
P("GE-2195", "GE", "Molla fermafiltro", "Filter basket retaining spring",
  MACHINES, 0.80, 600, 3, ["molletta del filtro"], ["basket spring", "filter clip"])
P("GE-2196", "GE", "Beccuccio 2 vie cromato", "Spout 2-way chrome",
  MACHINES, 7.40, 120, 3, ["beccuccio doppio"], ["double spout"])
P("GE-2197", "GE", "Beccuccio 1 via cromato", "Spout 1-way chrome",
  MACHINES, 6.90, 90, 4, ["beccuccio singolo"], ["single spout"])
P("GE-2200", "GE", "Corpo gruppo completo ottone cromato, Marea/Giglio", "Group head body complete chrome brass, Marea/Giglio",
  HX, 310.00, 6, 5, ["gruppo completo", "corpo del gruppo"], ["group head body", "complete group"])
P("GE-2201", "GE", "Corpo gruppo completo con camicia riscaldata, Onda", "Group head body complete with heating jacket, Onda",
  ONDA, 480.00, 4, 5, ["gruppo completo Onda"], ["Onda group body"])
P("GE-2205", "GE", "Guarnizione flangia gruppo-scambiatore", "Group-to-heat-exchanger flange gasket",
  HX, 2.60, 180, 3, ["guarnizione flangia gruppo"], ["group flange gasket"])
P("GE-2210", "GE", "Kit revisione gruppo Marea/Giglio (guarnizione, doccetta, vite)", "Group service kit Marea/Giglio (gasket, screen, screw)",
  HX, 10.50, 200, 1, ["kit gruppo", "kit revisione gruppo"], ["group service kit", "group rebuild kit"])
P("GE-2211", "GE", "Kit revisione gruppo Onda (guarnizione, doccetta, OR)", "Group service kit Onda (gasket, screen, o-rings)",
  ONDA, 16.80, 90, 1, ["kit gruppo Onda"], ["Onda group service kit"])
P("GE-2220", "GE", "Sonda temperatura gruppo PT100, Onda", "Group temperature probe PT100, Onda",
  ONDA, 24.00, 40, 3, ["sonda del gruppo", "sensore temperatura gruppo"], ["group temperature sensor", "group probe"])
P("GE-2221", "GE", "Resistenza camicia gruppo 150 W 230 V, Onda", "Group jacket heating element 150 W 230 V, Onda",
  ONDA, 42.00, 20, 4, ["resistenza del gruppo"], ["group heater", "group heating element"], voltage="230V")
P("GE-2222", "GE", "Resistenza camicia gruppo 150 W 110 V, Onda", "Group jacket heating element 150 W 110 V, Onda",
  ONDA, 42.00, 8, 5, ["resistenza del gruppo 110"], ["group heater 110 volt"], voltage="110V")
P("GE-2230", "GE", "Tubo rame scambiatore-gruppo, Marea 2 / 2 Plus", "Copper pipe heat-exchanger to group, Marea 2 / 2 Plus",
  MAREA_OLD, 18.00, 30, 4, ["tubo dello scambiatore"], ["exchanger pipe"])
P("GE-2231", "GE", "Tubo rame scambiatore-gruppo, Marea 2 Evo", "Copper pipe heat-exchanger to group, Marea 2 Evo",
  ["marea-2-evo"], 21.00, 15, 4, ["tubo scambiatore Evo"], ["Evo exchanger pipe"], note="New boiler geometry on the Evo: not interchangeable with GE-2230.")
P("GE-2232", "GE", "Tubo rame scambiatore-gruppo, Giglio", "Copper pipe heat-exchanger to group, Giglio",
  GIGLIO, 15.00, 20, 4, ["tubo scambiatore Giglio"], ["Giglio exchanger pipe"])
P("GE-2240", "GE", "Raccordo ingresso gruppo 1/4\" ottone", "Group inlet fitting 1/4\" brass",
  MACHINES, 4.30, 100, 4, ["raccordo del gruppo"], ["group fitting"])
P("GE-2245", "GE", "OR raccordo gruppo (kit 10)", "Group fitting O-ring (kit of 10)",
  MACHINES, 3.50, 150, 3, ["oring del raccordo"], ["fitting o-ring"])
P("GE-2250", "GE", "Guarnizione portafiltro cieco silicone (per lavaggio)", "Blind portafilter silicone gasket (for backflush)",
  MACHINES, 3.90, 80, 4, [], ["backflush gasket"])
P("GE-2260", "GE", "Leva erogazione manuale con micro, Marea 2", "Manual brew lever with microswitch, Marea 2",
  ["marea-2"], 28.00, 12, 5, ["levetta erogazione"], ["brew lever"], note="Only the 2024 Marea 2 has the auxiliary manual lever.")

# --------------------------------------------------------------------------
# CA — caldaia / boiler
# --------------------------------------------------------------------------
P("CA-1180", "CA", "Resistenza caldaia 3000 W 230 V, Marea 2 / 2 Plus", "Boiler heating element 3000 W 230 V, Marea 2 / 2 Plus",
  MAREA_OLD, 96.00, 30, 2, ["resistenza", "resistenza della caldaia"], ["heating element", "boiler element", "heater"], voltage="230V")
P("CA-1181", "CA", "Resistenza caldaia 3000 W 110 V, Marea 2 / 2 Plus", "Boiler heating element 3000 W 110 V, Marea 2 / 2 Plus",
  MAREA_OLD, 96.00, 12, 3, ["resistenza centodieci"], ["heating element 110 volt"], voltage="110V", note="Trap triple CA-1180/1181/1182: same element, three voltages.")
P("CA-1182", "CA", "Resistenza caldaia 4500 W 400 V trifase, Marea 2 / 2 Plus", "Boiler heating element 4500 W 400 V three-phase, Marea 2 / 2 Plus",
  MAREA_OLD, 118.00, 10, 3, ["resistenza trifase", "resistenza quattrocento"], ["three-phase element", "400 volt element"], voltage="400V")
P("CA-1185", "CA", "Resistenza caldaia 3500 W 230 V, Marea 2 Evo", "Boiler heating element 3500 W 230 V, Marea 2 Evo",
  ["marea-2-evo"], 104.00, 18, 2, ["resistenza Evo"], ["Evo heating element"], voltage="230V", note="Evo boiler has a different flange: CA-1180 does not fit.")
P("CA-1186", "CA", "Resistenza caldaia 3500 W 110 V, Marea 2 Evo", "Boiler heating element 3500 W 110 V, Marea 2 Evo",
  ["marea-2-evo"], 104.00, 6, 3, [], ["Evo element 110 volt"], voltage="110V")
P("CA-1187", "CA", "Resistenza caldaia 5000 W 400 V trifase, Marea 2 Evo", "Boiler heating element 5000 W 400 V three-phase, Marea 2 Evo",
  ["marea-2-evo"], 126.00, 5, 4, [], ["Evo three-phase element"], voltage="400V")
P("CA-1190", "CA", "Resistenza caldaia 1800 W 230 V, Giglio", "Boiler heating element 1800 W 230 V, Giglio",
  GIGLIO, 72.00, 20, 2, ["resistenza Giglio"], ["Giglio heating element"], voltage="230V")
P("CA-1191", "CA", "Resistenza caldaia 1500 W 110 V, Giglio", "Boiler heating element 1500 W 110 V, Giglio",
  GIGLIO, 72.00, 8, 3, [], ["Giglio element 110 volt"], voltage="110V")
P("CA-1200", "CA", "Resistenza caldaia vapore 3200 W 230 V, Onda MB2 / MB2 Evo", "Steam boiler heating element 3200 W 230 V, Onda MB2 / MB2 Evo",
  ["onda-mb2", "onda-mb2-evo"], 112.00, 14, 2, ["resistenza vapore", "resistenza caldaia vapore"], ["steam boiler element", "steam heater"], voltage="230V")
P("CA-1201", "CA", "Resistenza caldaia vapore 3200 W 110 V, Onda MB2 / MB2 Evo", "Steam boiler heating element 3200 W 110 V, Onda MB2 / MB2 Evo",
  ["onda-mb2", "onda-mb2-evo"], 112.00, 6, 3, [], ["steam element 110 volt"], voltage="110V")
P("CA-1202", "CA", "Resistenza caldaia vapore 4800 W 400 V trifase, Onda MB3", "Steam boiler heating element 4800 W 400 V three-phase, Onda MB3",
  ["onda-mb3"], 138.00, 5, 3, ["resistenza vapore MB3"], ["MB3 steam element"], voltage="400V")
P("CA-1203", "CA", "Resistenza caldaia vapore 4800 W 230 V, Onda MB3", "Steam boiler heating element 4800 W 230 V, Onda MB3",
  ["onda-mb3"], 138.00, 4, 4, [], ["MB3 steam element 230 volt"], voltage="230V")
P("CA-1210", "CA", "Resistenza caldaia caffè 800 W 230 V (per gruppo), Onda", "Coffee boiler heating element 800 W 230 V (per group), Onda",
  ONDA, 58.00, 30, 2, ["resistenza caldaia caffè", "resistenza caldaietta"], ["coffee boiler element", "brew boiler heater"], voltage="230V")
P("CA-1211", "CA", "Resistenza caldaia caffè 800 W 110 V (per gruppo), Onda", "Coffee boiler heating element 800 W 110 V (per group), Onda",
  ONDA, 58.00, 10, 3, [], ["brew boiler heater 110 volt"], voltage="110V")
P("CA-1220", "CA", "Guarnizione flangia resistenza, Marea/Giglio", "Heating element flange gasket, Marea/Giglio",
  HX, 2.90, 200, 2, ["guarnizione della resistenza"], ["element gasket", "heater flange gasket"])
P("CA-1221", "CA", "Guarnizione flangia resistenza, Onda", "Heating element flange gasket, Onda",
  ONDA, 3.40, 90, 2, ["guarnizione resistenza Onda"], ["Onda element gasket"])
P("CA-1230", "CA", "Sonda di livello caldaia 100 mm con isolante, Marea/Giglio", "Boiler level probe 100 mm with insulator, Marea/Giglio",
  HX, 17.50, 80, 2, ["sonda livello", "sonda del livello", "sonda dell'acqua"], ["level probe", "water level sensor", "autofill probe"])
P("CA-1231", "CA", "Sonda di livello caldaia vapore 130 mm, Onda", "Steam boiler level probe 130 mm, Onda",
  ONDA, 19.50, 40, 2, ["sonda livello Onda"], ["Onda level probe"])
P("CA-1232", "CA", "Isolante teflon sonda di livello (kit 5)", "Level probe PTFE insulator (kit of 5)",
  MACHINES, 4.80, 120, 3, ["isolante della sonda", "teflon della sonda"], ["probe insulator", "probe teflon"])
P("CA-1240", "CA", "Pressostato 0,5–1,4 bar", "Pressurestat 0.5–1.4 bar",
  PRESSOSTAT, 46.00, 40, 2, ["pressostato", "il pressostato della caldaia"], ["pressurestat", "pressure switch", "boiler pressure switch"], note="Not fitted on Marea 2 Evo (pressure transducer CA-1245) nor on Onda.")
P("CA-1241", "CA", "Membrana pressostato", "Pressurestat diaphragm",
  PRESSOSTAT, 8.50, 60, 4, ["membrana del pressostato"], ["pressurestat diaphragm"])
P("CA-1245", "CA", "Trasduttore di pressione caldaia 0–3 bar", "Boiler pressure transducer 0–3 bar",
  ["marea-2-evo"] + ONDA, 64.00, 25, 3, ["sensore di pressione", "trasduttore"], ["pressure sensor", "pressure transducer"])
P("CA-1250", "CA", "Valvola di sicurezza 1,8 bar certificata", "Safety valve 1.8 bar certified",
  MACHINES, 26.00, 90, 2, ["valvola di sicurezza", "valvola sicurezza caldaia"], ["safety valve", "pressure relief valve"])
P("CA-1251", "CA", "Valvola di sicurezza 2,2 bar caldaia vapore, Onda", "Safety valve 2.2 bar steam boiler, Onda",
  ONDA, 29.00, 30, 3, ["valvola sicurezza Onda"], ["Onda safety valve"])
P("CA-1260", "CA", "Valvola antidepressione 1/4\"", "Anti-vacuum valve 1/4\"",
  MACHINES, 14.80, 150, 1, ["antidepressione", "valvola antivuoto", "la valvolina che fischia"], ["anti-vacuum valve", "vacuum breaker", "the little valve that hisses"])
P("CA-1261", "CA", "OR valvola antidepressione (kit 10)", "Anti-vacuum valve O-ring (kit of 10)",
  MACHINES, 3.20, 200, 3, ["oring antidepressione"], ["vacuum valve o-ring"])
P("CA-1270", "CA", "Termostato di sicurezza 165 °C a riarmo, Marea/Giglio", "Safety thermostat 165 °C manual reset, Marea/Giglio",
  HX, 12.60, 70, 3, ["termostato di sicurezza", "termico", "il termostato che scatta"], ["safety thermostat", "high-limit thermostat", "thermal cutout"])
P("CA-1271", "CA", "Termostato di sicurezza 140 °C caldaia caffè, Onda", "Safety thermostat 140 °C coffee boiler, Onda",
  ONDA, 12.60, 40, 3, ["termostato caldaietta"], ["brew boiler thermostat"])
P("CA-1280", "CA", "Manometro doppio pompa/caldaia 0–16 / 0–3 bar", "Dual gauge pump/boiler 0–16 / 0–3 bar",
  MAREA_OLD + GIGLIO, 32.00, 30, 3, ["manometro", "manometro doppio"], ["dual gauge", "pressure gauge", "manometer"])
P("CA-1281", "CA", "Manometro singolo pompa 0–16 bar", "Single pump gauge 0–16 bar",
  ["marea-2-evo"] + ONDA, 21.00, 25, 4, ["manometro pompa"], ["pump gauge"], note="Evo and Onda show boiler pressure on the display; only the pump gauge is mechanical.")
P("CA-1290", "CA", "Sonda temperatura caldaia NTC, Marea 2 Plus", "Boiler temperature probe NTC, Marea 2 Plus",
  ["marea-2-plus"], 18.00, 30, 3, ["sonda temperatura", "sonda del PID"], ["temperature probe", "PID probe"])
P("CA-1291", "CA", "Sonda temperatura caldaia PT100, Marea 2 Evo / Onda", "Boiler temperature probe PT100, Marea 2 Evo / Onda",
  ["marea-2-evo"] + ONDA, 22.00, 40, 3, ["sonda PT100"], ["PT100 probe"], note="Trap: one digit from CA-1290, different sensor type, not interchangeable.")
P("CA-1300", "CA", "Scambiatore di calore rame, Marea 2 / 2 Plus", "Heat exchanger copper, Marea 2 / 2 Plus",
  MAREA_OLD, 88.00, 8, 5, ["scambiatore"], ["heat exchanger", "HX"])
P("CA-1301", "CA", "Scambiatore di calore rame, Marea 2 Evo", "Heat exchanger copper, Marea 2 Evo",
  ["marea-2-evo"], 94.00, 5, 5, ["scambiatore Evo"], ["Evo heat exchanger"])
P("CA-1302", "CA", "Scambiatore di calore rame, Giglio", "Heat exchanger copper, Giglio",
  GIGLIO, 66.00, 6, 5, ["scambiatore Giglio"], ["Giglio heat exchanger"])
P("CA-1310", "CA", "Rubinetto scarico caldaia 3/8\"", "Boiler drain tap 3/8\"",
  MACHINES, 11.20, 50, 4, ["rubinetto di scarico", "scarico caldaia"], ["drain valve", "boiler drain tap"])
P("CA-1311", "CA", "Guarnizione rubinetto scarico caldaia", "Boiler drain tap gasket",
  MACHINES, 1.40, 150, 4, [], ["drain tap gasket"])
P("CA-1320", "CA", "Caldaia completa 11 L rame, Marea 2 / 2 Plus", "Boiler complete 11 L copper, Marea 2 / 2 Plus",
  MAREA_OLD, 640.00, 3, 5, ["caldaia completa"], ["complete boiler"])
P("CA-1321", "CA", "Caldaia completa 12 L rame coibentata, Marea 2 Evo", "Boiler complete 12 L copper insulated, Marea 2 Evo",
  ["marea-2-evo"], 720.00, 2, 5, ["caldaia Evo"], ["Evo boiler"])
P("CA-1322", "CA", "Caldaia completa 4,5 L rame, Giglio", "Boiler complete 4.5 L copper, Giglio",
  GIGLIO, 420.00, 3, 5, ["caldaia Giglio"], ["Giglio boiler"])
P("CA-1323", "CA", "Caldaia vapore 7 L inox, Onda MB2 / MB2 Evo", "Steam boiler 7 L stainless, Onda MB2 / MB2 Evo",
  ["onda-mb2", "onda-mb2-evo"], 780.00, 2, 5, ["caldaia vapore"], ["steam boiler"])
P("CA-1324", "CA", "Caldaia vapore 10 L inox, Onda MB3", "Steam boiler 10 L stainless, Onda MB3",
  ["onda-mb3"], 890.00, 1, 5, ["caldaia vapore MB3"], ["MB3 steam boiler"])
P("CA-1325", "CA", "Caldaia caffè 0,8 L inox (per gruppo), Onda", "Coffee boiler 0.8 L stainless (per group), Onda",
  ONDA, 260.00, 6, 5, ["caldaietta", "caldaia caffè"], ["brew boiler", "coffee boiler"])
P("CA-1330", "CA", "Guarnizione flangia caldaia in fibra, Marea/Giglio", "Boiler flange gasket fibre, Marea/Giglio",
  HX, 5.60, 60, 4, ["guarnizione flangia caldaia"], ["boiler flange gasket"])
P("CA-1331", "CA", "Guarnizione flangia caldaia, Onda", "Boiler flange gasket, Onda",
  ONDA, 6.80, 30, 4, [], ["Onda boiler flange gasket"])
P("CA-1340", "CA", "Tappo caldaia 3/8\" con OR", "Boiler plug 3/8\" with O-ring",
  MACHINES, 3.80, 80, 4, ["tappo della caldaia"], ["boiler plug"])
P("CA-1350", "CA", "Coibentazione caldaia (kit), Marea 2 Evo / Onda MB2 Evo", "Boiler insulation jacket (kit), Marea 2 Evo / Onda MB2 Evo",
  ["marea-2-evo", "onda-mb2-evo"], 34.00, 10, 5, ["isolamento caldaia", "cappotto della caldaia"], ["boiler insulation", "boiler jacket"])

# --------------------------------------------------------------------------
# ID — circuito idraulico e pompa / hydraulics and pump
# --------------------------------------------------------------------------
P("ID-4010", "ID", "Pompa rotativa 100 L/h attacco 3/8\"", "Rotary pump 100 L/h 3/8\" ports",
  MAREA + ["giglio-1-plus", "onda-mb2", "onda-mb2-evo"], 142.00, 20, 2, ["pompa", "pompa rotativa", "la pompa"], ["rotary pump", "pump", "procon pump"])
P("ID-4011", "ID", "Pompa rotativa 150 L/h attacco 3/8\", Onda MB3", "Rotary pump 150 L/h 3/8\" ports, Onda MB3",
  ["onda-mb3"], 168.00, 5, 4, ["pompa MB3"], ["MB3 pump"])
P("ID-4015", "ID", "Motore pompa 165 W 230 V con condensatore", "Pump motor 165 W 230 V with capacitor",
  ROTARY, 124.00, 15, 3, ["motore della pompa", "motorino pompa"], ["pump motor"], voltage="230V")
P("ID-4016", "ID", "Motore pompa 165 W 110 V con condensatore", "Pump motor 165 W 110 V with capacitor",
  ROTARY, 124.00, 6, 4, [], ["pump motor 110 volt"], voltage="110V")
P("ID-4017", "ID", "Giunto motore-pompa", "Motor-to-pump coupling",
  ROTARY, 6.20, 40, 4, ["giunto della pompa", "giunto pompa motore"], ["pump coupling", "motor coupling"])
P("ID-4018", "ID", "Fascetta motore pompa con silent block", "Pump motor clamp with rubber mount",
  ROTARY, 9.40, 30, 5, ["fascetta del motore"], ["motor clamp"])
P("ID-4019", "ID", "Condensatore motore pompa 8 µF", "Pump motor capacitor 8 µF",
  ROTARY, 7.80, 40, 4, ["condensatore della pompa"], ["pump capacitor"])
P("ID-4020", "ID", "Pompa a vibrazione 230 V 48 W, Giglio 1", "Vibration pump 230 V 48 W, Giglio 1",
  ["giglio-1"], 28.00, 40, 2, ["pompa a vibrazione", "pompetta"], ["vibration pump", "vibe pump", "ulka pump"], voltage="230V")
P("ID-4021", "ID", "Pompa a vibrazione 110 V 48 W, Giglio 1", "Vibration pump 110 V 48 W, Giglio 1",
  ["giglio-1"], 28.00, 15, 3, [], ["vibration pump 110 volt"], voltage="110V")
P("ID-4025", "ID", "Valvola di espansione 12 bar regolabile", "Expansion valve 12 bar adjustable",
  HX, 22.00, 60, 2, ["valvola di espansione", "by-pass", "valvola di sovrapressione"], ["expansion valve", "over-pressure valve", "OPV"])
P("ID-4026", "ID", "Valvola di espansione 12 bar, Onda", "Expansion valve 12 bar, Onda",
  ONDA, 26.00, 25, 3, ["espansione Onda"], ["Onda expansion valve"])
P("ID-4027", "ID", "Kit guarnizioni valvola di espansione", "Expansion valve seal kit",
  MACHINES, 4.90, 80, 3, ["guarnizioni espansione"], ["expansion valve seals"])
P("ID-4030", "ID", "Valvola di ritegno 3/8\"", "Check valve 3/8\"",
  HX, 13.50, 50, 3, ["valvola di ritegno", "valvola di non ritorno", "ritegno"], ["check valve", "non-return valve", "one-way valve"])
P("ID-4031", "ID", "Valvola di ritegno 1/4\", Onda", "Check valve 1/4\", Onda",
  ONDA, 12.80, 30, 3, ["ritegno Onda"], ["Onda check valve"])
P("ID-4040", "ID", "Elettrovalvola carico caldaia 2 vie 230 V", "Boiler fill solenoid valve 2-way 230 V",
  HX, 48.00, 40, 2, ["elettrovalvola di carico", "valvola di carico", "elettrovalvola dell'acqua"], ["fill solenoid", "autofill valve", "inlet solenoid"], voltage="230V")
P("ID-4041", "ID", "Elettrovalvola carico caldaia 2 vie 110 V", "Boiler fill solenoid valve 2-way 110 V",
  HX, 48.00, 12, 3, [], ["fill solenoid 110 volt"], voltage="110V")
P("ID-4042", "ID", "Elettrovalvola carico caldaia 2 vie 24 V, Onda", "Boiler fill solenoid valve 2-way 24 V, Onda",
  ONDA, 52.00, 20, 2, ["carico Onda"], ["Onda fill solenoid"], voltage="24V")
P("ID-4045", "ID", "Corpo elettrovalvola carico senza bobina", "Fill solenoid valve body without coil",
  MACHINES, 24.00, 30, 4, [], ["fill valve body"])
P("ID-4050", "ID", "Flussometro completo con sensore", "Flowmeter complete with sensor",
  VOLUMETRIC, 68.00, 30, 2, ["flussometro", "contalitri", "il contatore dell'acqua"], ["flowmeter", "flow meter", "volumetric sensor"])
P("ID-4051", "ID", "Turbina flussometro", "Flowmeter turbine",
  VOLUMETRIC, 9.60, 60, 3, ["turbina del flussometro", "girante"], ["flowmeter turbine", "impeller"])
P("ID-4052", "ID", "Sensore Hall flussometro con cavo", "Flowmeter Hall sensor with cable",
  VOLUMETRIC, 19.00, 40, 3, ["sensore del flussometro"], ["flowmeter sensor", "hall sensor"])
P("ID-4053", "ID", "OR flussometro (kit 10)", "Flowmeter O-ring (kit of 10)",
  VOLUMETRIC, 3.20, 100, 4, [], ["flowmeter o-ring"])
P("ID-4060", "ID", "Filtro ingresso acqua 3/8\" con cartuccia", "Water inlet filter 3/8\" with cartridge",
  MACHINES, 14.00, 60, 3, ["filtro dell'acqua", "filtro ingresso"], ["inlet filter", "water filter"])
P("ID-4061", "ID", "Cartuccia filtro ingresso (kit 3)", "Inlet filter cartridge (kit of 3)",
  MACHINES, 6.50, 120, 3, ["cartuccia del filtro"], ["filter cartridge"])
P("ID-4070", "ID", "Raccordo diritto 1/4\" ottone", "Straight fitting 1/4\" brass",
  ALL, 2.10, 300, 4, ["raccordo un quarto"], ["quarter inch fitting"])
P("ID-4071", "ID", "Raccordo diritto 3/8\" ottone", "Straight fitting 3/8\" brass",
  MACHINES, 2.60, 250, 4, ["raccordo tre ottavi"], ["three-eighths fitting"])
P("ID-4072", "ID", "Raccordo a gomito 1/4\" ottone", "Elbow fitting 1/4\" brass",
  MACHINES, 2.80, 200, 4, ["gomito", "raccordo a gomito"], ["elbow fitting"])
P("ID-4073", "ID", "Raccordo a T 1/4\" ottone", "Tee fitting 1/4\" brass",
  MACHINES, 3.40, 120, 5, ["raccordo a ti"], ["tee fitting"])
P("ID-4080", "ID", "Tubo teflon 1/4\" (al metro)", "PTFE tube 1/4\" (per metre)",
  MACHINES, 3.90, 400, 3, ["tubo teflon", "tubo bianco"], ["teflon tube", "PTFE tube"])
P("ID-4081", "ID", "Tubo rame 6 mm (al metro)", "Copper tube 6 mm (per metre)",
  MACHINES, 4.40, 300, 4, ["tubo rame sei"], ["six millimetre copper tube"])
P("ID-4082", "ID", "Tubo rame 8 mm (al metro)", "Copper tube 8 mm (per metre)",
  MACHINES, 5.60, 200, 4, ["tubo rame otto"], ["eight millimetre copper tube"])
P("ID-4085", "ID", "Tubo carico rete 3/8\" 1,5 m inox con guarnizioni", "Mains inlet hose 3/8\" 1.5 m stainless with gaskets",
  MACHINES, 16.00, 80, 3, ["tubo di carico", "tubo dell'acqua"], ["inlet hose", "water hose", "supply hose"])
P("ID-4086", "ID", "Tubo scarico 20 mm 1 m con fascetta", "Drain hose 20 mm 1 m with clamp",
  MACHINES, 7.20, 100, 3, ["tubo di scarico"], ["drain hose"])
P("ID-4090", "ID", "OR 2043 EPDM (kit 10)", "O-ring 2043 EPDM (kit of 10)",
  ALL, 2.80, 200, 3, ["oring venti quarantatré"], ["o-ring twenty forty-three"])
P("ID-4091", "ID", "OR 2062 EPDM (kit 10)", "O-ring 2062 EPDM (kit of 10)",
  ALL, 2.80, 200, 3, ["oring venti sessantadue"], ["o-ring twenty sixty-two"])
P("ID-4092", "ID", "OR 3050 EPDM (kit 10)", "O-ring 3050 EPDM (kit of 10)",
  ALL, 3.20, 150, 4, ["oring trenta cinquanta"], ["o-ring thirty fifty"])
P("ID-4100", "ID", "Kit OR revisione idraulica completa, Marea/Giglio", "Complete hydraulic O-ring service kit, Marea/Giglio",
  HX, 18.50, 60, 2, ["kit oring", "kit guarnizioni idraulica"], ["o-ring kit", "hydraulic seal kit"])
P("ID-4101", "ID", "Kit OR revisione idraulica completa, Onda", "Complete hydraulic O-ring service kit, Onda",
  ONDA, 24.00, 30, 2, ["kit oring Onda"], ["Onda seal kit"])
P("ID-4110", "ID", "Riduttore di pressione ingresso 3/8\" 3 bar", "Inlet pressure reducer 3/8\" 3 bar",
  MACHINES, 38.00, 20, 4, ["riduttore di pressione"], ["pressure reducer", "pressure regulator"])
P("ID-4120", "ID", "Valvola by-pass pompa rotativa (regolazione 9 bar)", "Rotary pump bypass valve (9 bar adjustment)",
  ROTARY, 15.00, 25, 4, ["by-pass della pompa", "vite di regolazione pompa"], ["pump bypass", "pump adjustment screw"])

# --------------------------------------------------------------------------
# VA — vapore e acqua calda / steam and hot water
# --------------------------------------------------------------------------
P("VA-5010", "VA", "Rubinetto vapore completo a volantino, Marea/Giglio", "Steam valve complete with knob, Marea/Giglio",
  HX, 58.00, 25, 3, ["rubinetto del vapore", "rubinetto vapore completo"], ["steam valve", "steam tap complete"])
P("VA-5011", "VA", "Valvola vapore joystick completa, Onda", "Steam joystick valve complete, Onda",
  ONDA, 96.00, 15, 3, ["joystick del vapore", "levetta vapore"], ["steam joystick", "steam lever valve"])
P("VA-5015", "VA", "Kit guarnizioni rubinetto vapore (tenute + OR)", "Steam valve seal kit (seals + o-rings)",
  HX, 6.40, 250, 1, ["guarnizioni del vapore", "kit tenute vapore", "guarnizioni rubinetto"], ["steam valve seals", "steam tap seal kit", "steam valve gaskets"])
P("VA-5016", "VA", "Alberino rubinetto vapore con premistoppa", "Steam valve stem with gland",
  HX, 14.00, 60, 3, ["alberino del vapore", "perno del rubinetto"], ["steam valve stem", "steam spindle"])
P("VA-5017", "VA", "Manopola rubinetto vapore nera", "Steam valve knob black",
  HX, 6.80, 90, 3, ["manopola del vapore", "pomello vapore"], ["steam knob"])
P("VA-5018", "VA", "Manopola rubinetto vapore crema, edizione Vaniglia", "Steam valve knob cream, Vaniglia edition",
  ["marea-2-plus", "giglio-1-plus"], 8.90, 25, 4, ["manopola vaniglia", "manopola crema"], ["vanilla knob", "cream knob"])
P("VA-5019", "VA", "Kit guarnizioni valvola joystick, Onda", "Joystick valve seal kit, Onda",
  ONDA, 9.80, 80, 1, ["guarnizioni joystick"], ["joystick seals"])
P("VA-5020", "VA", "Lancia vapore inox 2 curve, Marea/Giglio", "Steam wand stainless 2-bend, Marea/Giglio",
  HX, 24.00, 50, 3, ["lancia del vapore", "lancia vapore", "cannello"], ["steam wand", "steam arm", "steam pipe"])
P("VA-5021", "VA", "Lancia vapore cool-touch, Onda", "Steam wand cool-touch, Onda",
  ONDA, 42.00, 30, 3, ["lancia cool touch", "lancia fredda"], ["cool-touch wand", "no-burn wand"])
P("VA-5025", "VA", "Terminale vapore 2 fori", "Steam tip 2-hole",
  MACHINES, 7.20, 120, 2, ["beccuccio del vapore", "terminale vapore due fori", "ugello vapore"], ["steam tip", "two-hole steam tip", "steam nozzle"])
P("VA-5026", "VA", "Terminale vapore 4 fori", "Steam tip 4-hole",
  MACHINES, 7.20, 100, 2, ["terminale quattro fori"], ["four-hole steam tip"])
P("VA-5027", "VA", "Snodo lancia vapore con OR", "Steam wand ball joint with o-rings",
  HX, 16.50, 40, 3, ["snodo della lancia", "sfera della lancia"], ["wand ball joint", "steam wand swivel"])
P("VA-5028", "VA", "OR snodo lancia (kit 10)", "Wand joint O-ring (kit of 10)",
  MACHINES, 3.60, 150, 2, ["oring della lancia", "guarnizioni dello snodo"], ["wand o-rings", "swivel o-rings"])
P("VA-5030", "VA", "Gommino antiscottatura lancia", "Steam wand anti-burn grip",
  HX, 3.40, 120, 3, ["gommino della lancia", "antiscottatura"], ["wand grip", "anti-burn rubber"])
P("VA-5040", "VA", "Lancia acqua calda inox", "Hot water wand stainless",
  MACHINES, 18.00, 40, 4, ["lancia dell'acqua calda"], ["hot water wand", "hot water spout"])
P("VA-5041", "VA", "Rubinetto acqua calda completo a volantino, Marea 2 / Giglio 1", "Hot water valve complete with knob, Marea 2 / Giglio 1",
  ["marea-2", "giglio-1"], 52.00, 15, 4, ["rubinetto dell'acqua calda"], ["hot water tap"])
P("VA-5042", "VA", "Elettrovalvola acqua calda 230 V, Marea 2 Plus / Evo / Giglio 1 Plus", "Hot water solenoid valve 230 V, Marea 2 Plus / Evo / Giglio 1 Plus",
  ["marea-2-plus", "marea-2-evo", "giglio-1-plus"], 46.00, 20, 3, ["elettrovalvola acqua calda"], ["hot water solenoid"], voltage="230V")
P("VA-5043", "VA", "Elettrovalvola acqua calda 24 V, Onda", "Hot water solenoid valve 24 V, Onda",
  ONDA, 49.00, 15, 3, [], ["Onda hot water solenoid"], voltage="24V")
P("VA-5045", "VA", "Miscelatore acqua calda regolabile", "Hot water mixing valve adjustable",
  ["marea-2-plus", "marea-2-evo"] + ONDA, 34.00, 20, 4, ["miscelatore", "miscelatore dell'acqua calda"], ["mixing valve", "hot water mixer"])
P("VA-5046", "VA", "Kit guarnizioni miscelatore", "Mixing valve seal kit",
  ["marea-2-plus", "marea-2-evo"] + ONDA, 5.20, 60, 4, [], ["mixer seals"])
P("VA-5060", "VA", "Leva joystick vapore con pomello, Onda", "Steam joystick lever with knob, Onda",
  ONDA, 22.00, 25, 4, ["leva del joystick"], ["joystick lever"])
P("VA-5070", "VA", "Kit revisione vapore completo (tenute, alberino, OR snodo), Marea/Giglio", "Complete steam service kit (seals, stem, joint o-rings), Marea/Giglio",
  HX, 19.90, 80, 2, ["kit vapore", "kit revisione vapore"], ["steam service kit", "steam rebuild kit"])

# --------------------------------------------------------------------------
# EL — elettronica e comandi / electronics and controls
# --------------------------------------------------------------------------
P("EL-3010", "EL", "Centralina elettronica v1, Marea 2 / Giglio 1", "Control board v1, Marea 2 / Giglio 1",
  ["marea-2", "giglio-1"], 210.00, 0, 3, ["centralina", "scheda", "la scheda elettronica", "cpu"], ["control box", "control board", "main board", "CPU"],
  superseded_by="EL-3012", note="Out of production since 2025. Superseded by EL-3012, which fits both v1 and v2 machines.")
P("EL-3011", "EL", "Centralina elettronica v2, Marea 2 Plus / Giglio 1 Plus (primo lotto 2025)", "Control board v2, Marea 2 Plus / Giglio 1 Plus (first 2025 batch)",
  ["marea-2-plus", "giglio-1-plus"], 235.00, 2, 4, ["centralina v2", "centralina plus"], ["v2 control board", "plus control board"],
  superseded_by="EL-3012", note="First-batch board with the flowmeter counting bug. Replaced by EL-3012.")
P("EL-3012", "EL", "Centralina elettronica v2 rev.B, Marea 2 / 2 Plus / Giglio 1 / 1 Plus", "Control board v2 rev.B, Marea 2 / 2 Plus / Giglio 1 / 1 Plus",
  ["marea-2", "marea-2-plus", "giglio-1", "giglio-1-plus"], 235.00, 18, 2, ["centralina rev bi", "centralina nuova"], ["rev B board", "replacement control board"],
  supersedes="EL-3010", note="Current replacement for EL-3010 and EL-3011. Needs the adapter harness EL-3036 on 2024 machines.")
P("EL-3013", "EL", "Centralina elettronica v3 con uscita display, Marea 2 Evo", "Control board v3 with display output, Marea 2 Evo",
  ["marea-2-evo"], 268.00, 10, 3, ["centralina Evo", "centralina v3"], ["Evo control board", "v3 board"])
P("EL-3020", "EL", "Centralina multi-caldaia PID, Onda MB2 / MB3", "Multi-boiler PID control board, Onda MB2 / MB3",
  ONDA_OLD, 390.00, 8, 3, ["centralina Onda", "scheda PID"], ["Onda control board", "PID board"])
P("EL-3021", "EL", "Centralina multi-caldaia con bilance e touch, Onda MB2 Evo", "Multi-boiler control board with scales and touch, Onda MB2 Evo",
  ["onda-mb2-evo"], 460.00, 5, 3, ["centralina Onda Evo"], ["Onda Evo board"])
P("EL-3030", "EL", "Pulsantiera 6 tasti a membrana con led, Marea 2 / Giglio 1", "Membrane touchpad 6 buttons with LEDs, Marea 2 / Giglio 1",
  ["marea-2", "giglio-1"], 88.00, 25, 2, ["pulsantiera", "tastiera", "i tasti", "tastierino"], ["touchpad", "keypad", "button pad", "the buttons"])
P("EL-3031", "EL", "Pulsantiera capacitiva 6 tasti, Marea 2 Plus / Giglio 1 Plus", "Capacitive touchpad 6 buttons, Marea 2 Plus / Giglio 1 Plus",
  ["marea-2-plus", "giglio-1-plus"], 112.00, 20, 2, ["pulsantiera capacitiva", "pulsantiera touch"], ["capacitive touchpad", "touch keypad"])
P("EL-3032", "EL", "Pulsantiera capacitiva 6 tasti con display OLED, Marea 2 Evo", "Capacitive touchpad 6 buttons with OLED display, Marea 2 Evo",
  ["marea-2-evo"], 148.00, 12, 2, ["pulsantiera Evo", "pulsantiera con display"], ["Evo touchpad", "touchpad with display"])
P("EL-3033", "EL", "Pulsantiera 5 tasti retroilluminata, Onda MB2 / MB3", "Backlit touchpad 5 buttons, Onda MB2 / MB3",
  ONDA_OLD, 118.00, 15, 2, ["pulsantiera Onda"], ["Onda touchpad"])
P("EL-3034", "EL", "Pannello touch per gruppo, Onda MB2 Evo", "Per-group touch panel, Onda MB2 Evo",
  ["onda-mb2-evo"], 165.00, 8, 3, ["touch del gruppo", "pannello touch"], ["group touch panel"])
P("EL-3035", "EL", "Cavo piatto pulsantiera-centralina 10 poli 60 cm", "Flat cable touchpad-to-board 10-pin 60 cm",
  HX, 8.50, 50, 3, ["cavo della pulsantiera", "piattina"], ["touchpad cable", "ribbon cable"])
P("EL-3036", "EL", "Cablaggio adattatore centralina rev.B su Marea 2 / Giglio 1 (2024)", "Adapter harness for rev.B board on Marea 2 / Giglio 1 (2024)",
  ["marea-2", "giglio-1"], 14.00, 30, 3, ["adattatore della centralina", "cablaggio adattatore"], ["board adapter harness", "adapter cable"], note="Required when fitting EL-3012 to a 2024 machine.")
P("EL-3040", "EL", "Display TFT 2,8\" con scheda, Marea 2 Evo", "TFT display 2.8\" with board, Marea 2 Evo",
  ["marea-2-evo"], 96.00, 10, 3, ["display", "schermo", "displayino"], ["display", "screen"])
P("EL-3041", "EL", "Display touch 5\" con scheda, Onda MB2 Evo", "Touch display 5\" with board, Onda MB2 Evo",
  ["onda-mb2-evo"], 210.00, 5, 3, ["display touch", "schermo touch"], ["touch screen", "touch display"])
P("EL-3042", "EL", "Cavo display-centralina", "Display-to-board cable",
  ["marea-2-evo", "onda-mb2-evo"], 9.80, 30, 4, ["cavo del display"], ["display cable"])
P("EL-3050", "EL", "Teleruttore resistenza 25 A bobina 230 V", "Heating element contactor 25 A 230 V coil",
  HX, 32.00, 30, 3, ["teleruttore", "contattore", "relè della resistenza"], ["contactor", "heater relay", "element contactor"], voltage="230V")
P("EL-3051", "EL", "Relè statico resistenza 25 A, Onda", "Solid-state relay heater 25 A, Onda",
  ONDA, 38.00, 20, 3, ["relè statico", "SSR"], ["solid state relay", "SSR"])
P("EL-3052", "EL", "Relè carico caldaia 10 A", "Boiler fill relay 10 A",
  ["marea-2", "giglio-1"], 9.60, 30, 4, ["relè del carico"], ["fill relay"], note="External relay only on v1 electronics; later boards drive the fill valve directly.")
P("EL-3055", "EL", "Trasformatore 230/12 V 20 VA", "Transformer 230/12 V 20 VA",
  HX, 24.00, 25, 4, ["trasformatore"], ["transformer"], voltage="230V")
P("EL-3056", "EL", "Trasformatore 110/12 V 20 VA", "Transformer 110/12 V 20 VA",
  HX, 24.00, 8, 5, [], ["transformer 110 volt"], voltage="110V")
P("EL-3057", "EL", "Alimentatore switching 24 V 60 W, Onda", "Switching power supply 24 V 60 W, Onda",
  ONDA, 46.00, 15, 3, ["alimentatore", "alimentatore ventiquattro volt"], ["power supply", "24 volt PSU"])
P("EL-3060", "EL", "Fusibile 10 A 5x20 ritardato (kit 5)", "Fuse 10 A 5x20 slow-blow (kit of 5)",
  ALL, 2.40, 200, 3, ["fusibile dieci ampere", "fusibili"], ["ten amp fuse", "fuses"])
P("EL-3061", "EL", "Fusibile 2 A 5x20 (kit 5)", "Fuse 2 A 5x20 (kit of 5)",
  ALL, 2.20, 200, 3, ["fusibile due ampere"], ["two amp fuse"])
P("EL-3062", "EL", "Portafusibile da pannello", "Panel fuse holder",
  ALL, 3.10, 60, 5, ["portafusibile"], ["fuse holder"])
P("EL-3070", "EL", "Interruttore generale 3 posizioni 20 A", "Main switch 3-position 20 A",
  HX, 28.00, 25, 3, ["interruttore generale", "interruttore principale", "l'interruttore"], ["main switch", "power switch"])
P("EL-3071", "EL", "Interruttore generale con led, Onda", "Main switch with LED, Onda",
  ONDA, 34.00, 15, 4, ["interruttore Onda"], ["Onda main switch"])
P("EL-3075", "EL", "Cavo alimentazione 3x2,5 mm² spina Schuko 2 m", "Power cord 3x2.5 mm² Schuko plug 2 m",
  MACHINES, 18.00, 40, 4, ["cavo di alimentazione", "cavo della corrente"], ["power cord", "mains cable"], voltage="230V")
P("EL-3076", "EL", "Cavo alimentazione spina NEMA 5-20 2 m", "Power cord NEMA 5-20 plug 2 m",
  MACHINES, 22.00, 10, 5, [], ["power cord 110 volt", "NEMA cord"], voltage="110V")
P("EL-3077", "EL", "Cavo alimentazione 5x2,5 mm² trifase 2 m senza spina", "Power cord 5x2.5 mm² three-phase 2 m no plug",
  MAREA + ["onda-mb3"], 26.00, 8, 5, ["cavo trifase"], ["three-phase cord"], voltage="400V")
P("EL-3080", "EL", "Morsettiera alimentazione 5 poli", "Power terminal block 5-pole",
  MACHINES, 6.40, 40, 5, ["morsettiera"], ["terminal block"])
P("EL-3085", "EL", "Bobina elettrovalvola 230 V 9 W", "Solenoid coil 230 V 9 W",
  HX, 22.00, 80, 2, ["bobina", "bobina dell'elettrovalvola", "la bobina"], ["solenoid coil", "coil"], voltage="230V")
P("EL-3086", "EL", "Bobina elettrovalvola 110 V 9 W", "Solenoid coil 110 V 9 W",
  HX, 22.00, 20, 3, [], ["coil 110 volt"], voltage="110V")
P("EL-3087", "EL", "Bobina elettrovalvola 24 V 9 W, Onda", "Solenoid coil 24 V 9 W, Onda",
  ONDA, 24.00, 50, 2, ["bobina Onda", "bobina ventiquattro volt"], ["Onda coil", "24 volt coil"], voltage="24V")
P("EL-3090", "EL", "Modulo PID scambiatore con sonda, Marea 2 Plus", "Heat-exchanger PID module with probe, Marea 2 Plus",
  ["marea-2-plus"], 84.00, 12, 4, ["modulo PID", "il PID"], ["PID module", "PID controller"])
P("EL-3095", "EL", "Scheda bilance integrate, Onda MB2 Evo", "Built-in scales board, Onda MB2 Evo",
  ["onda-mb2-evo"], 120.00, 6, 4, ["scheda delle bilance"], ["scales board"])
P("EL-3096", "EL", "Cella di carico 2 kg griglia, Onda MB2 Evo", "Load cell 2 kg drip tray, Onda MB2 Evo",
  ["onda-mb2-evo"], 42.00, 10, 4, ["cella di carico", "bilancia della griglia"], ["load cell", "tray scale"])
P("EL-3100", "EL", "Striscia led illuminazione piano lavoro 12 V", "LED strip work-surface lighting 12 V",
  ["marea-2-plus", "marea-2-evo"] + ONDA, 16.00, 30, 4, ["led del piano", "luci del piano"], ["work light", "LED strip"])
P("EL-3101", "EL", "Sensore livello vaschetta scarico, Marea 2 Evo / Onda MB2 Evo", "Drip tray level sensor, Marea 2 Evo / Onda MB2 Evo",
  ["marea-2-evo", "onda-mb2-evo"], 18.00, 15, 5, ["sensore della vaschetta"], ["drip tray sensor"])

# --------------------------------------------------------------------------
# CR — carrozzeria e accessori / body and accessories
# --------------------------------------------------------------------------
P("CR-6010", "CR", "Pannello laterale sinistro nero, Marea", "Side panel left black, Marea",
  MAREA, 74.00, 10, 4, ["fianco sinistro", "pannello laterale sinistro"], ["left side panel"])
P("CR-6011", "CR", "Pannello laterale destro nero, Marea", "Side panel right black, Marea",
  MAREA, 74.00, 10, 4, ["fianco destro"], ["right side panel"])
P("CR-6012", "CR", "Pannello laterale sinistro crema, Marea 2 Plus Vaniglia", "Side panel left cream, Marea 2 Plus Vaniglia",
  ["marea-2-plus"], 82.00, 4, 5, ["fianco vaniglia sinistro", "pannello crema"], ["vanilla left panel", "cream side panel"])
P("CR-6013", "CR", "Pannello laterale destro crema, Marea 2 Plus Vaniglia", "Side panel right cream, Marea 2 Plus Vaniglia",
  ["marea-2-plus"], 82.00, 4, 5, ["fianco vaniglia destro"], ["vanilla right panel"])
P("CR-6014", "CR", "Pannello laterale nero (dx/sx), Giglio", "Side panel black (left/right), Giglio",
  GIGLIO, 58.00, 8, 4, ["fianco Giglio"], ["Giglio side panel"])
P("CR-6015", "CR", "Pannello laterale crema (dx/sx), Giglio 1 Plus Vaniglia", "Side panel cream (left/right), Giglio 1 Plus Vaniglia",
  ["giglio-1-plus"], 64.00, 4, 5, ["fianco Giglio vaniglia"], ["Giglio vanilla panel"])
P("CR-6016", "CR", "Pannello laterale alluminio spazzolato, Onda", "Side panel brushed aluminium, Onda",
  ONDA, 118.00, 6, 5, ["fianco Onda"], ["Onda side panel"])
P("CR-6020", "CR", "Pannello posteriore inox, Marea", "Rear panel stainless, Marea",
  MAREA, 62.00, 8, 5, ["pannello posteriore", "schienale"], ["rear panel", "back panel"])
P("CR-6021", "CR", "Pannello frontale inox con logo, Marea", "Front panel stainless with logo, Marea",
  MAREA, 96.00, 5, 5, ["frontale", "pannello frontale"], ["front panel", "fascia"])
P("CR-6025", "CR", "Griglia scaldatazze inox, Marea 2", "Cup warmer grid stainless, Marea 2",
  MAREA, 44.00, 15, 4, ["griglia scaldatazze", "griglia delle tazze", "piano tazze"], ["cup warmer grid", "cup tray", "top grid"])
P("CR-6026", "CR", "Griglia scaldatazze inox, Giglio", "Cup warmer grid stainless, Giglio",
  GIGLIO, 32.00, 12, 4, ["griglia tazze Giglio"], ["Giglio cup grid"])
P("CR-6030", "CR", "Vaschetta raccogligocce inox, Marea", "Drip tray stainless, Marea",
  MAREA, 38.00, 15, 3, ["vaschetta", "vaschetta di scarico", "raccogligocce"], ["drip tray", "drain tray"])
P("CR-6031", "CR", "Griglia vaschetta inox, Marea", "Drip tray grid stainless, Marea",
  MAREA, 24.00, 25, 3, ["griglia della vaschetta", "grigliato"], ["drip tray grid", "drip grate"])
P("CR-6032", "CR", "Vaschetta raccogligocce con griglia, Giglio", "Drip tray with grid, Giglio",
  GIGLIO, 42.00, 12, 3, ["vaschetta Giglio"], ["Giglio drip tray"])
P("CR-6033", "CR", "Griglia vaschetta con sede bilance, Onda MB2 Evo", "Drip tray grid with scale seat, Onda MB2 Evo",
  ["onda-mb2-evo"], 58.00, 6, 4, ["griglia con bilance"], ["scale grid"])
P("CR-6034", "CR", "Griglia vaschetta inox, Onda MB2 / MB3", "Drip tray grid stainless, Onda MB2 / MB3",
  ONDA_OLD, 36.00, 10, 4, ["griglia Onda"], ["Onda drip grid"])
P("CR-6040", "CR", "Piedino regolabile M10 (kit 4)", "Adjustable foot M10 (kit of 4)",
  ALL, 12.00, 40, 4, ["piedini", "piedino regolabile"], ["feet", "adjustable foot"])
P("CR-6045", "CR", "Logo frontale Sereni cromato", "Front badge Sereni chrome",
  MACHINES, 9.50, 30, 5, ["logo", "targhetta"], ["badge", "logo"])
P("CR-6050", "CR", "Tamper 58 mm alluminio", "Tamper 58 mm aluminium",
  MACHINES, 22.00, 40, 3, ["tamper", "pressino"], ["tamper"])
P("CR-6051", "CR", "Spazzola pulizia gruppo", "Group cleaning brush",
  MACHINES, 4.90, 80, 3, ["spazzolino del gruppo"], ["group brush"])
P("CR-6052", "CR", "Pastiglie detergente gruppo (barattolo 100)", "Group cleaning tablets (jar of 100)",
  MACHINES, 19.00, 60, 2, ["pastiglie", "pastiglie per il lavaggio", "detergente"], ["cleaning tablets", "backflush tablets", "detergent"])

# --------------------------------------------------------------------------
# MC — macinacaffè / grinder
# --------------------------------------------------------------------------
P("MC-7010", "MC", "Coppia macine piane 65 mm acciaio temprato", "Pair of flat burrs 65 mm hardened steel",
  MONDA, 62.00, 40, 2, ["macine", "le macine", "coppia macine", "lame"], ["burrs", "burr set", "grinding discs", "blades"])
P("MC-7011", "MC", "Viti fissaggio macine M4 (kit 6)", "Burr fixing screws M4 (kit of 6)",
  MONDA, 2.40, 100, 4, ["viti delle macine"], ["burr screws"])
P("MC-7015", "MC", "Portamacina superiore con ghiera", "Upper burr carrier with adjustment ring",
  MONDA, 46.00, 8, 5, ["portamacina superiore"], ["upper burr carrier"])
P("MC-7016", "MC", "Portamacina inferiore", "Lower burr carrier",
  MONDA, 38.00, 8, 5, ["portamacina inferiore"], ["lower burr carrier"])
P("MC-7020", "MC", "Motore 350 W 230 V con condensatore", "Motor 350 W 230 V with capacitor",
  MONDA, 118.00, 10, 3, ["motore", "motore del macinino"], ["motor", "grinder motor"], voltage="230V")
P("MC-7021", "MC", "Motore 350 W 110 V con condensatore", "Motor 350 W 110 V with capacitor",
  MONDA, 118.00, 4, 4, [], ["grinder motor 110 volt"], voltage="110V")
P("MC-7025", "MC", "Condensatore motore 12 µF", "Motor capacitor 12 µF",
  MONDA, 8.40, 30, 3, ["condensatore"], ["capacitor", "run capacitor"])
P("MC-7026", "MC", "Ventola raffreddamento motore", "Motor cooling fan",
  MONDA, 14.00, 15, 4, ["ventola", "ventolina"], ["fan", "cooling fan"])
P("MC-7030", "MC", "Dosatore completo con stella e leva, Monda 65", "Doser complete with star and lever, Monda 65",
  ["monda-65"], 96.00, 6, 4, ["dosatore", "dosatore completo"], ["doser", "doser chamber"])
P("MC-7031", "MC", "Stella dosatore 6 settori, Monda 65", "Doser star 6-sector, Monda 65",
  ["monda-65"], 16.00, 15, 4, ["stella del dosatore", "girella"], ["doser star", "doser vanes"])
P("MC-7032", "MC", "Leva dosatore con pomello, Monda 65", "Doser lever with knob, Monda 65",
  ["monda-65"], 12.50, 20, 3, ["leva del dosatore", "levetta"], ["doser lever", "doser handle"])
P("MC-7033", "MC", "Molla di richiamo leva dosatore, Monda 65", "Doser lever return spring, Monda 65",
  ["monda-65"], 3.20, 40, 3, ["molla della leva"], ["lever spring"])
P("MC-7040", "MC", "Campana 1,2 kg policarbonato", "Hopper 1.2 kg polycarbonate",
  MONDA, 28.00, 20, 3, ["campana", "tramoggia", "contenitore dei chicchi"], ["hopper", "bean hopper"])
P("MC-7041", "MC", "Saracinesca campana", "Hopper shutter slide",
  MONDA, 6.80, 30, 4, ["saracinesca", "chiusura della campana"], ["hopper shutter", "hopper gate"])
P("MC-7042", "MC", "Coperchio campana", "Hopper lid",
  MONDA, 5.40, 30, 4, ["coperchio della campana"], ["hopper lid"])
P("MC-7050", "MC", "Forcella portafiltro regolabile", "Portafilter fork adjustable",
  MONDA, 14.00, 25, 3, ["forcella", "forchetta del portafiltro"], ["portafilter fork", "portafilter holder"])
P("MC-7060", "MC", "Scheda elettronica dosaggio a tempo, Monda 65 Digit", "Timed dosing electronic board, Monda 65 Digit",
  ["monda-65-digit"], 84.00, 8, 3, ["scheda del Digit", "centralina del macinino"], ["Digit board", "grinder control board"])
P("MC-7061", "MC", "Display con pulsanti, Monda 65 Digit", "Display with buttons, Monda 65 Digit",
  ["monda-65-digit"], 46.00, 10, 3, ["display del macinino"], ["grinder display"])
P("MC-7062", "MC", "Microinterruttore forcella, Monda 65 Digit", "Fork microswitch, Monda 65 Digit",
  ["monda-65-digit"], 4.60, 30, 3, ["micro della forcella", "microinterruttore"], ["fork microswitch", "micro switch"])
P("MC-7063", "MC", "Beccuccio uscita caffè antistatico, Monda 65 Digit", "Anti-static coffee chute, Monda 65 Digit",
  ["monda-65-digit"], 11.00, 20, 4, ["beccuccio del caffè", "scivolo"], ["coffee chute", "grinds spout"])
P("MC-7070", "MC", "Interruttore bipolare con spia, Monda 65", "Double-pole switch with lamp, Monda 65",
  ["monda-65"], 9.20, 20, 4, ["interruttore del macinino"], ["grinder switch"])
P("MC-7075", "MC", "Ghiera regolazione macinatura con fermo", "Grind adjustment collar with stop",
  MONDA, 32.00, 10, 4, ["ghiera", "ghiera di regolazione"], ["adjustment collar", "grind ring"])
P("MC-7076", "MC", "Guarnizione ghiera regolazione", "Adjustment collar gasket",
  MONDA, 2.60, 40, 4, ["guarnizione della ghiera"], ["collar gasket"])
P("MC-7080", "MC", "Piedino gomma antivibrazione (kit 4)", "Anti-vibration rubber foot (kit of 4)",
  MONDA, 6.00, 30, 5, ["piedini del macinino"], ["grinder feet"])


# --------------------------------------------------------------------------
# Validation and output
# --------------------------------------------------------------------------

def validate() -> None:
    codes = [p["code"] for p in PARTS]
    assert len(codes) == len(set(codes)), "duplicate codes"
    model_ids = {m[0] for m in MODELS}
    for p in PARTS:
        assert p["models"], p["code"]
        for m in p["models"]:
            assert m in model_ids, (p["code"], m)
        assert p["group"] == p["code"][:2], p["code"]
        for ref in (p["supersedes"], p["superseded_by"]):
            assert ref is None or ref in codes, (p["code"], ref)


def main() -> None:
    validate()
    models = [
        {"id": i, "name": n, "family": f, "year": y, "type": t, "groups": g, "aliases": a}
        for (i, n, f, y, t, g, a) in MODELS
    ]
    (HERE / "models.json").write_text(
        json.dumps({"manufacturer": "Sereni Macchine da Caffè", "city": "Firenze",
                    "models": models, "editions": EDITIONS}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (HERE / "catalog.json").write_text(
        json.dumps(PARTS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    by_group: dict[str, int] = {}
    for p in PARTS:
        by_group[p["group"]] = by_group.get(p["group"], 0) + 1
    print(f"{len(PARTS)} parts, {len(models)} models")
    for g, n in sorted(by_group.items()):
        print(f"  {g}: {n}")


if __name__ == "__main__":
    main()
