"""Spoken text -> canonical part codes.

A Sereni part code is two letters, a dash and four digits (GE-2140). On the phone
it arrives as "GE-2140", "GE2140", "G E twenty-one forty", "gi e due uno quattro
zero", "C A eleven eighty"... This module finds those sequences in a transcript
and returns canonical candidates. Pure logic, no I/O.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PREFIXES = ("GE", "CA", "ID", "VA", "EL", "CR", "MC")

# --- letters -----------------------------------------------------------------
LETTER_NAMES = {
    # english
    "a": "A", "ay": "A", "bee": "B", "be": "B", "see": "C", "cee": "C", "sea": "C", "dee": "D",
    "e": "E", "ee": "E", "gee": "G", "jee": "G", "g": "G", "i": "I", "eye": "I", "el": "L", "ell": "L",
    "em": "M", "m": "M", "ar": "R", "are": "R", "r": "R", "vee": "V", "v": "V", "c": "C", "d": "D", "l": "L", "b": "B",
    # italian
    "bi": "B", "ci": "C", "di": "D", "gi": "G", "elle": "L", "emme": "M", "erre": "R", "vu": "V", "vi": "V",
}

# --- numbers -----------------------------------------------------------------
EN_UNITS = {"zero": 0, "oh": 0, "o": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9}
EN_TEENS = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
            "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
EN_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
           "eighty": 80, "ninety": 90}

IT_UNITS = {"zero": 0, "uno": 1, "un": 1, "una": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6,
            "sette": 7, "otto": 8, "nove": 9}
IT_TEENS = {"dieci": 10, "undici": 11, "dodici": 12, "tredici": 13, "quattordici": 14, "quindici": 15,
            "sedici": 16, "diciassette": 17, "diciotto": 18, "diciannove": 19}
IT_TENS = {"venti": 20, "trenta": 30, "quaranta": 40, "cinquanta": 50, "sessanta": 60, "settanta": 70,
           "ottanta": 80, "novanta": 90}
_IT_TENS_STEMS = {k[:-1]: v for k, v in IT_TENS.items()}  # "vent", "quarant" ... for "ventuno", "quarantotto"


def _italian_compound(word: str) -> int | None:
    """ventuno -> 21, quarantotto -> 48, trentatré -> 33."""
    w = word.replace("é", "e").replace("è", "e")
    for tens_word, tens in IT_TENS.items():
        if w.startswith(tens_word) and len(w) > len(tens_word):
            unit = IT_UNITS.get(w[len(tens_word):])
            if unit:
                return tens + unit
    for stem, tens in _IT_TENS_STEMS.items():
        if w.startswith(stem) and len(w) > len(stem):
            unit = IT_UNITS.get(w[len(stem):])
            if unit in (1, 8):  # elision only before uno / otto
                return tens + unit
    return None


def number_token(tok: str) -> tuple[str, int] | None:
    """Classify a token: ('unit'|'teen'|'tens'|'compound'|'digits'|'hundred'|'thousand', value)."""
    if tok.isdigit():
        return ("digits", int(tok))
    if tok in EN_UNITS:
        return ("unit", EN_UNITS[tok])
    if tok in IT_UNITS:
        return ("unit", IT_UNITS[tok])
    if tok in EN_TEENS:
        return ("teen", EN_TEENS[tok])
    if tok in IT_TEENS:
        return ("teen", IT_TEENS[tok])
    if tok in EN_TENS:
        return ("tens", EN_TENS[tok])
    if tok in IT_TENS:
        return ("tens", IT_TENS[tok])
    if tok in ("hundred", "cento"):
        return ("hundred", 100)
    if tok in ("thousand", "mille", "mila"):
        return ("thousand", 1000)
    c = _italian_compound(tok)
    if c is not None:
        return ("compound", c)
    return None


_TOKEN_RE = re.compile(r"[a-zàèéìòù]+|\d+", re.I)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text.replace("-", " "))]


def read_digits(tokens: list[str], start: int, want: int = 4) -> tuple[str, int]:
    """Read number words from tokens[start:] as they are spoken in a code and return
    (digit_string, next_index). 'twenty one forty' -> '2140'; 'two one four zero' -> '2140';
    'two thousand one hundred forty' -> '2140'; '21 40' -> '2140'."""
    out = ""
    i = start
    raw_tokens = tokens  # digits tokens keep their original width ("07" stays "07")
    while i < len(tokens) and len(out) < want + 1:
        nt = number_token(tokens[i])
        if nt is None:
            break
        kind, val = nt
        if kind == "digits":
            out += raw_tokens[i]
            i += 1
        elif kind in ("thousand", "hundred"):
            # arithmetic form: rebuild the whole number from here backwards is messy; handle forward:
            # "<unit> thousand [<unit> hundred] [<tens> [<unit>]]"
            break
        elif kind == "unit":
            # look ahead for "X thousand ..." arithmetic
            if i + 1 < len(tokens) and number_token(tokens[i + 1]) in (("thousand", 1000),):
                total = val * 1000
                j = i + 2
                nxt = number_token(tokens[j]) if j < len(tokens) else None
                if nxt and nxt[0] == "unit" and j + 1 < len(tokens) and number_token(tokens[j + 1]) == ("hundred", 100):
                    total += nxt[1] * 100
                    j += 2
                elif nxt == ("hundred", 100):
                    total += 100
                    j += 1
                if j < len(tokens) and tokens[j] in ("and", "e"):
                    j += 1
                nxt = number_token(tokens[j]) if j < len(tokens) else None
                if nxt and nxt[0] in ("tens", "compound", "teen"):
                    total += nxt[1]
                    j += 1
                    nn = number_token(tokens[j]) if j < len(tokens) else None
                    if nxt[0] == "tens" and nn and nn[0] == "unit" and nn[1] > 0:
                        total += nn[1]
                        j += 1
                elif nxt and nxt[0] == "unit":
                    total += nxt[1]
                    j += 1
                out += str(total)
                i = j
            else:
                out += str(val)
                i += 1
        elif kind == "tens":
            nn = number_token(tokens[i + 1]) if i + 1 < len(tokens) else None
            if nn and nn[0] == "unit" and nn[1] > 0 and len(out) + 2 <= want:
                out += str(val + nn[1])
                i += 2
            else:
                out += str(val)
                i += 1
        else:  # teen, compound
            out += str(val)
            i += 1
    return out, i


def read_prefix(tokens: list[str], i: int) -> tuple[str, int] | None:
    """A known two-letter prefix at tokens[i]: written together ('ge') or spelled ('g','e' / 'gi','e')."""
    t = tokens[i].upper()
    if t in PREFIXES:
        return t, i + 1
    if i + 1 < len(tokens):
        a, b = LETTER_NAMES.get(tokens[i]), LETTER_NAMES.get(tokens[i + 1])
        if a and b and (a + b) in PREFIXES:
            return a + b, i + 2
    return None


@dataclass(frozen=True)
class CodeCandidate:
    code: str          # canonical, e.g. "GE-2140"; "??-2140" when the prefix was not heard
    raw: str           # the words it came from
    exact_shape: bool  # True when prefix + exactly four digits were heard


_WRITTEN = re.compile(r"\b([A-Za-z]{2})[\s\-\.]?(\d{4})\b")


def extract_codes(text: str) -> list[CodeCandidate]:
    found: list[CodeCandidate] = []
    seen: set[str] = set()

    def add(c: CodeCandidate) -> None:
        if c.code not in seen:
            seen.add(c.code)
            found.append(c)

    for m in _WRITTEN.finditer(text):
        if m.group(1).upper() in PREFIXES:
            add(CodeCandidate(f"{m.group(1).upper()}-{m.group(2)}", m.group(0), True))

    tokens = tokenize(text)
    i = 0
    while i < len(tokens):
        pref = read_prefix(tokens, i)
        if pref:
            prefix, j = pref
            digits, k = read_digits(tokens, j)
            if len(digits) == 4:
                add(CodeCandidate(f"{prefix}-{digits}", " ".join(tokens[i:k]), True))
                i = k
                continue
            if len(digits) in (3, 5):
                add(CodeCandidate(f"{prefix}-{digits}", " ".join(tokens[i:k]), False))
                i = k
                continue
        i += 1
    return found


def words_to_digits(text: str) -> str:
    """Lower-cased text with number words replaced by digits and spelled letter pairs joined:
    'the Marea two plus' -> 'the marea 2 plus'; 'Onda M B two' -> 'onda mb2';
    'Monda sixty-five digit' -> 'monda 65 digit'. Used to match model names."""
    tokens = tokenize(text)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        nt = number_token(tokens[i])
        if nt and nt[0] != "digits" and tokens[i] not in ("o", "oh", "un", "una", "e"):
            digits, j = read_digits(tokens, i, want=3)
            if digits:
                out.append(digits)
                i = j
                continue
        out.append(tokens[i])
        i += 1
    s = " ".join(out)
    s = re.sub(r"\b(m|em|emme)\s+(b|bee|bi)\s*(\d)\b", r"mb\3", s)
    s = re.sub(r"\bmb\s+(\d)\b", r"mb\1", s)
    return s
