import pytest

from app.core.normalizer import canonicalize_codes, extract_codes, words_to_digits


def codes(text):
    return [c.code for c in extract_codes(text)]


@pytest.mark.parametrize("text,expected", [
    ("the code is GE-2140", ["GE-2140"]),
    ("the code is GE2140.", ["GE-2140"]),
    ("the code is GE 2140", ["GE-2140"]),
    ("the code is G E twenty-one forty", ["GE-2140"]),
    ("We also need the shower screen, G E two one five zero.", ["GE-2150"]),
    ("the invoice says C A eleven eighty", ["CA-1180"]),
    ("The control board is E L three zero one zero, and the pump is I D forty ten.", ["EL-3010", "ID-4010"]),
    ("The steam valve seal kit is V A fifty fifteen.", ["VA-5015"]),
    ("the burrs are M C seventy ten", ["MC-7010"]),
    ("The Onda gasket is G E twenty-four ten.", ["GE-2410"]),
    ("it is G E two thousand one hundred forty", ["GE-2140"]),
    ("GE 21 40", ["GE-2140"]),
    # italian
    ("codice gi e ventuno quaranta", ["GE-2140"]),
    ("la doccetta, gi e due uno cinque zero", ["GE-2150"]),
    ("sulla fattura c'è scritto ci a undici ottanta", ["CA-1180"]),
    ("la centralina è e elle tre zero uno zero, e la pompa è i di quaranta dieci", ["EL-3010", "ID-4010"]),
    ("il kit è vu a cinquanta quindici", ["VA-5015"]),
    ("le macine sono emme ci settanta dieci", ["MC-7010"]),
    ("gi e ventiquattro dieci", ["GE-2410"]),
    ("ci a undici ottantuno", ["CA-1181"]),
])
def test_codes(text, expected):
    assert codes(text) == expected


@pytest.mark.parametrize("text", [
    "I have a problem and it is getting worse",
    "e poi a me non va di aspettare due settimane",
    "we ordered it in twenty twenty four",
    "la macchina va a 230 volt",
])
def test_no_false_codes(text):
    assert codes(text) == []


def test_weak_shape_is_flagged():
    c = extract_codes("the code is G E two one four")
    assert len(c) == 1 and c[0].code == "GE-214" and not c[0].exact_shape


@pytest.mark.parametrize("text,expected", [
    ("We have a Marea two plus", "we have a marea 2 plus"),
    ("the Onda M B two has a probe alarm", "the onda mb2 has a probe alarm"),
    ("a Monda sixty-five digit grinder", "a monda 65 digit grinder"),
    ("il Giglio uno plus", "il giglio 1 plus"),
    ("la Onda emme bi tre", "la onda mb3"),
])
def test_words_to_digits(text, expected):
    assert words_to_digits(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("Ci sarebbe il control board e L3010.", "Ci sarebbe il control board EL-3010."),
    ("the code is G E twenty-one forty, I think", "the code is GE-2140, I think"),
    ("Scusate, il codice della fattura è GE-2140.", "Scusate, il codice della fattura è GE-2140."),
    ("the pump is I D forty ten and the board E L three zero one zero", "the pump is ID-4010 and the board EL-3010"),
    ("codice gi e ventuno quaranta grazie", "codice GE-2140 grazie"),
    ("good morning, how are you", "good morning, how are you"),
])
def test_canonicalize_codes_in_sentence(text, expected):
    assert canonicalize_codes(text)[0] == expected
