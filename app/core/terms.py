"""Sereni's commercial terms (fictional, like the rest of the company): what a service call, a technician's visit and
shipping cost, and what the warranty covers. Prices come from the ERP's price list (service_prices in sereni.db); the
assistant quotes these and never invents a price."""
import sqlite3
from pathlib import Path

WARRANTY_MONTHS = 24


def _price_list() -> dict[str, float]:
    try:
        con = sqlite3.connect(Path(__file__).resolve().parents[2] / "data" / "sereni.db")
        try:
            return dict(con.execute("SELECT code, price_eur FROM service_prices"))
        finally:
            con.close()
    except sqlite3.Error:
        return {}


PRICES = _price_list()
SERVICE_CALL_EUR = PRICES.get("SERVICE-CALL", 35.0)      # remote video call with the service desk, up to 30 minutes
TECH_VISIT_EUR = PRICES.get("TECH-VISIT", 80.0)          # technician's visit, fixed call-out
SHIPPING_EU_EUR = PRICES.get("SHIP-EU", 9.90)            # express courier from Florence or the Rotterdam hub
SHIPPING_WORLD_EUR = PRICES.get("SHIP-WORLD", 29.00)
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
        eur = TECH_VISIT_EUR
        what_en, what_it = "technician's visit (fixed call-out)", "uscita del tecnico (prezzo fisso)"
    else:
        return None
    return {"what_en": what_en, "what_it": what_it, "list_eur": eur,
            "customer_pays_eur": 0.0 if in_warranty else eur if in_warranty is False else None}
