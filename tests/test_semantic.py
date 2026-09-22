"""Meaning, not words: fault descriptions in languages we never wrote must land on the right symptom.
Reference texts exist only in Italian and English. Needs the local embedding model (downloaded once)."""
import pytest

pytest.importorskip("fastembed")

from app.core.semantic import DECOY_MARGIN, SYMPTOM_THRESHOLD, SemanticIndex  # noqa: E402
from app.session import sentence_complete  # noqa: E402

sem = SemanticIndex()
sem.load()
MAREA = sem.ids_for("symptom", "marea-2-plus")

CASES = [
    ("it", "il caffè esce in maniera debole, è un po' annacquato", "marea-weak-coffee"),
    ("it", "la macchina stamattina è rimasta gelata, non va in temperatura", "marea-no-heat"),
    ("en", "ze coffee she come out sin, no taste, run very quick", "marea-weak-coffee"),
    ("en", "when I take off the handle after the coffee it explodes everywhere", "marea-spits-end-of-shot"),
    ("en", "milk is not foaming anymore, the steam is very poor", "marea-steam-weak-or-dripping"),
    ("de", "Der Kaffee ist wässrig und läuft viel zu schnell durch", "marea-weak-coffee"),
    ("de", "Die Maschine wird nicht mehr heiß, der Kessel bleibt kalt", "marea-no-heat"),
    ("es", "el café sale aguado y muy rápido, sin crema", "marea-weak-coffee"),
    ("es", "un botón ya no responde y las dosis salen mal", "marea-doses-and-buttons"),
    ("tr", "kahve çok sulu ve hızlı akıyor", "marea-weak-coffee"),
    ("tr", "makine ısınmıyor, kazan soğuk kalıyor", "marea-no-heat"),
    ("fr", "la machine siffle quand elle chauffe le matin", "marea-hiss-at-startup"),
    ("fr", "la pompe fait du bruit et la pression ne monte pas", "marea-pump-pressure-low"),
    ("zh", "咖啡很淡，像水一样，流得太快", "marea-weak-coffee"),
    ("zh", "机器不加热，锅炉是冷的", "marea-no-heat"),
    ("pt", "a máquina está completamente morta, não acende nenhuma luz", "marea-machine-dead"),
]


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_fault_described_in_any_language(lang, text, expected):
    top = sem.search(text, allowed=MAREA, k=1)[0]
    assert top.node_id == f"symptom/{expected}" and top.score >= SYMPTOM_THRESHOLD


@pytest.mark.parametrize("text", [
    "good morning, this is Jonas calling from Cafe Berlin",
    "buongiorno, la chiamo da Amburgo, mi sente bene?",
    "können Sie mir die Rechnung per E-Mail schicken?",
    "thank you very much, have a nice day",
])
def test_small_talk_is_not_a_symptom(text):
    hits = [m for m in sem.search(text, allowed=MAREA, k=1) if m.score >= SYMPTOM_THRESHOLD and not sem.nodes[m.node_id].get("decoy")]
    assert hits == []


def test_graph_filter_keeps_other_machines_out():
    evo = sem.ids_for("symptom", "marea-2-evo")
    assert "symptom/marea-boiler-pressure" not in evo          # the Evo has no pressurestat procedure
    assert sem.ids_for("manual", "marea-2-plus") and not sem.ids_for("manual", "onda-mb2")


def test_manual_section_and_sentence_to_highlight():
    allowed = sem.ids_for("manual", "marea-2-plus")
    top = sem.search("how often should we clean the groups with the tablet?", allowed=allowed, k=1)[0]
    assert "ogni-giorno" in top.node_id
    sentence, score = sem.best_sentence("how often should we clean the groups with the tablet?", sem.nodes[top.node_id]["refs"][1 + sem.nodes[top.node_id]["n_topics"]:])
    assert "pastiglia" in sentence.lower() and score > 0.45


# --- the "doses instead of weak coffee" rehearsal bug (22 Sept): a sentence cut in two by the turn detector -------------
def _scores(text):
    ms = sem.search(text, allowed=MAREA, k=4)
    decoy = max((m.score for m in ms if sem.nodes[m.node_id].get("decoy")), default=0.0)
    real = [(m.node_id.split("/", 1)[1], m.score) for m in ms if not sem.nodes[m.node_id].get("decoy")]
    return decoy, real


def test_half_sentence_does_not_clear_the_decoy():
    decoy, real = _scores("Since maybe 2 weeks, the coffee comes out very")
    assert real and real[0][1] < decoy + DECOY_MARGIN


def test_the_other_half_is_a_clear_symptom():
    decoy, real = _scores("thin and fast.")
    assert real[0][0] == "marea-weak-coffee" and real[0][1] >= max(SYMPTOM_THRESHOLD, decoy + DECOY_MARGIN)


@pytest.mark.parametrize("text,ok", [
    ("the coffee comes out very", False), ("thin and fast.", True), ("Is it still the same part?", True),
    ("No body, no crema!", True), ("the code is GE", False), ("Well...", True),
])
def test_sentence_complete(text, ok):
    assert sentence_complete(text) is ok
