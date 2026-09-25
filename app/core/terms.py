"""Sereni's commercial terms (fictional, like the rest of the company): what a service call, a technician's visit and
shipping cost, and what the warranty covers. The assistant quotes these; it never invents a price."""

WARRANTY_MONTHS = 24

SERVICE_CALL_EUR = 35.0          # remote video call with the service desk, up to 30 minutes
TECH_CALLOUT_EUR = 90.0          # technician's visit: call-out
TECH_HOURLY_EUR = 60.0           # ... plus labour per hour
TECH_ESTIMATED_HOURS = 1.0

SHIPPING_EU_EUR = 9.90           # express courier from Florence or the Rotterdam hub
SHIPPING_WORLD_EUR = 29.00
EU = {"IT", "DE", "AT", "ES", "NL", "FR", "PT", "BE", "LU", "IE", "DK", "SE", "FI", "PL", "CZ", "SK", "SI", "HR", "HU",
      "RO", "BG", "GR", "CY", "MT", "EE", "LV", "LT"}

EURO_AREA = {"IT", "DE", "AT", "ES", "NL", "FR", "PT", "BE", "LU", "IE", "FI", "SK", "SI", "HR", "GR", "CY", "MT", "EE",
             "LV", "LT"}

WARRANTY_TERMS = {
    "en": [f"{WARRANTY_MONTHS} months from installation: repair parts, service calls, technician visits and shipping are free.",
           "Missed cleaning or backflushing does not void the warranty. Not covered: limescale damage without a water "
           "softener, drops and misuse, repairs by non-Sereni technicians.",
           "Consumables (cleaning tablets, brushes, filter cartridges) are always charged."],
    "it": [f"{WARRANTY_MONTHS} mesi dall'installazione: ricambi della riparazione, chiamate del service, visite del tecnico e "
           "spedizione gratuiti.",
           "Le pulizie saltate non fanno decadere la garanzia. Esclusi: danni da calcare senza addolcitore, cadute e uso "
           "improprio, riparazioni di tecnici non Sereni.",
           "Il materiale di consumo (pastiglie, spazzolini, cartucce filtro) si paga sempre."],
}


def shipping_eur(country: str | None, in_warranty: bool | None) -> float | None:
    """Shipping of the parts: free under warranty, otherwise by destination; unknown without the machine record."""
    if in_warranty:
        return 0.0
    if not country:
        return None
    return SHIPPING_EU_EUR if country.upper() in EU else SHIPPING_WORLD_EUR


def labour(kind: str, in_warranty: bool | None, fits_alone: bool = False) -> dict | None:
    """The service part of an outcome, with its price for this customer."""
    if kind == "part_with_support" and not fits_alone:
        what_en, what_it, eur = "service video call (up to 30 min)", "videochiamata con il service (fino a 30 min)", SERVICE_CALL_EUR
    elif kind == "technician":
        eur = TECH_CALLOUT_EUR + TECH_HOURLY_EUR * TECH_ESTIMATED_HOURS
        what_en = f"technician's visit (€{TECH_CALLOUT_EUR:.0f} call-out + €{TECH_HOURLY_EUR:.0f}/h, about {TECH_ESTIMATED_HOURS:.0f} h)"
        what_it = f"visita del tecnico (€{TECH_CALLOUT_EUR:.0f} uscita + €{TECH_HOURLY_EUR:.0f}/h, circa {TECH_ESTIMATED_HOURS:.0f} h)"
    else:
        return None
    return {"what_en": what_en, "what_it": what_it, "list_eur": eur,
            "customer_pays_eur": 0.0 if in_warranty else eur if in_warranty is False else None}
