"""Cardex on the AssemblyAI Voice Agent API: the hosted agent listens, thinks and talks; our server is its
memory and its rulebook. Every fact the agent may say comes from a tool that runs here, against the same
procedures, catalogue, installed base and calendar as the operator mode. The agent never diagnoses: it asks what
the current step asks, reports the customer's answer with answer_step, and the procedure decides.

The browser holds the two sockets (the agent's and ours) and relays tool calls and transcripts between them,
so nothing needs a public URL: the tools are client-side function tools executed by this server.
"""
from __future__ import annotations

import json
import os
import re

import httpx

from ..agent.dialog import classify_branch, digits_in, email_in, for_customer, numbers_in, polarity, said_email

AGENTS_URL = "https://agents.assemblyai.com/v1"
AGENT_NAME = "Cardex Assistant"
VOICE_ID = os.getenv("CARDEX_VOICE", "alba")
# one native voice per language the API can speak (input understands 18 languages on its own)
LANGUAGES = {"en": ("English", "alba"), "it": ("Italian", "giovanni"), "es": ("Spanish", "lola"),
             "de": ("German", "juergen"), "fr": ("French", "estelle"), "pt": ("Portuguese", "rafael")}
GREETINGS = {"en": "Sereni service, good morning. Which machine are you calling about, and what is it doing?",
             "it": "Servizio assistenza Sereni, buongiorno. Per quale macchina chiama, e cosa fa?",
             "es": "Servicio técnico Sereni, buenos días. ¿Por qué máquina llama, y qué le pasa?",
             "de": "Sereni Kundendienst, guten Tag. Um welche Maschine geht es, und was macht sie?",
             "fr": "Service Sereni, bonjour. Pour quelle machine appelez-vous, et que fait-elle ?",
             "pt": "Assistência Sereni, bom dia. Sobre qual máquina liga, e o que ela está a fazer?"}

SYSTEM_PROMPT = """You are the first-line service assistant of Sereni, an espresso machine maker in Florence, Italy. You are on the phone with a customer, usually a barista abroad, and you speak simple, clear English.

HOW YOU WORK
1. You do not diagnose. The troubleshooting procedure decides. The moment the customer has described what the machine is doing, call find_procedure with their words, before saying anything else. Then ask what the current step asks, in your own natural words, one question at a time. The ONLY questions you may ask about the fault are the ones the steps give you: never add checks of your own ("is the gasket dirty?").
2. After the customer answers a step (or reports what happened after doing what you asked), call answer_step with the number of the option that matches their words. If their words do not answer the question, do not choose for them: ask the step's question again, plainly. Never call answer_step to guess.
3c. If find_procedure returns candidates, read them to the customer and call start_procedure ONLY after the customer has said which one applies. Never pick one yourself.
3d. After any side topic (the serial, a question, a part), continue with the step given in "resume" of the tool result. Never re-ask a question listed there as already answered, and never make up a question of your own.
3b. The customer cannot interrupt you while you talk: keep every reply to one or two short sentences, and never repeat a question the customer has already answered.
3. When a step asks the customer to do something (press, unscrew, clean, backflush), explain it simply, wait for them to do it and tell you the result, then call answer_step.
4. Order of things: as soon as the fault is described, call find_procedure and ask its first question. Right after the customer answers that first question, ask for the serial number (it is on the plate at the back) and call identify_machine with the digits and the model words the customer used: it tells you the machine, whether it is under warranty and who pays. Then continue with the steps.
5. Say prices, delivery times, part codes, warranty, totals and dates ONLY when they come from a tool result in this conversation. Never invent a number, never name a part the tools did not return, never explain what broke beyond what the step or the outcome says. Always use the "spoken" forms given in the results for codes and prices (for example "C A twelve seventy, twelve euros sixty"), every time you say a code.
6. THE CUSTOMER MAY ASK ANYTHING AT ANY MOMENT, in any order (warranty before the serial, cost before the outcome, the appointment in the middle of a step). Never refuse, postpone or pass to the operator a question that get_call_status can answer: call it, answer in one or two sentences, then go back to the step where you were. If the answer depends on something missing (no serial yet, no outcome yet), say what is missing and ask for it. Customer questions: answer from tool results when you can. Money: always say what the CUSTOMER pays (customer_pays_spoken, customer_pays_total_spoken, labour), never the list price as if it were a cost. Under warranty the repair's parts and the service are free; consumables such as cleaning tablets are always charged, and if asked, say so plainly ("the tablets are consumables, they are not covered"). What the warranty covers or excludes (for example whether missed cleaning voids it): answer from who_pays.terms of get_call_status. Shipping, the service call and the technician have fixed prices in the outcome (shipping, labour): quote them, never guess. The outcome also gives delivery days and whether a service call or a technician is needed; use them. How to pay: never take payment on the phone and never invent links, card payments or bank details; say what the outcome's payment field says (a colleague emails the quote and payment instructions, the parts ship when the payment is confirmed). Call note_for_operator only for things no tool covers (discounts, invoices, complaints), say the operator will follow up, then return to the procedure. Warranty, prices, delivery and appointments are NEVER operator questions.
7. At the outcome, explain what happens next (parts shipped FROM our warehouse to the customer, second call with service, technician's visit), who pays, and propose the first free slot from the result. Call book_slot only when the customer has accepted THAT slot; never book or move an appointment on your own. If they want to choose or the slot does not suit them, read three or four free slots on different days and let them pick. The outcome's parts all ship together: never ask the customer to choose between them. When the customer agrees to receive the parts, call confirm_parts with their codes: without it nothing is ordered. If the customer pays anything, if the customer pays something, the quote and the payment instructions go by email: read out the email on file (machine.email_on_file) and ask if it is still right. If they pay nothing, never mention a quote or a payment: only confirm the email on file for the order confirmation. Only if it is wrong or missing, ask for a new one, let the customer spell it to the end without interrupting, call set_email, read back its result and ask if it is right. Never take payment on the call. Prices are in euros: if asked about another currency, say we invoice in euros and their bank or card converts at the day's rate.
7b. Tell the outcome in short turns, never all at once: the outcome result gives say_first (what failed, what replaces it, what it costs, warranty or not): say only that and wait for the customer. Then one piece per turn: delivery, the service call or visit (ask about it yourself if they have not), the email. Two or three sentences per turn. Do not propose a slot before the customer has agreed to the service call. If the outcome needs a service call or a technician and the customer wants to fit the part alone, say once that this part must be fitted with our service (safety, and the repair's warranty); if they still decline, call note_for_operator ("customer declines service support").
8. Say numbers as words, the natural way: "two hundred thirty volts", "one point two bar", never digit by digit (except serial numbers when you repeat them back). Keep every reply to one or two short sentences. Warm and professional, never chatty. Repeat numbers back to confirm them.
10. If a tool result says "stale" or "error", call answer_step again right away with the step_id given in that result and the option matching the customer's words. Never guess the outcome yourself and never use find_part to work out which part is needed: only the procedure's outcome names the parts. find_part is for parts the customer asks about by code or by name.
9. When there is nothing else, thank them, say goodbye, and call end_call.
Everything you do is recorded for a human operator, who approves orders and bookings afterwards; say so if asked."""


TOOLS: list[dict] = [
    {"name": "identify_machine",
     "description": "Call as soon as the customer names the machine model and/or reads the serial number. Returns the machine on file: model, edition, warranty status, who pays for a technician, previous orders. Pass the customer's exact words for the model; never guess.",
     "parameters": {"type": "object", "properties": {
         "model_text": {"type": "string", "description": "The customer's words about the model, e.g. 'the Marea 2 Plus, the vanilla one'"},
         "serial": {"type": "string", "description": "Serial number as read by the customer, digits possibly separated by spaces, e.g. '0 4 7 2 1 9' or '047219'", "pattern": "^[0-9A-Za-z][0-9A-Za-z -]{3,14}$"},
        "customer_words": {"type": "string", "description": "What the customer said about themselves: business name and city, e.g. 'Kaffeehaus Nord in Berlin'. Used to find the machine when the serial is not understood."}},
         "required": []}, "execution_mode": "hold"},
    {"name": "find_procedure",
     "description": "Call when the customer has described what the machine is doing wrong, in their own words. The machine (model or serial) must be known first: if the result says need_machine, identify the machine and call again. Opens the matching troubleshooting procedure and returns its first step. If it returns candidates instead, ask the customer which one applies and call start_procedure. When in doubt, call it: a wasted call is fine.",
     "parameters": {"type": "object", "properties": {"description": {"type": "string", "description": "What the customer said about the fault, verbatim"}},
                    "required": ["description"]}, "execution_mode": "hold"},
    {"name": "start_procedure",
     "description": "Start one of the candidate procedures returned by find_procedure, after the customer said which one applies.",
     "parameters": {"type": "object", "properties": {"symptom_id": {"type": "string"}}, "required": ["symptom_id"]}, "execution_mode": "hold"},
    {"name": "answer_step",
     "description": "Call once, right after the customer answered the current step's question, or reported the result of what you asked them to do. Pass the step_id you are answering and the number of the option that matches their answer. Returns the next step, or the outcome with parts, prices, delivery, warranty, total cost and free service slots. Never call it twice for the same step.",
     "parameters": {"type": "object", "properties": {
         "step_id": {"type": "string", "description": "The step_id from the step you asked (from the last tool result)"},
         "option_number": {"type": "integer", "minimum": 1, "maximum": 6, "description": "The option that matches the customer's answer"},
         "customer_words": {"type": "string", "description": "What the customer said, verbatim"}},
         "required": ["step_id", "option_number", "customer_words"]}, "execution_mode": "hold"},
    {"name": "find_part",
     "description": "Call when the customer names a spare part by code (like GE-2140 or EL-3010) or by description (group gasket, cleaning tablets, water filter). Returns the parts on file with price, stock, delivery days, compatibility and whether the customer can fit them. Quote prices and delivery only from this result.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "The code or description as the customer said it"}},
                    "required": ["query"]}, "execution_mode": "hold"},
    {"name": "book_slot",
     "description": "Call when the customer accepts one of the free slots you proposed for the service call or the technician's visit. Pass the slot id exactly as given in the outcome.",
     "parameters": {"type": "object", "properties": {"slot_id": {"type": "string", "pattern": "^[A-Z]+:[0-9]+:[0-9]+$"}},
                    "required": ["slot_id"]}, "execution_mode": "hold"},
    {"name": "confirm_parts",
     "description": "Call when the customer agrees to receive the parts named in the outcome (or a part from find_part). Records the order for the operator, who approves it before shipping. Never say the parts are on their way without calling this.",
     "parameters": {"type": "object", "properties": {"codes": {"type": "array", "items": {"type": "string"}, "description": "The part codes the customer accepted, e.g. [\"GE-2140\", \"GE-2210\"]"},
                                                     "email": {"type": "string", "description": "The customer's email for the quote and payment instructions, exactly as spelled, e.g. dave@espressocorner.com. Needed whenever the customer pays something."}},
                    "required": ["codes"]}, "execution_mode": "hold"},
    {"name": "set_email",
     "description": "Call only when the customer gives a NEW email address for the quote (the one on file is wrong or missing). Let them spell it to the end before calling; then read back what the tool returns and ask if it is right.",
     "parameters": {"type": "object", "properties": {"email": {"type": "string", "description": "The customer's email address, complete, as spelled: name, at sign, domain.", "examples": ["klaus.becker@gmail.com", "info@barsol.es"]}},
                    "required": ["email"]}, "execution_mode": "hold"},
    {"name": "get_call_status",
     "description": "Call whenever the customer asks something that is not the answer to the current step, at ANY moment: warranty, who pays (parts, labour, consumables), total cost, delivery time, who fits the part, what has been ordered, the appointment, what happens next. Returns everything known on this call. Answer from it, then return to where you were. When in doubt, call it.",
     "parameters": {"type": "object", "properties": {"question": {"type": "string", "description": "The customer's question, verbatim"}},
                    "required": ["question"]}, "execution_mode": "hold"},
    {"name": "note_for_operator",
     "description": "Call when the customer asks for something you cannot answer from tool results (discounts, invoices, anything outside the procedure) or wants something done by a person. Tell the customer the operator will follow up.",
     "parameters": {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]}, "execution_mode": "interactive"},
    {"name": "end_call",
     "description": "Call right after you have said goodbye, when the customer has nothing else.",
     "parameters": {"type": "object", "properties": {}, "required": []}, "execution_mode": "interactive"},
]

def session_config(keyterms: list[str], lang: str = "en", resume: bool = False) -> dict:
    """What the browser sends in session.update: the whole agent inline (a stored agent_id cannot be combined
    with per-session tools, and our tools are client-side functions executed by this server)."""
    cfg = agent_config(keyterms, lang)
    out = {"system_prompt": cfg["system_prompt"], "greeting": cfg["greeting"], "input": cfg["input"],
           "output": cfg["output"], "tools": [{"type": "function", **t} for t in TOOLS]}   # "function" = executed by the client
    if resume:
        del out["greeting"]                     # a language handover continues the call: no second greeting
    return out


_agent_id: str | None = None
_GOODBYE = re.compile(r"\b(good ?bye|bye|arrivederci|arrivederla|buona giornata|buona serata|adi[oó]s|hasta luego|"
                      r"auf wieder(h[oö]ren|sehen)|tsch[uü]ss|au revoir|bonne journ[ée]e|adeus|tchau|at[ée] logo)\b", re.I)


TRANSCRIPTION_PROMPT = ("A phone call to the service desk of Sereni, an Italian maker of professional espresso machines "
                        "(Marea, Giglio, Onda, Monda). People talk about boilers, heating elements, gaskets, solenoid valves, "
                        "portafilters, steam wands, voltages, part codes of two letters and four digits (CA-1181, GE-2160) and "
                        "serial numbers read digit by digit. Customers ask about the warranty or guarantee, prices, "
                        "delivery and appointments.")


def agent_config(keyterms: list[str], lang: str = "en") -> dict:
    lang = lang if lang in LANGUAGES else "en"
    name, voice = LANGUAGES[lang]
    prompt = SYSTEM_PROMPT + (f"\n\nLANGUAGE: speak {name} with the customer. The tools answer in English: translate "
                              f"what they say into natural {name}; keep part codes as they are and say prices in words. "
                              "If the customer speaks or asks for Italian, Spanish, German, French or Portuguese, answer in "
                              "that language: never say you only speak one language.")
    return {"name": AGENT_NAME, "system_prompt": prompt, "greeting": GREETINGS[lang],
            "voice": {"voice_id": voice},
            "input": {"format": {"encoding": "audio/pcm", "sample_rate": 24000}, "keyterms": keyterms[:100],
                      "language_codes": list(LANGUAGES), "transcription_prompt": TRANSCRIPTION_PROMPT,
                      # No turn_detection: a fixed one-second silence cut the customer's sentences ("spray all over"
                      # arrived as "Rice all over." | "pray, man."). The default reads the meaning of what was said
                      # and adapts to the speaker's pace (AssemblyAI docs: leave it on default). The browser still
                      # keeps the mic closed while the agent's voice plays (half duplex).
                      },
            "output": {"voice": voice, "format": {"encoding": "audio/pcm", "sample_rate": 24000}, "volume": 100},
            "tools": [], "llm": []}                        # managed model; tools are declared per session by the browser


async def ensure_agent(api_key: str, keyterms: list[str]) -> str:
    """The stored agent named 'Cardex Assistant', created once and updated with the current prompt."""
    global _agent_id
    if _agent_id:
        return _agent_id
    h = {"Authorization": api_key, "Content-Type": "application/json"}
    cfg = agent_config(keyterms)
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{AGENTS_URL}/agents", headers=h)
        found = None
        if r.status_code == 200:
            body = r.json()
            items = body if isinstance(body, list) else body.get("agents") or body.get("items") or body.get("data") or []
            found = next((a["id"] for a in items if a.get("name") == AGENT_NAME), None)
        if found:
            u = await c.put(f"{AGENTS_URL}/agents/{found}", headers=h, json=cfg)
            u.raise_for_status()
            _agent_id = found
        else:
            p = await c.post(f"{AGENTS_URL}/agents", headers=h, json=cfg)
            p.raise_for_status()
            _agent_id = p.json()["id"]
    return _agent_id


async def session_token(api_key: str, seconds: int = 600) -> str:
    """A single-use token for one browser session (the API caps it at 600 s; the session itself lives longer)."""
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{AGENTS_URL}/token", headers={"Authorization": f"Bearer {api_key}"}, params={"expires_in_seconds": seconds})
        r.raise_for_status()
        return r.json()["token"]


# ------------------------------------------------------------------ spoken forms (the voice reads "CA-1270" badly)
_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
         "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def num_words(n: int) -> str:
    """0-999 in words: 12 -> twelve, 96 -> ninety-six, 240 -> two hundred forty."""
    n = int(n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("-" + _ONES[n % 10] if n % 10 else "")
    return _ONES[n // 100] + " hundred" + (" " + num_words(n % 100) if n % 100 else "")


def spoken_code(code: str) -> str:
    """'CA-1270' -> 'C A twelve seventy'; 'GE-2140' -> 'G E twenty-one forty'."""
    m = re.fullmatch(r"([A-Z]{2})-(\d{4})", code or "")
    if not m:
        return code
    letters, digits = m.groups()
    return " ".join(letters) + " " + num_words(int(digits[:2])) + " " + ("hundred" if digits[2:] == "00" else num_words(int(digits[2:])) if digits[2] != "0" else "oh " + _ONES[int(digits[3])])


def spoken_price(eur: float | None) -> str:
    """12.6 -> 'twelve euros sixty'; 96.0 -> 'ninety-six euros'."""
    if eur is None:
        return "price to be confirmed"
    whole, cents = int(eur), int(round((eur - int(eur)) * 100))
    return num_words(whole) + " euros" + (" " + num_words(cents) if cents else "")


# ------------------------------------------------------------------ the tools, run against a CallSession
def _known_from_record(s) -> int | None:
    """The option of the current step that the serial's record already answers (the voltage on the rating plate),
    or None."""
    d, m = s.diagnosis, s.machine
    if not (d and d.current and m and m.get("voltage")) or "volt" not in d.step["text_en"].lower():
        return None
    from ..session import SEMANTIC, VOCAB
    said = f"{VOCAB.model_names.get(m['model_id'], '')} {m['voltage'].replace('V', '')} volts"
    j, _ = classify_branch(said, d.step["branches"], SEMANTIC.similarities)
    return j


def _step_view(s) -> dict:
    d = s.diagnosis
    st = d.step
    text = for_customer(st["text_en"])
    out = {"symptom": d.symptom["symptom_en"], "step_id": st["id"], "kind": st["kind"],
           "ask_the_customer": text if st["kind"] == "ask" else text + " Then ask what happened.",
           "options": [{"number": i + 1, "label": b["label_en"]} for i, b in enumerate(st["branches"])],
           "note": st.get("note_en")}
    j = _known_from_record(s)
    if j is not None:
        # 26/9: "110, but don't you know from the serial number?"
        out["known_from_record"] = {"option_number": j + 1, "label": st["branches"][j]["label_en"]}
        out["ask_the_customer"] = (f"Our records for this serial say {s.machine['voltage'].replace('V', ' volts')}: "
                                   "just ask the customer to confirm it, do not ask as if you did not know.")
    return out


def _already_answered(s, words: str) -> dict:
    """When a procedure opens, the customer's own description may already answer its first question ("water comes from
    the portafilter rim" answers "rim or group body?"). Checked with the same classifier as answer_step."""
    d = s.diagnosis
    if not (d and d.current and words):
        return {}
    from ..session import SEMANTIC
    st = d.step
    j, conf = classify_branch(words, st["branches"], SEMANTIC.similarities, question=st["text_en"] if st["kind"] == "ask" else "")
    if j is None:
        return {}
    return {"already_answered": {"option_number": j + 1, "label": st["branches"][j]["label_en"], "customer_words": words},
            "hint": "the customer's description already answers this question: do not ask it again, call answer_step now "
                    "with this step_id, this option_number and these words (or ask a short confirmation if unsure)."}


def warranty_rules(s) -> dict:
    """Who pays what on this machine, in words the agent can say."""
    from ..core.terms import WARRANTY_TERMS
    return {**_warranty_rules(s), "terms": WARRANTY_TERMS["en"]}


def _warranty_rules(s) -> dict:
    m = s.machine
    if not m:
        return {"known": False, "say": "the warranty depends on the machine: ask for the serial number on the plate at the back"}
    if m.get("in_warranty"):
        return {"known": True, "status": f"under warranty until {m['warranty_until']}",
                "repair_parts": "free: the parts of the repair are covered", "labour_and_service_call": "free",
                "consumables": "always charged (cleaning tablets, brushes): not covered by any warranty"}
    return {"known": True, "status": f"out of warranty since {m['warranty_until']}",
            "repair_parts": "charged at list price", "labour_and_service_call": "charged: a quote follows",
            "consumables": "charged"}


def call_status(s) -> dict:
    """Everything known on the call, for any question in any order."""
    from ..session import VOCAB
    d = s.diagnosis
    if d and d.outcome:
        procedure = {"state": "outcome", **_outcome_view(s)}
    elif d and d.current:
        procedure = {"state": "in_progress", **_step_view(s)}
    else:
        procedure = {"state": "not_started", "hint": "the fault has not been described yet"}
    parts = []
    for c in s.cards.values():
        ch = s.charge_for(c["code"])
        parts.append({"code": c["code"], "spoken": spoken_code(c["code"]), "description": c.get("description_en") or c["description"],
                      "status": {"confirmed": "ordered", "proposed": "not ordered yet", "dismissed": "declined"}[c["status"]],
                      "fits_this_machine": c.get("compatible", True),
                      "customer_pays_spoken": "free, covered by the warranty" if ch["covered_by_warranty"] else spoken_price(ch["customer_pays_eur"]),
                      "why": ch["why"]})
    ordered = [p for p in s.cards.values() if p["status"] == "confirmed"]
    total = round(sum(s.charge_for(p["code"])["customer_pays_eur"] or 0 for p in ordered), 2)
    return {"machine": {"model": VOCAB.model_names.get(s.model_id) or s.family or "unknown", **_machine_view(s)},
            "who_pays": warranty_rules(s), "procedure": procedure, "parts": parts,
            "ordered_total_customer_pays": "nothing" if total == 0 else spoken_price(total),
            "appointment": s._slot_view(s.booking)["label_en"] + " with " + s.booking["technician"] if s.booking else None,
            "notes_for_operator": s.notes}


def _machine_view(s) -> dict:
    m = s.machine
    if not m:
        return {"serial": s.serial, "on_file": False, "warranty": "unknown", "hint": "ask for the serial number on the plate at the back"}
    return {"serial": m["serial"], "on_file": True, "model": m["model_id"], "edition": m.get("edition"), "built": m["built"],
            "voltage": m["voltage"], "customer": m["customer"], "city": m["city"], "country": m["country"],
            "warranty": "under warranty until " + m["warranty_until"] if m.get("in_warranty") else "out of warranty since " + m["warranty_until"],
            "who_pays_technician": "Sereni" if m.get("in_warranty") else "the customer",
            "notes": m.get("notes"), "matched_exactly": m.get("matched_exactly", True),
            "email_on_file": m.get("contact_email"),
            "previous_orders": [f"{o['ordered_on']} {o['code']} x{o['qty']}" for o in m.get("orders", [])[:4]]}


def _say_first(s, n: dict) -> str:
    """The first thing to tell at the outcome, and only that: what failed, what replaces it, what the customer pays
    for it, warranty or not. Delivery, the service call and the email come after the customer has answered."""
    d = s.diagnosis
    if n["kind"] == "remote":
        return "Good news: the problem is solved, nothing needs to be replaced."
    parts = " and ".join(f"{(p.get('description_en') or p['description']).split(',')[0].lower()} ({spoken_code(p['code'])})"
                         for p in n["parts"])
    what = f"This is the {d.symptom['symptom_en'].split(',')[0].lower()} problem: we need to replace the {parts}." if parts \
        else "This needs a technician's visit."
    c = n.get("costs") or {}
    if n["warranty"] is True:
        money = "Your machine is under warranty, so this costs you nothing."
    elif n["warranty"] is False:
        money = (f"Your machine is out of warranty: the parts cost {spoken_price(c.get('parts_eur') or 0)}."
                 if parts else "Your machine is out of warranty, so the visit is charged.")
    else:
        money = "To tell you who pays, I need the serial number on the plate at the back."
    return f"{what} {money}"


def _outcome_view(s) -> dict:
    n = s._next_step()
    kind = n["kind"]
    out = {"outcome": kind,
           "say_first": _say_first(s, n),
           "how_to_tell_it": ("Say ONLY say_first now, in your own words, then stop and let the customer answer. Then, one "
                              "piece per turn: delivery; then the service call or the technician visit if the outcome needs "
                              "one (ask about it yourself if the customer has not); then, if they pay something, the email "
                              "for the quote. Everything else below is for their questions; never read it all out."),
           "meaning": {"remote": "fixed remotely, nothing to ship",
                       "part_diy": "ship the parts, the customer fits them with the sheet",
                       "part_with_support": "ship the parts and book a second call with service to fit them",
                       "technician": "a technician's visit is needed"}[kind],
           "warranty": {True: "under warranty: no charge", False: "out of warranty: parts and labour are charged, a quote follows",
                        None: "warranty unknown: ask the serial number"}[n["warranty"]],
           "parts": [{"code": p["code"], "spoken": spoken_code(p["code"]),
                      "list_price_spoken": spoken_price(p["price_eur"]),
                      "customer_pays_spoken": "free, covered by the warranty" if p["covered_by_warranty"] else spoken_price(p["customer_pays_eur"]),
                      "covered_by_warranty": p["covered_by_warranty"], "customer_pays_eur": p["customer_pays_eur"],
                      "description": p.get("description_en") or p["description"], "list_price_eur": p["price_eur"],
                      "delivery": (p["delivery"][0]["from"].replace("FI-01 ", "").replace("NL-01 ", "") + ", " + p["delivery"][0]["days"] + " working days") if p["delivery"] else "unknown",
                      "fitting": {"diy": "the customer fits it", "support": "fitted on a service call"}.get(p["handling"], p["handling"])}
                     for p in n["parts"]],
           "customer_pays_total_eur": round(sum(p["customer_pays_eur"] or 0 for p in n["parts"]), 2),
           "customer_pays_total_spoken": (lambda t: "nothing, all covered by the warranty" if t == 0 else spoken_price(t))(
               round(sum(p["customer_pays_eur"] or 0 for p in n["parts"]), 2)),
           "labour": ("free, covered by the warranty" if n["warranty"] is True else "charged, a quote follows" if n["warranty"] is False
                      else "depends on the warranty: ask the serial number")}
    c = n.get("costs")
    if c:
        out["shipping"] = ("free" if c["shipping_eur"] == 0 else spoken_price(c["shipping_eur"]) if c["shipping_eur"] is not None
                           else "depends on the destination: ask the serial number")
        if c["labour"]:
            lp = c["labour"]["customer_pays_eur"]
            out["labour"] = c["labour"]["what_en"] + ": " + ("free, covered by the warranty" if lp == 0 else
                                                               spoken_price(lp) if lp else "depends on the warranty: ask the serial number")
        if c["total_eur"] is not None:
            out["customer_pays_total_with_shipping_and_service_spoken"] = ("nothing" if c["total_eur"] == 0
                                                                            else spoken_price(c["total_eur"]))
    if n.get("payment"):
        out["payment"] = n["payment"]["say_en"] or n["payment"]["text"]
        out["ship_to"] = n["ship_to"]
    if n.get("fits_alone"):
        out["customer_fits_alone"] = "the customer declined the service call; they can call service back for help"
    b = n.get("booking")
    if b:
        out["booking"] = {"kind": "technician's visit" if b["kind"] == "onsite" else "second call with service (video call)",
                          "booked": b["booked"]["label_en"] if b["booked"] else None,
                          "need_serial": b["need_serial"], "no_partner": b["no_partner"],
                          "free_slots": [{"slot_id": x["id"], "when": x["label_en"], "with": x["technician"]} for x in b["slots"]]}
    return out


def _card_view(c: dict, charge: dict | None = None) -> dict:
    d = c["delivery"][0] if c.get("delivery") else None
    charge = charge or {"covered_by_warranty": False, "customer_pays_eur": c["price_eur"], "why": "unknown"}
    return {"code": c["code"], "spoken": spoken_code(c["code"]), "list_price_spoken": spoken_price(c["price_eur"]),
            "customer_pays_spoken": "free, covered by the warranty" if charge["covered_by_warranty"] else spoken_price(charge["customer_pays_eur"]),
            "covered_by_warranty": charge["covered_by_warranty"], "why": charge["why"],
            "description": c.get("description_en") or c["description"], "list_price_eur": c["price_eur"],
            "delivery": (d["from"].replace("FI-01 ", "").replace("NL-01 ", "") + ", " + d["days"] + " working days") if d else "unknown",
            "fits_this_machine": c["compatible"], "superseded_by": c.get("superseded_by"), "requires": c.get("requires"),
            "fitting": {"diy": "the customer fits it", "support": "fitted on a service call"}.get(c.get("handling"), c.get("handling")),
            "note": c.get("note_en") or c.get("note")}


async def run_tool(s, name: str, args: dict) -> dict:
    """Executes one tool call from the voice agent on the call session. Returns what the agent may say, plus where the
    procedure stands, so a side question or the serial never makes the agent lose the thread."""
    result = await _run_tool(s, name, args)
    d = s.diagnosis
    if name in ("identify_machine", "get_call_status", "find_part", "note_for_operator") and d and d.current:
        result["resume"] = {"step_id": d.current, "ask_next": _step_view(s)["ask_the_customer"],
                            "already_answered": [f"{h['text_en']} -> {h['answer_en']}" for h in d.history],
                            "hint": "go back to this step now; do not ask again what is already answered"}
    return result


async def _run_tool(s, name: str, args: dict) -> dict:
    args = args or {}
    if name == "identify_machine":
        if args.get("model_text"):
            await s.apply_model_words(args["model_text"])
        serial = digits_in(args.get("serial") or "") or re.sub(r"[^0-9A-Za-z]", "", args.get("serial") or "")
        if len(serial) >= 5:
            await s._set_serial(serial.upper())
        if s.machine:
            await s.adopt_machine_record()          # "Giglio 1" said, Giglio 1 Plus on file: the file wins
        from ..session import CATALOG, VOCAB
        out = {"model": VOCAB.model_names.get(s.model_id) or s.family or "unknown, ask the customer", "edition": s.edition,
               "machine": _machine_view(s)}
        if (s.model_id or s.family) and s.pending_description and not s.diagnosis:
            out["next"] = f"the fault was already described: call find_procedure now with: {s.pending_description!r}"
        if not s.machine:
            # the digits did not come through ("Bir, bir", "Beer"): the city, the business name and the model usually do
            said = (args.get("customer_words") or "") + " " + " ".join(u["text"] for u in s.utterances if u["role"] == "customer")
            fam = CATALOG.family_models(s.family) if s.family and not s.model_id else None
            cands = CATALOG.machines_matching(said, s.model_id, fam)
            if len(cands) == 1:
                c = cands[0]
                out["candidate"] = {"serial": c["serial"], "model": VOCAB.model_names.get(c["model_id"], c["model_id"]),
                                    "customer": c["customer"], "city": c["city"]}
                out["hint"] = (f"the serial was not understood, but one machine on file matches: the {out['candidate']['model']} "
                               f"at {c['customer']}, {c['city']}. Ask the customer to confirm it; if yes, call identify_machine "
                               f"with serial {c['serial']}. Do not ask for the digits again.")
            elif len(cands) > 1:
                out["candidates"] = [{"serial": c["serial"], "customer": c["customer"], "city": c["city"]} for c in cands[:3]]
                out["hint"] = "several machines match: ask which business it is, or the serial digit by digit"
        if s.diagnosis and s.diagnosis.outcome:
            # the warranty is known now: what the customer pays may have changed (shipping, service), say it from here
            out["outcome_now"] = _outcome_view(s)
        return out
    if name == "find_procedure":
        desc = args.get("description") or ""
        s.pending_description = desc or s.pending_description
        if not (s.model_id or s.family or s.machine):
            # procedures differ by machine (an Onda has a steam boiler of its own, a Marea does not): know it first
            return {"status": "need_machine",
                    "hint": "the procedure depends on the machine: ask which Sereni machine it is (model name on the front, or "
                            "the serial number on the plate at the back), call identify_machine, then call find_procedure again "
                            "with this same description. Do not ask the customer to describe the fault again."}
        if not (s.diagnosis and s.diagnosis.current):
            await s._detect_symptom([desc], semantic=True)
        if s.diagnosis and s.diagnosis.current:
            return {"status": "opened", **_step_view(s), **_already_answered(s, desc)}
        if s.diagnosis and s.diagnosis.outcome:
            return {"status": "outcome", **_outcome_view(s)}
        cands = s.symptom_candidates(desc)
        if cands:
            return {"status": "candidates", "candidates": cands, "hint": "ask the customer which one applies, then call start_procedure"}
        return {"status": "none", "hint": "ask the customer to describe, in a few words, what the machine does or does not do"}
    if name == "start_procedure":
        await s.control({"action": "start_symptom", "symptom_id": args.get("symptom_id")})
        if s.diagnosis and s.diagnosis.current:
            said = " ".join(u["text"] for u in s.utterances if u["role"] == "customer")[-400:]
            return {"status": "opened", **_step_view(s), **_already_answered(s, said)}
        return {"status": "error", "hint": "unknown procedure id; use an id from find_procedure"}
    if name == "answer_step":
        d = s.diagnosis
        if not (d and d.current):
            return {"status": "no_open_step", "hint": "call find_procedure first"} if not (d and d.outcome) else {"status": "outcome", **_outcome_view(s)}
        i = int(args.get("option_number") or 0) - 1
        if not 0 <= i < len(d.step["branches"]):
            return {"status": "error", "hint": "option_number must be one of the options", "options": _step_view(s)["options"]}
        words = args.get("customer_words") or ""
        # The guard: the customer's own words are the evidence, not the agent's bookkeeping. Our classifier (numbers,
        # yes/no, on/off, negation, shared words, meaning, in English and Italian) reads them against the CURRENT step:
        #   words pick the agent's option                       -> apply (even if the agent quoted a stale step_id)
        #   words pick nothing, words + earlier call pick it    -> apply ("no alarm" after "it stays cold")
        #   words pick nothing, stale step_id                   -> a late or repeated call: nothing moves
        #   words pick nothing / a different option (1st time) -> the agent asks or confirms; the 2nd call is accepted
        st = d.step
        from ..session import SEMANTIC

        def read(text: str):
            out = []
            for lab, q in (("label_en", "text_en"), ("label_it", "text_it")):
                brs = [{**b, "label_en": b.get(lab) or b["label_en"]} for b in st["branches"]]
                out.append(classify_branch(text, brs, SEMANTIC.similarities, question=st[q] if st["kind"] == "ask" else ""))
            hits = [r for r in out if r[0] is not None]
            return max(hits, key=lambda r: r[1]) if hits else (None, max(r[1] for r in out))

        j, conf = read(words)
        known = _known_from_record(s)
        other_number = numbers_in(words) - {re.sub(r"\D", "", s.machine["voltage"])} if known is not None else set()
        if known is not None and i == known and not other_number and polarity(words) >= 0 \
                and not re.search(r"\b(no|not|wrong|different)\b", words, re.I):
            j, conf = known, 1.0                               # "yes, correct" confirms what the serial's record says
        if j is None:
            context = " ".join(u["text"] for u in s.utterances if u["role"] == "customer")[-300:]
            if context and context.strip() != words.strip():
                jc, cc = read(words + " " + context)
                if jc == i:                                     # context may confirm the agent, never pick for it
                    j, conf = jc, cc
        stale = bool(args.get("step_id")) and args["step_id"] != d.current
        if j is None and stale:
            return {"status": "stale", "hint": f"step '{args['step_id']}' was already answered and these words do not answer "
                                              f"the current step '{d.current}'. Ask its question now.", **_step_view(s)}
        tries = s.unclear_count.get(d.current, 0)
        short_reply = len(words.split()) <= 5
        first_time = tries == 0 or (tries == 1 and j is None and not short_reply)
        if (j is None or j != i) and first_time:
            s.unclear_count[d.current] = tries + 1
        if j is None and first_time:
            s.unclear_steps.add(d.current)
            s._log_decision("branch_rejected", step=d.current, text=words, agent_option=i, confidence=conf)
            return {"status": "unclear",
                    "hint": "the customer's words do not answer this step. Do not choose for them: ask exactly this question, "
                            "then call answer_step again with what they say.", **_step_view(s)}
        if j is not None and j != i and first_time:
            s.unclear_steps.add(d.current)
            s._log_decision("branch_mismatch", step=d.current, text=words, agent_option=i, classifier=j, confidence=conf)
            return {"status": "confirm",
                    "hint": f"the customer's words sound like '{st['branches'][j]['label_en']}', not '{st['branches'][i]['label_en']}'. "
                            "Ask a short confirmation question, then call answer_step with the option the customer confirms.",
                    **_step_view(s)}
        s._log_decision("branch", step=d.current, text=words, chosen=i, by="voice-agent", classifier=j, confidence=conf, stale_id=stale)
        await s.control({"action": "answer_step", "branch": i})
        if d.outcome:
            return {"status": "outcome", **_outcome_view(s)}
        return {"status": "next_step", **_step_view(s)}
    if name == "find_part":
        q = args.get("query") or ""
        cards = await s.parts_for(q)
        if not cards:
            # "G2410": one letter of the code lost in transcription. The digits and the first letter are enough.
            from ..session import CATALOG
            for letter, digits in re.findall(r"\b([A-Za-z])\s*-?\s*(\d{4})\b", q):
                for code in CATALOG._parts:
                    if code[0] == letter.upper() and code.endswith(digits):
                        cards += await s.parts_for(code)
        if not cards:
            return {"status": "none", "hint": "no part on file matches these words. Do not invent one: call note_for_operator with the "
                                              "request and tell the customer the operator will follow up (or ask for the code on the invoice)."}
        return {"status": "found", "parts": [_card_view(c, s.charge_for(c["code"])) for c in cards]}
    if name == "book_slot":
        proposed = [c for c in (s.diagnosis.outcome.parts if s.diagnosis and s.diagnosis.outcome else [])
                    if c in s.cards and s.cards[c]["status"] == "proposed"]
        await s.control({"action": "book_slot", "id": args.get("slot_id")})     # booking also orders the outcome's parts
        if s.booking:
            v = s._slot_view(s.booking)
            ordered = [c for c in proposed if s.cards[c]["status"] == "confirmed"]
            return {"status": "booked", "when": v["label_en"], "with": s.booking["technician"],
                    "parts_ordered_with_it": ordered,
                    "next": "ask if there is anything else; if not, say goodbye, THEN call end_call"}
        return {"status": "error", "hint": "slot id not free or unknown; propose another from the outcome"}
    if name == "set_email":
        raw = str(args.get("email") or "").strip().lower()
        em = raw if re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+", raw) else email_in(raw)
        if not em:
            return {"status": "incomplete", "hint": "that is not a complete address: ask for the part that is missing (the name, or what comes after the at sign)"}
        if not said_email(em, [u["text"] for u in s.utterances if u["role"] == "customer"][-12:]):
            return {"status": "not_heard", "hint": "the customer's words do not contain this address: ask them to spell it again, slowly"}
        await s._set_email(em)
        return {"status": "recorded", "email": em, "read_back": " ".join(em.replace("@", " at ").replace(".", " dot ").split()),
                "next": "read it back and ask if it is right; if not, ask for the correct one and call set_email again"}
    if name == "confirm_parts":
        if args.get("email"):
            raw = str(args["email"]).strip().lower()
            em = raw if re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+", raw) else email_in(raw)
            if em and said_email(em, [u["text"] for u in s.utterances if u["role"] == "customer"][-12:]):
                await s._set_email(em)                     # never an address the customer did not say
        codes = [str(c).upper().strip() for c in (args.get("codes") or [])]
        done = []
        for code in codes:
            if code in s.cards:
                await s.control({"action": "confirm_part", "code": code})
                done.append(code)
        if not done:
            return {"status": "error", "hint": "none of these codes is on the table; use the codes from the outcome or from find_part"}
        pays = s._next_step().get("payment") if s.diagnosis and s.diagnosis.outcome else None
        if pays and pays["status"] == "awaiting_payment" and not s.email:
            return {"status": "confirmed", "codes": done, "email_missing": True,
                    "say": "the order is recorded; ask the customer's email for the quote and the payment instructions, "
                           "spell it back, then call confirm_parts again with the same codes and the email"}
        return {"status": "confirmed", "codes": done, "email": s.email or None,
                "say": "the order is recorded; an operator approves it and the parts are shipped from our warehouse"}
    if name == "get_call_status":
        s._log_decision("status_asked", question=args.get("question", ""))
        return call_status(s)
    if name == "note_for_operator":
        note = (args.get("note") or "").strip()
        if note:
            s.notes.append(note)
            if re.search(r"declin|fit.{0,20}(alone|himself|herself|themsel|own)|monta.{0,20}da sol", note, re.I):
                s.fits_alone = True
            await s._agent(("Nota per l'operatore: " if s.lang == "it" else "Note for the operator: ") + note)
        return {"status": "noted", "say": "the operator will follow up on this"}
    if name == "end_call":
        s.end_wanted = True
        d = s.diagnosis
        if d and d.current and "step" not in s.end_refused:
            # the procedure is still open: the customer's last answer must be recorded first ("it works now")
            s.end_refused.add("step")
            return {"status": "open_step", "end": False,
                    "hint": "a procedure step is still open. Call answer_step now with the customer's last answer to it "
                            "(for example 'fixed'), then say goodbye and call end_call again.", **_step_view(s)}
        pending = [c for c in (d.outcome.parts if d and d.outcome else []) if c in s.cards and s.cards[c]["status"] == "proposed"]
        if pending and "parts" not in s.end_refused:
            s.end_refused.add("parts")
            return {"status": "parts_not_confirmed", "end": False, "codes": pending,
                    "hint": "the outcome's parts are not ordered. If the customer agreed, call confirm_parts with these codes; "
                            "if not, say so. Then say goodbye and call end_call again."}
        needs_visit = bool(d and d.outcome and d.outcome.kind in ("part_with_support", "technician"))
        if needs_visit and not s.booking and not s.notes and "visit" not in s.end_refused:
            s.end_refused.add("visit")
            what = "a second call with our service to fit the parts" if d.outcome.kind == "part_with_support" else "a technician's visit"
            return {"status": "service_not_booked", "end": False,
                    "hint": f"this repair needs {what}: nothing is booked. Explain once, briefly, that this part must be fitted with "
                            "our service on the line (electrical/safety work, and it keeps the warranty on the repair), and propose a "
                            "slot. If the customer still declines, call note_for_operator with 'customer declines service support', "
                            "then say goodbye and call end_call again."}
        # the customer decides when the call is over: "That's right." is not a goodbye (26/9: the call was closed on it)
        customer_leaving = customer_is_leaving(s.last_customer_text)
        if not customer_leaving and "else" not in s.end_refused:
            s.end_refused.add("else")
            return {"status": "customer_not_done", "end": False,
                    "hint": "the customer has not said goodbye. Ask 'Is there anything else I can help you with?' and WAIT for "
                            "the answer. Only if they have nothing else, thank them, say goodbye and call end_call again."}
        # the agent's goodbye transcript can arrive after its end_call: a customer who already said goodbye or thanks
        # is leaving, so no second goodbye is asked for
        if not _GOODBYE.search(s.last_agent_text or "") and not customer_leaving and "bye" not in s.end_refused:
            s.end_refused.add("bye")
            return {"status": "no_goodbye", "end": False,
                    "hint": "ask the customer if there is anything else; if not, thank them and say goodbye, then call end_call again."}
        s.voice_done = True
        # the goodbye was already said: another one after this result doubled it (26/9)
        return {"status": "ok", "end": True, "say": "nothing: the goodbye was already said, the call is closing"}
    return {"status": "error", "hint": f"unknown tool {name}"}


_LEAVING = re.compile(r"\b(that'?s all|that is all|nothing else|no,? that'?s it|no,? thanks?|no,? thank you|"
                      r"è tutto|niente altro|nient'altro|no,? grazie|nada más|eso es todo|no,? gracias|das war'?s|"
                      r"nein,? danke|c'est tout|non,? merci|é tudo|não,? obrigad\w*)\b", re.I)


def customer_is_leaving(text: str | None) -> bool:
    """The customer's last words close the call: a goodbye, or "no, that's all" / "no thanks" after "anything else?".
    A thank-you alone is not enough: the live transcript once turned "in order to save something" into "Thank you."
    with full confidence (26/9)."""
    return bool(text and (_GOODBYE.search(text) or _LEAVING.search(text)))


def ready_to_hang_up(s, agent_text: str) -> bool:
    """The page hangs up when the agent says goodbye AFTER the customer is leaving (goodbye, thanks, "that's all").
    An agent that says goodbye on its own does not close the call."""
    if s.voice_done or not _GOODBYE.search(agent_text or ""):
        return False
    return customer_is_leaving(s.last_customer_text)


def tool_result_text(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)
