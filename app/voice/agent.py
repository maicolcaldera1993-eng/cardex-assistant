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

from ..agent.dialog import digits_in, for_customer
from ..core.normalizer import extract_codes

AGENTS_URL = "https://agents.assemblyai.com/v1"
AGENT_NAME = "Cardex Assistant"
VOICE_ID = os.getenv("CARDEX_VOICE", "alba")

SYSTEM_PROMPT = """You are the first-line service assistant of Sereni, an espresso machine maker in Florence, Italy. You are on the phone with a customer, usually a barista abroad, and you speak simple, clear English.

HOW YOU WORK
1. You do not diagnose. The troubleshooting procedure decides. When the customer has described what the machine is doing, call find_procedure with their words. Then ask what the current step asks, in your own natural words, one question at a time.
2. After the customer answers a step (or reports what happened after doing what you asked), call answer_step with the number of the option that matches their words. If nothing matches, ask again and mention the options in plain words. Never call answer_step to guess.
3. When a step asks the customer to do something (press, unscrew, clean, backflush), explain it simply, wait for them to do it and tell you the result, then call answer_step.
4. Order of things: as soon as the fault is described, call find_procedure and ask its first question. Right after the customer answers that first question, ask for the serial number (it is on the plate at the back) and call identify_machine with the digits and the model words the customer used: it tells you the machine, whether it is under warranty and who pays. Then continue with the steps.
5. Say prices, delivery times, part codes, warranty, totals and dates ONLY when they come from a tool result in this conversation. Never invent a number, never name a part the tools did not return, never explain what broke beyond what the step or the outcome says. Use the "spoken" forms given in the results for codes and prices (for example "C A twelve seventy, twelve euros sixty").
6. Customer questions: answer from tool results when you can. The outcome gives the total of the parts (parts_total_eur), the delivery days, the warranty and whether labour is charged, and whether a service call or a technician is needed; use them. Call note_for_operator only for things the tools do not cover (discounts, invoices, complaints, anything outside the procedure), say the operator will follow up, then return to the procedure.
7. At the outcome, explain what happens next (parts shipped, second call with service, technician's visit), who pays, and propose the first free slot from the result. When the customer agrees, call book_slot with that slot id. If they prefer another, propose the next one.
8. Keep every reply to one or two short sentences. Warm and professional, never chatty. Repeat numbers back to confirm them.
10. If a tool result says "stale" or "error", call answer_step again right away with the step_id given in that result and the option matching the customer's words. Never guess the outcome yourself and never use find_part to work out which part is needed: only the procedure's outcome names the parts. find_part is for parts the customer asks about by code or by name.
9. When there is nothing else, thank them, say goodbye, and call end_call.
Everything you do is recorded for a human operator, who approves orders and bookings afterwards; say so if asked."""

GREETING = "Sereni service, good morning. Which machine are you calling about, and what is it doing?"

TOOLS: list[dict] = [
    {"name": "identify_machine",
     "description": "Call as soon as the customer names the machine model and/or reads the serial number. Returns the machine on file: model, edition, warranty status, who pays for a technician, previous orders. Pass the customer's exact words for the model; never guess.",
     "parameters": {"type": "object", "properties": {
         "model_text": {"type": "string", "description": "The customer's words about the model, e.g. 'the Marea 2 Plus, the vanilla one'"},
         "serial": {"type": "string", "description": "Serial number as read by the customer, digits possibly separated by spaces, e.g. '0 4 7 2 1 9' or '047219'", "pattern": "^[0-9A-Za-z][0-9A-Za-z -]{3,14}$"}},
         "required": []}, "execution_mode": "hold"},
    {"name": "find_procedure",
     "description": "Call when the customer has described what the machine is doing wrong, in their own words. Opens the matching troubleshooting procedure and returns its first step. If it returns candidates instead, ask the customer which one applies and call start_procedure. When in doubt, call it: a wasted call is fine.",
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
    {"name": "note_for_operator",
     "description": "Call when the customer asks for something you cannot answer from tool results (discounts, invoices, anything outside the procedure) or wants something done by a person. Tell the customer the operator will follow up.",
     "parameters": {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]}, "execution_mode": "interactive"},
    {"name": "end_call",
     "description": "Call right after you have said goodbye, when the customer has nothing else.",
     "parameters": {"type": "object", "properties": {}, "required": []}, "execution_mode": "interactive"},
]

def session_config(keyterms: list[str]) -> dict:
    """What the browser sends in session.update: the whole agent inline (a stored agent_id cannot be combined
    with per-session tools, and our tools are client-side functions executed by this server)."""
    cfg = agent_config(keyterms)
    return {"system_prompt": cfg["system_prompt"], "greeting": cfg["greeting"], "input": cfg["input"],
            "output": cfg["output"], "tools": [{"type": "function", **t} for t in TOOLS]}   # "function" = executed by the client


_agent_id: str | None = None


def agent_config(keyterms: list[str]) -> dict:
    return {"name": AGENT_NAME, "system_prompt": SYSTEM_PROMPT, "greeting": GREETING,
            "voice": {"voice_id": VOICE_ID},
            "input": {"format": {"encoding": "audio/pcm", "sample_rate": 24000}, "keyterms": keyterms[:100],
                      "turn_detection": {"vad_threshold": 0.5, "min_silence": 900, "max_silence": 2500, "interrupt_response": True}},
            "output": {"voice": VOICE_ID, "format": {"encoding": "audio/pcm", "sample_rate": 24000}, "volume": 100},
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
def _step_view(s) -> dict:
    d = s.diagnosis
    st = d.step
    text = for_customer(st["text_en"])
    return {"symptom": d.symptom["symptom_en"], "step_id": st["id"], "kind": st["kind"],
            "ask_the_customer": text if st["kind"] == "ask" else text + " Then ask what happened.",
            "options": [{"number": i + 1, "label": b["label_en"]} for i, b in enumerate(st["branches"])],
            "note": st.get("note_en")}


def _machine_view(s) -> dict:
    m = s.machine
    if not m:
        return {"serial": s.serial, "on_file": False, "warranty": "unknown", "hint": "ask for the serial number on the plate at the back"}
    return {"serial": m["serial"], "on_file": True, "model": m["model_id"], "edition": m.get("edition"), "built": m["built"],
            "voltage": m["voltage"], "customer": m["customer"], "city": m["city"], "country": m["country"],
            "warranty": "under warranty until " + m["warranty_until"] if m.get("in_warranty") else "out of warranty since " + m["warranty_until"],
            "who_pays_technician": "Sereni" if m.get("in_warranty") else "the customer",
            "notes": m.get("notes"), "matched_exactly": m.get("matched_exactly", True),
            "previous_orders": [f"{o['ordered_on']} {o['code']} x{o['qty']}" for o in m.get("orders", [])[:4]]}


def _outcome_view(s) -> dict:
    n = s._next_step()
    kind = n["kind"]
    out = {"outcome": kind,
           "meaning": {"remote": "fixed remotely, nothing to ship",
                       "part_diy": "ship the parts, the customer fits them with the sheet",
                       "part_with_support": "ship the parts and book a second call with service to fit them",
                       "technician": "a technician's visit is needed"}[kind],
           "warranty": {True: "under warranty: no charge", False: "out of warranty: parts and labour are charged, a quote follows",
                        None: "warranty unknown: ask the serial number"}[n["warranty"]],
           "parts": [{"code": p["code"], "spoken": spoken_code(p["code"]) + ", " + spoken_price(p["price_eur"]),
                      "description": p.get("description_en") or p["description"], "price_eur": p["price_eur"],
                      "delivery": (p["delivery"][0]["from"].replace("FI-01 ", "").replace("NL-01 ", "") + ", " + p["delivery"][0]["days"] + " working days") if p["delivery"] else "unknown",
                      "fitting": {"diy": "the customer fits it", "support": "fitted on a service call"}.get(p["handling"], p["handling"])}
                     for p in n["parts"]],
           "parts_total_eur": round(sum(p["price_eur"] or 0 for p in n["parts"]), 2),
           "parts_total_spoken": spoken_price(round(sum(p["price_eur"] or 0 for p in n["parts"]), 2))}
    b = n.get("booking")
    if b:
        out["booking"] = {"kind": "technician's visit" if b["kind"] == "onsite" else "second call with service (video call)",
                          "booked": b["booked"]["label_en"] if b["booked"] else None,
                          "need_serial": b["need_serial"], "no_partner": b["no_partner"],
                          "free_slots": [{"slot_id": x["id"], "when": x["label_en"], "with": x["technician"]} for x in b["slots"]]}
    return out


def _card_view(c: dict) -> dict:
    d = c["delivery"][0] if c.get("delivery") else None
    return {"code": c["code"], "spoken": spoken_code(c["code"]) + ", " + spoken_price(c["price_eur"]),
            "description": c.get("description_en") or c["description"], "price_eur": c["price_eur"],
            "delivery": (d["from"].replace("FI-01 ", "").replace("NL-01 ", "") + ", " + d["days"] + " working days") if d else "unknown",
            "fits_this_machine": c["compatible"], "superseded_by": c.get("superseded_by"), "requires": c.get("requires"),
            "fitting": {"diy": "the customer fits it", "support": "fitted on a service call"}.get(c.get("handling"), c.get("handling")),
            "note": c.get("note")}


async def run_tool(s, name: str, args: dict) -> dict:
    """Executes one tool call from the voice agent on the call session. Returns what the agent may say."""
    args = args or {}
    if name == "identify_machine":
        if args.get("model_text"):
            await s.apply_model_words(args["model_text"])
        serial = digits_in(args.get("serial") or "") or re.sub(r"[^0-9A-Za-z]", "", args.get("serial") or "")
        if len(serial) >= 5:
            await s._set_serial(serial.upper())
        from ..session import VOCAB
        return {"model": VOCAB.model_names.get(s.model_id) or s.family or "unknown, ask the customer", "edition": s.edition,
                "machine": _machine_view(s)}
    if name == "find_procedure":
        desc = args.get("description") or ""
        if not (s.diagnosis and s.diagnosis.current):
            await s._detect_symptom([desc], semantic=True)
        if s.diagnosis and s.diagnosis.current:
            return {"status": "opened", **_step_view(s)}
        if s.diagnosis and s.diagnosis.outcome:
            return {"status": "outcome", **_outcome_view(s)}
        cands = s.symptom_candidates(desc)
        if cands:
            return {"status": "candidates", "candidates": cands, "hint": "ask the customer which one applies, then call start_procedure"}
        return {"status": "none", "hint": "ask the customer to describe, in a few words, what the machine does or does not do"}
    if name == "start_procedure":
        await s.control({"action": "start_symptom", "symptom_id": args.get("symptom_id")})
        if s.diagnosis and s.diagnosis.current:
            return {"status": "opened", **_step_view(s)}
        return {"status": "error", "hint": "unknown procedure id; use an id from find_procedure"}
    if name == "answer_step":
        d = s.diagnosis
        if not (d and d.current):
            return {"status": "no_open_step", "hint": "call find_procedure first"} if not (d and d.outcome) else {"status": "outcome", **_outcome_view(s)}
        if args.get("step_id") and args["step_id"] != d.current:
            # a repeated or late call: that step is gone, do not apply the answer to the next one
            return {"status": "stale", "hint": f"step '{args['step_id']}' was already answered. Call answer_step again NOW with step_id "
                                              f"'{d.current}' and the option matching the customer's words; do not guess the outcome.",
                    **_step_view(s)}
        i = int(args.get("option_number") or 0) - 1
        if not 0 <= i < len(d.step["branches"]):
            return {"status": "error", "hint": "option_number must be one of the options", "options": _step_view(s)["options"]}
        s._log_decision("branch", step=d.current, text=args.get("customer_words", ""), chosen=i, by="voice-agent")
        await s.control({"action": "answer_step", "branch": i})
        if d.outcome:
            return {"status": "outcome", **_outcome_view(s)}
        return {"status": "next_step", **_step_view(s)}
    if name == "find_part":
        q = args.get("query") or ""
        cards = await s.parts_for(q)
        if not cards:
            return {"status": "none", "hint": "no part matches; ask for the code on the invoice or the packaging"}
        return {"status": "found", "parts": [_card_view(c) for c in cards]}
    if name == "book_slot":
        await s.control({"action": "book_slot", "id": args.get("slot_id")})
        if s.booking:
            v = s._slot_view(s.booking)
            return {"status": "booked", "when": v["label_en"], "with": s.booking["technician"]}
        return {"status": "error", "hint": "slot id not free or unknown; propose another from the outcome"}
    if name == "note_for_operator":
        note = (args.get("note") or "").strip()
        if note:
            s.notes.append(note)
            await s._agent(("Nota per l'operatore: " if s.lang == "it" else "Note for the operator: ") + note)
        return {"status": "noted", "say": "the operator will follow up on this"}
    if name == "end_call":
        s.voice_done = True
        return {"status": "ok", "end": True}
    return {"status": "error", "hint": f"unknown tool {name}"}


def tool_result_text(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)
