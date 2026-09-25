"""Operator-assist core: symptoms matched from the customer's words, step-by-step procedures and their outcomes,
answers to an open step not taken for new faults, keyterm vocabulary reloaded in phases, operator/customer roles from
AssemblyAI speaker labels."""
import pytest

from app.core.catalog import Catalog
from app.core.roles import CUSTOMER, OPERATOR, RoleTracker
from app.core.symptoms import DefectsLibrary, Outcome
from app.core.vocabulary import MAX_CHARS, MAX_TERMS, VocabularyManager

lib = DefectsLibrary()
cat = Catalog()
vocab = VocabularyManager(cat)


@pytest.mark.parametrize("text,symptom", [
    ("The coffee comes out thin and fast, like water.", "marea-weak-coffee"),
    ("il caffè esce slavato", "marea-weak-coffee"),
    ("it is leaking from the group when I lock the handle", "marea-group-leak"),
    ("the machine does not heat, the gauge is at zero", "marea-no-heat"),
    ("the steam wand drips all the time", "marea-steam-weak-or-dripping"),
    ("we have a level alarm and it is not filling", "marea-level-alarm"),
    ("un tasto non funziona più", "marea-doses-and-buttons"),
    ("it hisses when it heats up in the morning", "marea-hiss-at-startup"),
])
def test_symptom_match(text, symptom):
    hit = lib.match(text, model_id="marea-2-plus")
    assert hit and hit.symptom_id == symptom


def test_no_symptom_in_small_talk():
    assert lib.match("good morning, this is Jonas from Cafe Berlin", model_id="marea-2-plus") is None


def test_symptom_respects_model_scope():
    # boiler pressure procedure does not apply to the Evo (no pressurestat)
    assert lib.match("boiler pressure high", model_id="marea-2-evo") is None
    assert lib.match("boiler pressure high", model_id="marea-2").symptom_id == "marea-boiler-pressure"


def test_golden_path_descale_then_gasket():
    d = lib.start("marea-weak-coffee")
    assert d.step["id"] == "time"
    d.answer(1)                       # 25-30 s, normal
    assert d.step["id"] == "backflush-date"
    d.answer(1)                       # yesterday
    assert d.step["id"] == "screen"
    d.answer(0)                       # scaled but intact
    assert d.step["id"] == "descale-screen"
    out = d.answer(0)                 # fixed
    assert isinstance(out, Outcome) and out.kind == "remote" and d.view()["done"]
    assert d.view("en")["outcome"] == "remote"


def test_branch_to_part_and_maintenance_flag():
    d = lib.start("marea-weak-coffee")
    d.answer(1)
    d.answer(0)                       # last backflush more than a week ago -> maintenance skipped
    assert "CR-6052" in d.suggested_parts and d.view()["maintenance_skipped"]
    d.answer(1)                       # backflush did not fix it
    out = d.answer(1)                 # screen domed
    assert out.kind == "part_diy" and out.parts == ["GE-2150"]


def test_view_has_english_sentence_for_operator():
    v = lib.start("marea-no-heat").view("it")
    assert v["step"]["text"].startswith("Le spie") and v["step"]["say_in_english"].startswith("Are the lights")


def test_vocabulary_phases():
    v1 = vocab.build()
    assert v1.phase == 1 and "Giglio 1 Plus" in v1.keyterms and "GE-2140" not in v1.keyterms
    v2 = vocab.build(model_id="marea-2-plus")
    assert v2.phase == 2 and v2.keyterms[0] == "Marea 2 Plus" and "GE-2140" in v2.keyterms
    assert "GE-2410" not in v2.keyterms          # Onda gasket has no business in a Marea call
    assert "Marea 2 Plus" in v2.prompt
    v3 = vocab.build(model_id="marea-2-plus", group="CA", symptom_parts=["CA-1180", "CA-1220"])
    assert v3.phase == 3 and v3.keyterms[1:3] == ["CA-1180", "CA-1220"]
    for v in (v1, v2, v3):
        assert len(v.keyterms) <= MAX_TERMS and all(len(t) <= MAX_CHARS for t in v.keyterms)
        assert len(set(t.lower() for t in v.keyterms)) == len(v.keyterms)


def test_vocabulary_family_only():
    v = vocab.build(family="Onda")
    assert v.phase == 2 and "GE-2410" in v.keyterms and "GE-2140" not in v.keyterms


def test_roles():
    r = RoleTracker()
    assert r.role_for("A")[0] == OPERATOR
    assert r.role_for("B")[0] == CUSTOMER
    assert r.role_for("PENDING")[0] == CUSTOMER      # inherits previous speaker
    assert r.role_for("A")[0] == OPERATOR
    r.swap()
    assert r.role_for("A")[0] == CUSTOMER
    assert RoleTracker(single_speaker_role=CUSTOMER).role_for("A")[0] == CUSTOMER


@pytest.mark.parametrize("text,symptom", [
    # sentences actually spoken by the project owner in the first microphone test
    ("Abbiamo una macchinetta del caffè Marea 2 Plus e abbiamo notato che il caffè esce in maniera debole.", "marea-weak-coffee"),
    ("È un po' annacquato, quasi imbevibile.", "marea-weak-coffee"),
    ("la macchina non si scalda più da ieri", "marea-no-heat"),
    ("it won't fill, there is no water in the boiler", "marea-level-alarm"),
])
def test_symptoms_as_people_really_say_them(text, symptom):
    hit = lib.match(text, model_id="marea-2-plus")
    assert hit and hit.symptom_id == symptom


def test_pinned_customer_label_wins_over_first_speaker_rule():
    r = RoleTracker()
    r.pin_customer("A")                       # the recorded customer spoke first
    assert r.role_for("A")[0] == CUSTOMER
    assert r.role_for("B")[0] == OPERATOR
    assert r.role_for("A")[0] == CUSTOMER


# --- while a step is open, the customer's words are answers, not new faults (Dave rehearsal, 22 Sept) ---------------
def test_answers_to_the_open_step_are_not_new_symptoms():
    from app.core.symptoms import DefectsLibrary
    lib = DefectsLibrary()
    d = lib.start("marea-no-heat")                      # step "lights": are the lights and touchpad on? level alarm?
    assert d.is_answer("Yes, everything is on, the lights, the buttons.")
    assert d.is_answer("No alarm.")
    d.answer(2)                                         # -> reset: press the red button, wait 10 minutes
    assert d.is_answer("Okay, I found the red button, I pressed it.")
    assert d.is_answer("10 minutes later, it is still cold.")
    assert d.is_answer("Nothing.")
    # a genuinely new fault, said in a full sentence about other things, is not an answer
    assert not d.is_answer("When I take out the portafilter after the coffee, it sprays everywhere.")
    d.answer(1)
    d.answer(0)
    d.answer(0)                                         # element -> outcome
    assert d.outcome and not d.is_answer("Nothing.")    # no open step: nothing is an answer any more
