"""Hand-written notes for the parts that have a story. Everything else gets a
templated product sheet. Keys are part codes.

mounting: how it is fitted (goes on the product sheet and in the diagnosis panel)
notes:    history, gotchas, supersession details, what the help desk knows
"""

NOTES: dict[str, dict[str, str]] = {
    "GE-2140": {
        "mounting": "Rimuovere la doccetta (vite centrale), levare la vecchia guarnizione con un cacciavite piatto "
                    "facendo leva sul bordo, pulire la sede dal calcare, inserire la nuova con il lato smussato verso "
                    "il gruppo. Rimontare doccetta e vite. Aggancio del portafiltro al centro entro 5-10 caffè.",
        "notes": "Il ricambio più venduto. Durata tipica 6-12 mesi in un bar a 200 caffè al giorno. Se il portafiltro "
                 "aggancia oltre le ore 6 anche con guarnizione nuova, il bordo del portafiltro è consumato (GE-2180). "
                 "Non usare grasso al silicone sulla sede: la guarnizione scivola e fa bypass.",
    },
    "GE-2141": {
        "mounting": "Come GE-2140.",
        "notes": "Variante da 8 mm per gruppi con sede consumata dove la 8,5 mm fa agganciare il portafiltro troppo a "
                 "sinistra. Da usare solo se richiesto dal service.",
    },
    "GE-2410": {
        "mounting": "Come GE-2140, ma sulla Onda la doccetta è tenuta da due viti laterali.",
        "notes": "Attenzione al codice: GE-2410 (Onda, 9 mm) e GE-2140 (Marea/Giglio, 8,5 mm) si confondono a voce. "
                 "La 8,5 mm sulla Onda non tiene.",
    },
    "GE-2150": {
        "mounting": "Svitare la vite centrale M6, togliere la doccetta, pulire la sede, montare la nuova con la parte "
                    "convessa verso il basso. Non serrare oltre 2 Nm.",
        "notes": "Se i fori sono integri si recupera: 20 minuti in decalcificante caldo, spazzola, risciacquo. Si "
                 "sostituisce se bombata o con fori allargati. Il 70% delle richieste arriva da locali senza lavaggio "
                 "serale con filtro cieco: proporre sempre CR-6052.",
    },
    "GE-2160": {
        "mounting": "Chiudere l'acqua, scaricare la pressione, staccare i tre raccordi (ingresso, gruppo, scarico) "
                    "e i due fili della bobina. Montare la nuova rispettando il verso della freccia. Richiede chiave da "
                    "17 e accesso dal fianco.",
        "notes": "Se la valvola fa click ma il gruppo sputa a fine erogazione, quasi sempre è sporca e non rotta: "
                 "smontare il corpo (GE-2165) e pulire il pistoncino. Se la bobina non fa click: prima EL-3085.",
    },
    "GE-2180": {
        "mounting": "Nessun montaggio: si aggancia al gruppo.",
        "notes": "Bordo consumato dopo 3-4 anni: la guarnizione nuova non basta più. Compatibile con cestelli GE-2190/91.",
    },
    "CA-1180": {
        "mounting": "Solo con caldaia scarica e fredda. Togliere il pannello posteriore, scollegare i cavi (annotare "
                    "la posizione), svitare i 4 dadi della flangia, estrarre la resistenza, sostituire sempre la "
                    "guarnizione CA-1220. Serraggio a croce. Riempire la caldaia prima di ridare tensione.",
        "notes": "Verificare la tensione di targa prima di spedire: CA-1180 è 230 V monofase, CA-1181 è 110 V, "
                 "CA-1182 è 400 V trifase. Le tre si assomigliano. Sul Marea 2 Evo NON monta: flangia diversa, "
                 "usare CA-1185. Sostituzione con supporto del service, mai in autonomia.",
    },
    "CA-1185": {
        "mounting": "Come CA-1180. La flangia Evo ha 6 dadi.",
        "notes": "Introdotta con la caldaia coibentata del 2026. Non intercambiabile con CA-1180.",
    },
    "CA-1230": {
        "mounting": "Svitare la sonda dalla sommità della caldaia con chiave da 13, sostituire con l'isolante "
                    "nuovo (CA-1232), non serrare a fondo: 1/4 di giro oltre il contatto.",
        "notes": "Prima di sostituire: pulire la punta con carta abrasiva fine. Nel 60% dei casi 'non carica' o "
                 "'carica sempre' è calcare sulla sonda, non la sonda. Se l'isolante è crepato la sonda legge sempre "
                 "acqua e la caldaia non si riempie.",
    },
    "CA-1240": {
        "mounting": "Staccare il tubo capillare 1/8\" e i due faston, sostituire, ritarare con la vite centrale a "
                    "1,1-1,2 bar a macchina calda.",
        "notes": "Non presente su Marea 2 Evo e Onda (trasduttore CA-1245). Se la pressione oscilla di più di 0,3 bar "
                 "prima di sostituire provare la membrana CA-1241 e soffiare il capillare.",
    },
    "CA-1250": {
        "mounting": "Svitare e sostituire a caldaia fredda e scarica. Non manomettere la taratura.",
        "notes": "Componente di sicurezza a scadenza: sostituire ogni 2 anni o se ha sfiatato. Non riparare, non "
                 "pulire, non regolare.",
    },
    "CA-1260": {
        "mounting": "Svitare con chiave da 14 dalla sommità della caldaia, avvitare la nuova con teflon sul filetto.",
        "notes": "Il sibilo all'accensione che dura più di 5 minuti o la goccia sulla valvola: prima provare a "
                 "smontare e pulire lo spillo, poi sostituire l'OR CA-1261, poi la valvola. Il cliente lo fa da solo.",
    },
    "CA-1270": {
        "mounting": "Sul corpo caldaia, fissato con due viti. Il pulsante rosso di riarmo è accessibile togliendo "
                    "il pannello posteriore.",
        "notes": "Prima di ordinare: far premere il pulsante di riarmo. Se scatta di nuovo entro un giorno, la causa "
                 "è a monte (livello, pressostato, resistenza a secco).",
    },
    "ID-4010": {
        "mounting": "Con supporto del service. Staccare la pompa dal motore (fascetta e giunto ID-4017), scollegare "
                    "aspirazione e mandata, montare la nuova rispettando il verso di rotazione stampato sul corpo. "
                    "Regolare il by-pass a 9 bar con filtro cieco.",
        "notes": "Rumore metallico e pressione che non sale oltre 6 bar: pompa. Ronzio e pressione zero: motore o "
                 "condensatore ID-4019. Una pompa usurata da acqua dura si vede dal giunto: polvere nera.",
    },
    "ID-4025": {
        "mounting": "Sulla mandata della pompa. Svitare, sostituire, tarare a 12 bar.",
        "notes": "Se spurga in continuazione durante l'erogazione: espansione. Se spurga a macchina ferma: ritegno "
                 "ID-4030 o carico ID-4040. Distinguere chiedendo QUANDO gocciola.",
    },
    "ID-4040": {
        "mounting": "Sull'ingresso acqua, dopo il filtro. Due raccordi e la bobina. Rispettare il verso.",
        "notes": "Fa click ma non carica: filtro a rete interno intasato dal calcare, pulibile. Non fa click: bobina "
                 "(EL-3085) o centralina. Carica sempre: sonda CA-1230 o valvola bloccata aperta.",
    },
    "ID-4050": {
        "mounting": "Su ogni gruppo, tra elettrovalvola e scambiatore. Attenzione al verso della freccia; il sensore "
                    "si sfila senza aprire il circuito.",
        "notes": "Dosi che cambiano da un giorno all'altro: turbina sporca (ID-4051), pulibile. Dose infinita o "
                 "allarme flussometro: sensore ID-4052. Su Marea 2 Plus primo lotto (EL-3011) l'allarme era un bug "
                 "della centralina, non del flussometro.",
    },
    "VA-5015": {
        "mounting": "Chiudere il rubinetto, svitare il volantino e il premistoppa, estrarre l'alberino, sostituire "
                    "le due tenute e l'OR, rimontare senza serrare a fondo il premistoppa.",
        "notes": "Il cliente lo fa da solo in 10 minuti. Se dopo la sostituzione gocciola ancora, l'alberino è "
                 "rigato (VA-5016).",
    },
    "VA-5025": {
        "mounting": "Si svita a mano dalla lancia. Pulire il filetto.",
        "notes": "Vapore debole con pressione caldaia normale: quasi sempre il terminale intasato dal latte. Far "
                 "provare: svitare, lasciare 30 minuti in acqua calda con pastiglia, spillo nei fori.",
    },
    "EL-3010": {
        "mounting": "Non più applicabile: vedi EL-3012.",
        "notes": "FUORI PRODUZIONE dal marzo 2025. Sostituita da EL-3012 (v2 rev.B) che monta su Marea 2 e Giglio 1 "
                 "del 2024 SOLO con il cablaggio adattatore EL-3036. Se il cliente legge EL-3010 da una fattura "
                 "vecchia, ordinare EL-3012 + EL-3036 e prevedere il supporto del service per il montaggio e la "
                 "riprogrammazione delle dosi.",
    },
    "EL-3011": {
        "mounting": "Non più applicabile: vedi EL-3012.",
        "notes": "Primo lotto delle centraline v2 (Marea 2 Plus e Giglio 1 Plus, gennaio-marzo 2025): bug del "
                 "conteggio del flussometro che dava allarme dose. Sostituita in garanzia con EL-3012 senza adattatore.",
    },
    "EL-3012": {
        "mounting": "Con supporto del service. Togliere tensione, fotografare i connettori, sostituire la scheda, "
                    "sulle macchine 2024 interporre EL-3036. Alla riaccensione riprogrammare le 4 dosi per gruppo.",
        "notes": "Centralina corrente per tutta la famiglia Marea 2 / Marea 2 Plus / Giglio 1 / Giglio 1 Plus. "
                 "Sostituisce EL-3010 (richiede EL-3036) ed EL-3011 (diretta). Non monta su Marea 2 Evo (EL-3013).",
    },
    "EL-3030": {
        "mounting": "Si sfila dal frontale dopo aver tolto la cornice, si scollega la piattina EL-3035.",
        "notes": "Un tasto morto con led acceso: membrana. Tutti i tasti morti: piattina o centralina. Il cliente lo "
                 "fa da solo.",
    },
    "EL-3036": {
        "mounting": "Si interpone tra il connettore a 10 poli della macchina 2024 e la centralina EL-3012.",
        "notes": "Obbligatorio con EL-3012 su Marea 2 e Giglio 1 del 2024. Senza, la scheda si accende ma non "
                 "legge il flussometro. Spedire sempre insieme.",
    },
    "EL-3085": {
        "mounting": "Si sfila dal corpo valvola togliendo il dado superiore. Rispettare la tensione.",
        "notes": "Bobina calda al tatto e nessun click: bruciata. Prima causa di 'il gruppo non eroga' su un solo "
                 "gruppo. Il cliente la cambia da solo.",
    },
    "MC-7010": {
        "mounting": "Svuotare la campana, aprire la ghiera fino a togliere il portamacina superiore, svitare le 3 "
                    "viti per macina, pulire le sedi, montare le nuove, azzerare la ghiera al contatto e riaprire di "
                    "mezzo giro.",
        "notes": "Durata 600-800 kg di caffè. Segnali: macinatura lenta, caffè che sa di bruciato, polvere tiepida. "
                 "Il cliente le cambia da solo con la scheda. Uguali su Monda 65 e Monda 65 Digit.",
    },
    "MC-7062": {
        "mounting": "Dietro la forcella, due viti. Regolare la lamella perché scatti a portafiltro inserito.",
        "notes": "Il Digit non parte e non fa click quando si inserisce il portafiltro: micro. Prima verificare che "
                 "la forcella non sia allentata.",
    },
    "CR-6052": {
        "mounting": "Una pastiglia nel filtro cieco, 5 cicli di 10 secondi per gruppo, poi 5 cicli di risciacquo.",
        "notes": "Il consumabile da proporre in quasi ogni chiamata sul gruppo. Una al giorno per gruppo.",
    },
}


# English versions of the hand-written notes (same keys as NOTES).
NOTES_EN: dict[str, dict[str, str]] = {
    "GE-2140": {
        "mounting": "Remove the shower screen (centre screw), lever the old gasket out with a flat screwdriver from the rim, "
                    "clean the seat of scale, fit the new one with the chamfered side towards the group. Refit screen and screw. "
                    "The portafilter should lock at the centre within 5-10 coffees.",
        "notes": "Best-selling part. Typical life 6-12 months in a bar doing 200 coffees a day. If the portafilter still locks "
                 "past 6 o'clock with a new gasket, the portafilter rim is worn (GE-2180). Never put silicone grease on the seat: "
                 "the gasket slips and bypasses.",
    },
    "GE-2141": {"mounting": "As GE-2140.",
                "notes": "8 mm variant for worn group seats where the 8.5 mm locks the portafilter too far left. Only on the service desk's advice."},
    "GE-2410": {"mounting": "As GE-2140, but on the Onda the shower screen is held by two side screws.",
                "notes": "Mind the code: GE-2410 (Onda, 9 mm) and GE-2140 (Marea/Giglio, 8.5 mm) sound alike. The 8.5 mm does not seal on the Onda."},
    "GE-2150": {
        "mounting": "Undo the M6 centre screw, remove the screen, clean the seat, fit the new one convex side down. Do not exceed 2 Nm.",
        "notes": "If the holes are intact it can be saved: 20 minutes in hot descaler, brush, rinse. Replace if domed or with worn-open holes. "
                 "70% of requests come from shops that skip the evening backflush with the blind filter: always suggest CR-6052.",
    },
    "GE-2160": {
        "mounting": "Close the water, release the pressure, disconnect the three fittings (inlet, group, discharge) and the two coil wires. "
                    "Fit the new valve respecting the arrow. 17 mm spanner, access from the side panel.",
        "notes": "If the valve clicks but the group spits at the end of the shot it is almost always dirty, not broken: open the body (GE-2165) "
                 "and clean the plunger. If the coil does not click: EL-3085 first.",
    },
    "GE-2180": {"mounting": "No fitting: it locks into the group.",
                "notes": "Rim worn after 3-4 years: a new gasket is no longer enough. Takes baskets GE-2190/91."},
    "CA-1180": {
        "mounting": "Only with the boiler drained and cold. Remove the rear panel, disconnect the wires (note their positions), undo the "
                    "4 flange nuts, pull the element, always replace gasket CA-1220. Tighten crosswise. Fill the boiler before powering up.",
        "notes": "Check the rating plate voltage before shipping: CA-1180 is 230 V single-phase, CA-1181 is 110 V, CA-1182 is 400 V "
                 "three-phase. They look alike. Does NOT fit the Marea 2 Evo: different flange, use CA-1185. Fitting with service support, never alone.",
    },
    "CA-1185": {"mounting": "As CA-1180. The Evo flange has 6 nuts.",
                "notes": "Introduced with the 2026 insulated boiler. Not interchangeable with CA-1180."},
    "CA-1230": {
        "mounting": "Unscrew the probe from the top of the boiler with a 13 mm spanner, replace with the new insulator (CA-1232), "
                    "do not overtighten: a quarter turn past contact.",
        "notes": "Before replacing: clean the tip with fine abrasive paper. In 60% of 'not filling' or 'always filling' calls it is scale on "
                 "the probe, not the probe. If the insulator is cracked the probe always reads water and the boiler never fills.",
    },
    "CA-1240": {
        "mounting": "Disconnect the 1/8\" capillary and the two spade terminals, replace, reset with the centre screw to 1.1-1.2 bar with the machine hot.",
        "notes": "Not fitted on Marea 2 Evo and Onda (transducer CA-1245). If pressure swings by more than 0.3 bar, try the diaphragm "
                 "CA-1241 and blow the capillary through before replacing.",
    },
    "CA-1250": {"mounting": "Unscrew and replace with the boiler cold and drained. Never touch the setting.",
                "notes": "Safety part with a service life: replace every 2 years or after it has vented. Do not repair, clean or adjust."},
    "CA-1260": {
        "mounting": "Unscrew with a 14 mm spanner from the top of the boiler, fit the new one with PTFE tape on the thread.",
        "notes": "A hiss at start-up lasting more than 5 minutes, or a drop on the valve: first remove and clean the pin, then replace "
                 "the o-ring CA-1261, then the valve. The customer can do it alone.",
    },
    "CA-1270": {"mounting": "On the boiler body, two screws. The red reset button is reachable after removing the rear panel.",
                "notes": "Before ordering: have the customer press the reset button. If it trips again within a day the cause is upstream (level, pressurestat, element run dry)."},
    "ID-4010": {
        "mounting": "With service support. Separate the pump from the motor (clamp and coupling ID-4017), disconnect suction and delivery, "
                    "fit the new pump respecting the rotation arrow stamped on the body. Set the bypass to 9 bar with the blind filter.",
        "notes": "Metallic noise and pressure that will not go past 6 bar: pump. Hum and zero pressure: motor or capacitor ID-4019. "
                 "A pump worn by hard water shows at the coupling: black dust.",
    },
    "ID-4025": {"mounting": "On the pump delivery line. Unscrew, replace, set to 12 bar.",
                "notes": "Constant discharge while brewing: expansion valve. Discharge with the machine idle: check valve ID-4030 or fill valve ID-4040. Tell them apart by asking WHEN it drips."},
    "ID-4040": {"mounting": "On the water inlet, after the filter. Two fittings and the coil. Respect the flow direction.",
                "notes": "Clicks but does not fill: internal mesh blocked by scale, cleanable. No click: coil (EL-3085) or board. Fills all the time: probe CA-1230 or valve stuck open."},
    "ID-4050": {"mounting": "On each group, between solenoid and heat exchanger. Mind the arrow; the sensor slides off without opening the circuit.",
                "notes": "Doses changing from one day to the next: dirty turbine (ID-4051), cleanable. Endless dose or flowmeter alarm: sensor ID-4052. On first-batch Marea 2 Plus (EL-3011) the alarm was a board bug, not the flowmeter."},
    "VA-5015": {"mounting": "Close the tap, unscrew the knob and the gland, pull the stem, replace the two seals and the o-ring, refit without overtightening the gland.",
                "notes": "The customer does it alone in 10 minutes. If it still drips afterwards, the stem is scored (VA-5016)."},
    "VA-5025": {"mounting": "Unscrews by hand from the wand. Clean the thread.",
                "notes": "Weak steam with normal boiler pressure: almost always a tip blocked with milk. Have them unscrew it, 30 minutes in hot water with a tablet, a pin through the holes."},
    "EL-3010": {
        "mounting": "No longer applicable: see EL-3012.",
        "notes": "OUT OF PRODUCTION since March 2025. Superseded by EL-3012 (v2 rev.B), which fits 2024 Marea 2 and Giglio 1 ONLY with the "
                 "adapter harness EL-3036. If the customer reads EL-3010 from an old invoice, order EL-3012 + EL-3036 and plan service support "
                 "for fitting and dose reprogramming.",
    },
    "EL-3011": {"mounting": "No longer applicable: see EL-3012.",
                "notes": "First batch of v2 boards (Marea 2 Plus and Giglio 1 Plus, January-March 2025): flowmeter counting bug giving dose alarms. Replaced under warranty with EL-3012, no adapter needed."},
    "EL-3012": {
        "mounting": "With service support. Power off, photograph the connectors, replace the board, on 2024 machines fit EL-3036 in between. "
                    "At power-up reprogram the 4 doses per group.",
        "notes": "Current board for the whole Marea 2 / Marea 2 Plus / Giglio 1 / Giglio 1 Plus family. Replaces EL-3010 (needs EL-3036) and EL-3011 (direct). Does not fit the Marea 2 Evo (EL-3013).",
    },
    "EL-3030": {"mounting": "Slides out of the front after removing the bezel; unplug the ribbon cable EL-3035.",
                "notes": "One dead button with its LED on: membrane. All buttons dead: ribbon cable or board. The customer does it alone."},
    "EL-3036": {"mounting": "Goes between the machine's 10-pin connector (2024 build) and board EL-3012.",
                "notes": "Mandatory with EL-3012 on 2024 Marea 2 and Giglio 1. Without it the board powers up but does not read the flowmeter. Always ship together."},
    "EL-3085": {"mounting": "Slides off the valve body after removing the top nut. Respect the voltage.",
                "notes": "Coil warm to the touch and no click: burnt. First cause of 'one group does not brew'. The customer replaces it alone."},
    "MC-7010": {
        "mounting": "Empty the hopper, open the collar until the upper burr carrier comes off, undo the 3 screws per burr, clean the seats, "
                    "fit the new burrs, zero the collar at contact and reopen half a turn.",
        "notes": "Life 600-800 kg of coffee. Signs: slow grinding, burnt-tasting coffee, warm grounds. The customer changes them alone with the sheet. Same on Monda 65 and Monda 65 Digit.",
    },
    "MC-7062": {"mounting": "Behind the fork, two screws. Adjust the leaf so it clicks with the portafilter inserted.",
                "notes": "The Digit does not start and does not click when the portafilter goes in: microswitch. First check that the fork is not loose."},
    "CR-6052": {"mounting": "One tablet in the blind filter, 5 cycles of 10 seconds per group, then 5 rinse cycles.",
                "notes": "The consumable to suggest in almost every call about the group. One a day per group."},
}
