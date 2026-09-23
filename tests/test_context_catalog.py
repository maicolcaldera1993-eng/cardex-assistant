import pytest

from app.core.catalog import Catalog
from app.core.context import ContextDetector

det = ContextDetector()
cat = Catalog()


@pytest.mark.parametrize("text,model", [
    ("We have a Marea 2 Plus, the Vaniglia edition.", "marea-2-plus"),
    ("We have a Maria 2 Plus the Vanilla Edition", "marea-2-plus"),          # what the ASR wrote without keyterms
    ("we have a Marya to Plus", None),                                        # too broken: family only
    ("In the other shop we have a giggly one plus", "giglio-1-plus"),
    ("and a Monday 65 Digit grinder", "monda-65-digit"),
    ("And the Honda MB2 has a probe alarm.", "onda-mb2"),
    ("the Onda M B two evo", "onda-mb2-evo"),
    ("abbiamo una Marea due evo", "marea-2-evo"),
    ("la Onda emme bi tre", "onda-mb3"),
    ("il Giglio uno", "giglio-1"),
])
def test_model_detection(text, model):
    assert det.detect(text).model_id == model


def test_longest_alias_wins():
    assert det.detect("a Marea 2 Plus").model_id == "marea-2-plus"
    assert det.detect("a Marea 2").model_id == "marea-2"


def test_family_only():
    h = det.detect("my Marea makes weak coffee from the group")
    assert h.model_id is None and h.family == "Marea" and "GE" in h.groups


def test_edition():
    assert det.detect("it is the vanilla one").edition == "vaniglia"


def test_onda_monda_tiebreak_by_topic():
    assert det.detect("the Onda, the burrs are worn").family == "Monda"
    assert det.detect("the Monda, the boiler is cold").family == "Onda"
    assert det.detect("the Honda has no steam").family == "Onda"


def test_monday_is_a_day_unless_machine_context():
    assert det.detect("I will call you back on Monday").family is None
    assert det.detect("the Monday 65 is slow").model_id == "monda-65"


def test_groups():
    assert "CA" in det.detect("the boiler is not heating").groups
    assert "VA" in det.detect("la lancia del vapore gocciola").groups


# -- catalog -------------------------------------------------------------------

def test_exact_code():
    cards = cat.search_code("GE-2140", model_id="marea-2-plus")
    assert [c.code for c in cards] == ["GE-2140"] and cards[0].reason == "exact" and cards[0].compatible
    assert cards[0].stock and cards[0].price_eur == 4.20


def test_exact_code_wrong_machine_shows_neighbour():
    # GE-2410 is the Onda gasket; on a Marea the customer almost certainly means GE-2140
    cards = cat.search_code("GE-2410", model_id="marea-2-plus", groups=["GE"])
    codes = [c.code for c in cards]
    assert codes[0] == "GE-2410" and not cards[0].compatible
    assert "GE-2140" in codes


def test_near_code_two_candidates():
    cards = cat.search_code("GE-2149", model_id="marea-2-plus")
    assert 1 <= len(cards) <= 2 and cards[0].reason == "near-code"
    assert cards[0].code in ("GE-2140", "GE-2141")


def test_supersession_brings_replacement_and_adapter():
    codes = [c.code for c in cat.search_code("EL-3010", model_id="marea-2")]
    assert codes == ["EL-3010", "EL-3012", "EL-3036"]


def test_unsure_asr_shows_neighbour():
    codes = [c.code for c in cat.search_code("CA-1180", model_id="marea-2", min_confidence=0.55)]
    assert codes[0] == "CA-1180" and len(codes) == 2


def test_description_search():
    cards = cat.search_description("I need the group gasket please", model_id="marea-2-plus")
    assert cards and cards[0].code == "GE-2140"
    cards = cat.search_description("mi serve la gomma del gruppo", model_id="marea-2-plus")
    assert cards and cards[0].code == "GE-2140"
    cards = cat.search_description("the group gasket", model_id="onda-mb2")
    assert cards and cards[0].code == "GE-2410"
    assert cat.search_description("good morning how are you", model_id="marea-2-plus") == []


def test_adapter_only_on_machines_that_need_it():
    assert [c.code for c in cat.search_code("EL-3010", model_id="marea-2-plus")] == ["EL-3010", "EL-3012"]
    assert [c.code for c in cat.search_code("EL-3010", model_id="giglio-1")] == ["EL-3010", "EL-3012", "EL-3036"]


# --- fictional service calendar: two weeks ahead, working days, free slots depend on the zone ---------------------
def test_service_calendar_is_per_zone_and_skips_weekends():
    from datetime import date
    from app.core.catalog import Catalog
    c = Catalog()
    monday = date(2026, 9, 21)
    for zone in ("DE", "AT", "REMOTE"):
        slots = c.service_slots(zone, from_day=1, limit=6, today=monday)
        assert 1 <= len(slots) <= 6
        for s in slots:
            assert date.fromisoformat(s["date"]).weekday() < 5
            assert s["zone"] == zone and s["id"].startswith(f"{zone}:")
    # deterministic (fixed seed at build time): same call, same calendar
    assert c.service_slots("DE", today=monday) == c.service_slots("DE", today=monday)
    # a busier partner has fewer free slots in the same window
    free = {z: len(c.service_slots(z, from_day=1, limit=40, today=monday)) for z in ("IT", "AT")}
    assert free["IT"] > free["AT"]
    # the remote call is booked after the parts can be there: from_day moves the first slot
    later = c.service_slots("REMOTE", from_day=5, today=monday)
    assert all(s["day_offset"] >= 5 for s in later)
    assert c.service_slots("XX", today=monday) == []


def test_service_zone_comes_from_the_machine_record():
    from app.core.catalog import Catalog
    c = Catalog()
    assert c.service_zone(c.machine("041302")) == "US"
    assert c.service_zone(c.machine("052710")) == "AT"
    assert c.service_zone(None) is None
