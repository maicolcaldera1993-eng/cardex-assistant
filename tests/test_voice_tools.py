"""The Voice Agent's tools, run against a call session with a fake browser: every fact the agent may say
comes from here (machine on file, procedure steps, outcome with parts and slots, part cards, bookings)."""
import asyncio

import pytest

pytest.importorskip("fastembed")

from app.session import SEMANTIC, CallSession  # noqa: E402
from app.voice.agent import TOOLS, run_tool  # noqa: E402

SEMANTIC.load()


def make_session():
    events = []

    async def emit(ev):
        events.append(ev)

    s = CallSession("key", emit, source="voice", lang="it")
    return s, events


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_tools_are_declared_for_the_session():
    names = {t["name"] for t in TOOLS}
    assert {"identify_machine", "find_procedure", "answer_step", "find_part", "book_slot", "note_for_operator", "end_call"} <= names
    assert len(TOOLS) <= 10
    for t in TOOLS:
        assert t["parameters"]["type"] == "object" and "description" in t


def test_dave_end_to_end_through_the_tools():
    s, events = make_session()
    m = run(run_tool(s, "identify_machine", {"model_text": "we have the Marea 2, the two group", "serial": "0 4 1 3 0 2"}))
    assert m["model"] == "Marea 2" and m["machine"]["on_file"] and m["machine"]["warranty"].startswith("out of warranty")
    assert m["machine"]["who_pays_technician"] == "the customer"

    p = run(run_tool(s, "find_procedure", {"description": "since this morning the machine stays cold, the pressure gauge is at zero"}))
    assert p["status"] == "opened" and p["symptom"].startswith("Does not heat") and p["step_id"] == "lights"
    assert [o["number"] for o in p["options"]] == [1, 2, 3]

    n = run(run_tool(s, "answer_step", {"step_id": "lights", "option_number": 3, "customer_words": "everything is on but it is cold"}))
    assert n["status"] == "next_step" and n["step_id"] == "reset" and n["kind"] == "do"
    assert n["ask_the_customer"].startswith("With the machine off") and "Then ask what happened" in n["ask_the_customer"]

    # the agent repeats the call for the step it already answered: nothing moves
    again = run(run_tool(s, "answer_step", {"step_id": "lights", "option_number": 3, "customer_words": "everything is on"}))
    assert again["status"] == "stale" and again["step_id"] == "reset" and s.diagnosis.current == "reset"

    bad = run(run_tool(s, "answer_step", {"step_id": "reset", "option_number": 9, "customer_words": "?"}))
    assert bad["status"] == "error"

    run(run_tool(s, "answer_step", {"step_id": "reset", "option_number": 2, "customer_words": "still cold"}))           # -> contactor
    run(run_tool(s, "answer_step", {"step_id": "contactor", "option_number": 1, "customer_words": "clicks, no heat"}))  # -> element
    o = run(run_tool(s, "answer_step", {"step_id": "element", "option_number": 2, "customer_words": "110 volts"}))
    assert o["status"] == "outcome" and o["outcome"] == "part_with_support"
    assert {x["code"] for x in o["parts"]} == {"CA-1181", "CA-1220"} and o["parts_total_eur"] == 98.9
    assert o["parts_total_spoken"] == "ninety-eight euros ninety"
    assert next(x["spoken"] for x in o["parts"] if x["code"] == "CA-1181") == "C A eleven eighty-one, ninety-six euros"
    assert o["warranty"].startswith("out of warranty")
    assert o["booking"]["kind"].startswith("second call") and o["booking"]["free_slots"]
    slot = o["booking"]["free_slots"][0]["slot_id"]

    b = run(run_tool(s, "book_slot", {"slot_id": slot}))
    assert b["status"] == "booked" and s.booking["id"] == slot

    t = run(run_tool(s, "find_part", {"query": "a box of the cleaning tablets"}))
    assert t["status"] == "found" and t["parts"][0]["code"] == "CR-6052" and t["parts"][0]["price_eur"] == 19.0

    note = run(run_tool(s, "note_for_operator", {"note": "asks for a discount on the element"}))
    assert note["status"] == "noted" and s.notes == ["asks for a discount on the element"]

    e = run(run_tool(s, "end_call", {}))
    assert e["end"] is True and s.voice_done
    kinds = [ev["type"] for ev in events]
    assert "machine_record" in kinds and "diagnosis" in kinds and "parts" in kinds


def test_vague_description_returns_candidates_not_a_guess():
    s, _ = make_session()
    run(run_tool(s, "identify_machine", {"model_text": "Marea 2 Plus"}))
    r = run(run_tool(s, "find_procedure", {"description": "we have a problem with the machine, it is not good since two weeks"}))
    assert r["status"] in ("candidates", "none")
    assert not (s.diagnosis and s.diagnosis.current)
    if r["status"] == "candidates":
        st = run(run_tool(s, "start_procedure", {"symptom_id": r["candidates"][0]["symptom_id"]}))
        assert st["status"] == "opened"


def test_transcript_relay_feeds_the_panel():
    s, events = make_session()
    run(s.voice_transcript("agent", "Sereni service, good morning. Which machine are you calling about?"))
    run(s.voice_transcript("customer", "The Marea 2 Plus. The serial number is 047219. Last year we ordered the gasket GE-2140."))
    turns = [ev for ev in events if ev["type"] == "turn"]
    assert [t["role"] for t in turns] == ["agent", "customer"]
    assert s.model_id == "marea-2-plus" and s.serial == "047219" and s.machine and s.machine["in_warranty"]
    assert "GE-2140" in s.cards
    assert not s.diagnosis      # in voice mode the procedure opens only through the agent's tool


def test_spoken_forms_for_the_voice():
    from app.voice.agent import num_words, spoken_code, spoken_price
    assert num_words(12) == "twelve" and num_words(96) == "ninety-six" and num_words(240) == "two hundred forty"
    assert spoken_code("CA-1270") == "C A twelve seventy"
    assert spoken_code("GE-2140") == "G E twenty-one forty"
    assert spoken_code("EL-3010") == "E L thirty ten"
    assert spoken_code("VA-5005") == "V A fifty oh five"
    assert spoken_code("CR-6100") == "C R sixty-one hundred"
    assert spoken_price(12.6) == "twelve euros sixty" and spoken_price(96.0) == "ninety-six euros" and spoken_price(2.9) == "two euros ninety"


def test_agent_cannot_advance_on_words_that_do_not_answer_the_step():
    """Mehmet's live call (24 Sept): 'I think it's dirty' was reported as 'over a year, or past the centre'."""
    s, _ = make_session()
    run(run_tool(s, "identify_machine", {"model_text": "Marea 2 Evo", "serial": "052710"}))
    p = run(run_tool(s, "find_procedure", {"description": "when I lock the portafilter, water comes out around the edge and drips into the cup"}))
    assert p["status"] == "opened" and p["step_id"] == "where"
    run(run_tool(s, "answer_step", {"step_id": "where", "option_number": 1, "customer_words": "From the rim, not from the group above."}))
    assert s.diagnosis.current == "gasket-age"
    r = run(run_tool(s, "answer_step", {"step_id": "gasket-age", "option_number": 1, "customer_words": "Uh, yeah, I think it's dirty. Also some coffee grounds."}))
    assert r["status"] == "unclear" and s.diagnosis.current == "gasket-age" and not s.diagnosis.outcome
    ok = run(run_tool(s, "answer_step", {"step_id": "gasket-age", "option_number": 1, "customer_words": "The original gasket, and the handle goes past the centre, almost to the right."}))
    assert ok["status"] == "outcome" and ok["outcome"] == "part_diy" and {x["code"] for x in ok["parts"]} == {"GE-2140", "GE-2210"}


def test_confirm_parts_records_the_order_for_the_operator():
    s, events = make_session()
    run(run_tool(s, "identify_machine", {"model_text": "Marea 2 Evo", "serial": "052710"}))
    run(run_tool(s, "find_procedure", {"description": "water comes out around the edge of the portafilter when I lock it"}))
    run(run_tool(s, "answer_step", {"step_id": "where", "option_number": 1, "customer_words": "From the rim, not from the group above."}))
    o = run(run_tool(s, "answer_step", {"step_id": "gasket-age", "option_number": 1, "customer_words": "The original one, and the handle goes past the centre."}))
    assert o["status"] == "outcome"
    bad = run(run_tool(s, "confirm_parts", {"codes": ["XX-0000"]}))
    assert bad["status"] == "error"
    ok = run(run_tool(s, "confirm_parts", {"codes": ["ge-2140", "GE-2210"]}))
    assert ok["status"] == "confirmed" and ok["codes"] == ["GE-2140", "GE-2210"]
    assert {c["code"] for c in s.cards.values() if c["status"] == "confirmed"} == {"GE-2140", "GE-2210"}


def test_session_config_speaks_the_customer_language():
    from app.voice.agent import session_config
    it = session_config(["Marea"], "it")
    assert it["output"]["voice"] == "giovanni" and it["greeting"].startswith("Servizio assistenza Sereni")
    assert "speak Italian" in it["system_prompt"] and it["input"]["turn_detection"]["min_silence"] == 1000
    assert session_config([], "xx")["output"]["voice"] == "alba"


def test_end_call_waits_for_the_open_step():
    s, _ = make_session()
    run(run_tool(s, "identify_machine", {"model_text": "Marea 2", "serial": "041188"}))
    run(run_tool(s, "find_procedure", {"description": "La macchina non carica l'acqua, la spia del livello lampeggia e la pompa va sempre."}))
    r = run(run_tool(s, "end_call", {}))
    assert r["status"] == "open_step" and r["end"] is False and not s.voice_done
    assert run(run_tool(s, "end_call", {}))["end"] is True
