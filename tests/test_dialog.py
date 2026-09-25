"""The automatic assistant: reading the customer's answer to pick a branch, digits, polarity, wording."""
import pytest

pytest.importorskip("fastembed")

from app.agent.dialog import classify_branch, digits_in, for_customer, polarity  # noqa: E402
from app.core.semantic import SemanticIndex  # noqa: E402
from app.core.symptoms import DefectsLibrary  # noqa: E402

sem = SemanticIndex()
sem.load()
lib = DefectsLibrary()


def branches(symptom: str, step: str) -> list[dict]:
    return lib.symptoms[symptom]["_steps"][step]["branches"]


CASES = [
    # (symptom, step, what the customer said, expected branch label)
    ("marea-no-heat", "lights", "Yes, everything is on, the lights, the buttons. No alarm. But it is cold.", "On, boiler full, cold"),
    ("marea-no-heat", "reset", "Okay, I found the red button, I pressed it. Ten minutes later it is still cold. Nothing.", "Still cold"),
    ("marea-no-heat", "contactor", "Yes, I hear the click when I switch on. But no heat.", "Clicks, but no heat"),
    ("marea-no-heat", "element", "It is one hundred ten volts, the American version.", "Marea 2 / Plus, 110 V"),
    ("marea-group-leak", "where", "From the rim, from the edge of the portafilter. Not from above.", "From the portafilter rim"),
    ("marea-group-leak", "gasket-age", "The first one: the handle goes past the centre.", "Over a year, or past the centre"),
    ("marea-steam-weak-or-dripping", "which", "Weak steam, it does not drip.", "Weak steam"),
    ("marea-steam-weak-or-dripping", "boiler-ok", "The needle is at one point two.", "Yes"),
    ("marea-steam-weak-or-dripping", "tip", "I did it, the holes were half closed with milk. Now the steam is strong again. Fixed.", "Fixed"),
    ("marea-level-alarm", "tap", "The tap is open, yes. The hot water comes out strong, full.", "Open, full flow"),
    ("marea-level-alarm", "click", "Yes, I hear a click, click, but it does not fill.", "Clicks, but does not fill"),
    ("marea-level-alarm", "probe", "I cleaned it and put it back. Now the pump stopped, the boiler is full. It works.", "Cleaned: fixed"),
    ("marea-weak-coffee", "backflush", "Okay, I did the backflush now, five times with the tablet. It is still weak.", "Still weak"),
    ("marea-spits-end-of-shot", "backflush-date", "Hmm, maybe three weeks ago.", "More than a week ago"),
]


@pytest.mark.parametrize("symptom,step,text,expected", CASES)
def test_customer_answer_picks_the_branch(symptom, step, text, expected):
    st = lib.symptoms[symptom]["_steps"][step]
    i, conf = classify_branch(text, st["branches"], sem.similarities, question=st["text_en"] if st["kind"] == "ask" else "")
    assert i is not None, f"unsure ({conf}) for {text!r}"
    assert st["branches"][i]["label_en"] == expected


def test_numbers_said_in_words():
    from app.agent.dialog import numbers_in
    assert numbers_in("It is one hundred ten volts") == {"110"}
    assert numbers_in("two hundred and thirty volts, bought in 2024") == {"230", "2024"}
    assert numbers_in("the needle is at one point two") == {"1.2"}
    assert numbers_in("about fifteen, eighteen seconds") == {"15", "18"}


def test_unclear_answer_is_not_forced():
    br = branches("marea-no-heat", "lights")
    i, _ = classify_branch("Hmm, let me think about it.", br, sem.similarities)
    assert i is None


def test_digits_and_polarity_and_wording():
    assert digits_in("The serial is zero four one, three zero two.") == "041302"
    assert digits_in("041302") == "041302"
    assert digits_in("we bought it in 2024") == ""
    assert polarity("Yes, that works, perfect.") > 0 and polarity("No, still the same.") < 0
    assert for_customer("Have them open the grind by two notches, dose 14 g, pull another shot.").startswith("Please open")
    assert "Can you open" in for_customer("Can the customer open the solenoid valve body?")



def test_serial_digits_in_the_customer_language():
    assert digits_in("zero cinque uno, zero quattro zero") == "051040"
    assert digits_in("cero cinco dos, siete uno cero") == "052710"
    assert digits_in("null vier vier, acht null eins") == "044801"


def test_serial_said_twice_or_next_to_other_numbers():
    from app.agent.dialog import serials_in
    assert digits_in("Il numero di serie è zero cinque uno, zero quattro zero. 051040.") == "051040"
    assert digits_in("Sì, esatto. Zero cinque uno, zero quattro zero. 051040.") == "051040"
    assert digits_in("051040051040") == "051040"
    assert serials_in("bought in 2024, 230 volts") == []
    assert digits_in("zero cinque due sette uno zero") == "052710"
