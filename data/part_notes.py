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
