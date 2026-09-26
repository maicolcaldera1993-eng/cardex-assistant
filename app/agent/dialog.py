"""Reading what the customer said: which option of a procedure step they picked (classify_branch), yes/no, numbers
said in words, serial numbers, email addresses, the language they speak. Deterministic checks the server runs on the
Voice Agent's reports, so the agent never advances a procedure on words that do not answer the step."""
from __future__ import annotations

import re
from typing import Callable

from ..core.symptoms import content_words

YES = {"yes", "yeah", "yep", "correct", "exactly", "fixed", "works", "working", "better", "good", "true", "perfect",
       "solved", "normal", "great", "sì", "si", "funziona", "risolto", "esatto", "giusto", "certo", "sí", "ja", "oui"}
NO = {"no", "nope", "not", "never", "nothing", "still", "same", "doesn't", "dont", "don't", "isn't", "cannot", "can't",
      "cant", "unchanged", "worse", "dead", "damaged", "broken", "ancora", "niente", "nulla", "rotto", "rotta", "uguale"}

DIGIT_WORDS = {"zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
               "seven": "7", "eight": "8", "nine": "9",
               # Italian, Spanish, German: serial numbers are read digit by digit in the customer's language
               "uno": "1", "due": "2", "tre": "3", "quattro": "4", "cinque": "5", "sei": "6", "sette": "7", "otto": "8",
               "nove": "9", "cero": "0", "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7",
               "ocho": "8", "nueve": "9", "null": "0", "eins": "1", "zwei": "2", "drei": "3", "vier": "4", "fünf": "5",
               "sechs": "6", "sieben": "7", "acht": "8", "neun": "9"}

def polarity(text: str) -> int:
    """+1 for a yes-like text, -1 for a no-like one, 0 when unclear ("okay, I did it, still weak" is not a yes)."""
    w = set(re.findall(r"[a-zàèéìòùí']+", text.lower()))
    y, n = len(w & YES), len(w & NO)
    return 0 if y == n else (1 if y > n else -1)


def serials_in(text: str) -> list[str]:
    """Every 5-8 digit number in a sentence, said as one block ('041302') or in short groups of digits
    ('zero four one, three zero two'). A sentence ends a number, so a serial said twice ('zero cinque uno, zero
    quattro zero. 051040.') gives the same number twice instead of twelve digits; a year next to a voltage
    ('2024, 230 volts') is not glued into a serial because only groups of up to three digits are joined."""
    t = text.lower()
    for w, d in DIGIT_WORDS.items():
        t = re.sub(rf"\b{w}\b", d, t)
    out: list[str] = []
    for run in re.findall(r"\d+(?:[\s,\-]+\d+)*", t):
        chunks = re.findall(r"\d+", run)
        if len(chunks) > 1 and any(len(c) > 3 for c in chunks):
            chunks = [c for c in chunks if len(c) > 3]         # long blocks stand alone
            out += [c for c in chunks if 5 <= len(c) <= 8]
            continue
        n = "".join(chunks)
        if 5 <= len(n) <= 8:
            out.append(n)
        elif len(n) > 8 and len(n) % 2 == 0 and n[:len(n) // 2] == n[len(n) // 2:]:
            out.append(n[:len(n) // 2])                        # said twice without a pause
    return out


_LANG_WORDS = {
    "en": set("the and is it i you we my this that with have what for are yes please can there not was it's i'm don't "
              "machine coffee does".split()),
    "it": set("il lo gli che non è sono ho una per con della del mi ci ma anche perché questo quando sì grazie "
              "buongiorno allora macchina caffè esce fa si perfetto va bene possiamo parlare avete abbiamo qualcuno "
              "piacere qui lì cosa come sempre ancora niente".split()),
    "es": set("el los las que es y una por con mi pero muy sí gracias buenos está tengo hola máquina café sale hace "
              "cuando también".split()),
    "de": set("der die das und ist nicht ich ein eine mit es sie wir haben auch aber ja danke guten bitte maschine "
              "kaffee kommt".split()),
    "fr": set("le les et est je pas une avec pour nous oui merci bonjour c'est il vous machine café fait quand "
              "aussi".split()),
    "pt": set("o os as é não um uma com para eu sim obrigado bom está tenho máquina café faz quando também "
              "ela".split()),
}


# "can we speak Italian?", "possiamo parlare in italiano?": a request wins over the words around it
_LANG_REQUEST = [
    ("it", r"\b(in italiano|parl\w* (l')?italiano|speak italian|in italian|italian please)\b"),
    ("es", r"\b(en espa[nñ]ol|habl\w* espa[nñ]ol|speak spanish|in spanish)\b"),
    ("de", r"\b(auf deutsch|deutsch sprechen|sprechen sie deutsch|speak german|in german)\b"),
    ("fr", r"\b(en fran[cç]ais|parl\w* fran[cç]ais|speak french|in french)\b"),
    ("pt", r"\b(em portugu[eê]s|fal\w* portugu[eê]s|speak portuguese|in portuguese)\b"),
    ("en", r"\b(in english|speak english|in inglese|en ingl[eé]s|auf englisch|en anglais|em ingl[eê]s)\b"),
]
_GREETING = {"buongiorno": "it", "buonasera": "it", "salve": "it", "pronto": "it", "hola": "es", "buenos": "es",
             "buenas": "es", "bonjour": "fr", "bonsoir": "fr", "allô": "fr", "olá": "pt", "bom": "pt",
             "guten": "de", "grüß": "de", "servus": "de"}


def language_request(text: str) -> str | None:
    """The language the customer explicitly asks for ("possiamo parlare in italiano?", "in English, please"), or None."""
    t = (text or "").lower()
    for lg, pat in _LANG_REQUEST:
        if re.search(pat, t):
            return lg
    return None


def language_of(text: str) -> str | None:
    """The language a sentence is in, from its commonest words (en/it/es/de/fr/pt), or None when too short or unclear.
    An explicit request ("possiamo parlare in italiano?") decides by itself, even inside an English sentence; a lone
    greeting ("Buongiorno.") is enough."""
    t = (text or "").lower()
    for lg, pat in _LANG_REQUEST:
        if re.search(pat, t):
            return lg
    words = re.findall(r"[a-zà-ÿ']+", t)
    if 0 < len(words) <= 2 and words[0] in _GREETING:
        return _GREETING[words[0]]
    if len(words) < 3:
        return None
    scores = {lg: sum(w in ws for w in words) for lg, ws in _LANG_WORDS.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (best, a), (_, b) = ranked[0], ranked[1]
    return best if a >= 2 and a >= b + 2 else None


_EMAIL = re.compile(r"[a-z0-9][a-z0-9._%+-]*@[a-z0-9-]+(?:\.[a-z0-9-]+)+", re.I)
_TLD = r"(?:com|it|de|es|us|net|org|at|nl|fr|eu|pt|be|ch|tr|co\.uk|uk)"


def email_in(text: str) -> str:
    """An email address, written ('dave@corner.com') or spoken ('dave at espresso corner dot com',
    'd a v e dot miller at gmail dot com', 'luca chiocciola pasteleria sol punto es')."""
    t = text.lower()
    m = _EMAIL.search(t)
    if m:
        return m.group(0).rstrip(".")
    s = re.sub(r"[,;]", " ", t)
    s = re.sub(r"\s+(?:at|chiocciola|arroba|at sign)\s+", "@", s)
    s = re.sub(r"\s+(?:dot|punto|punkt|point)\s+", ".", s)
    s = re.sub(r"\s+(?:underscore|trattino basso)\s+", "_", s)
    s = re.sub(r"\s+(?:dash|hyphen|trattino|minus)\s+", "-", s)
    m = re.search(rf"([a-z0-9._\- ]{{1,60}})@([a-z0-9\- ]{{1,40}}(?:\.[a-z0-9\- ]{{1,40}})*?\.{_TLD})\b", s)
    if not m:
        return ""
    tokens = m.group(1).split()
    if not tokens:
        return ""
    local = [tokens[-1]]
    for tok in reversed(tokens[:-1]):                     # spelled letters: "d a v e" -> "dave"
        if len(tok) == 1:
            local.insert(0, tok)
        else:
            break
    domain = re.sub(r"\s+", "", m.group(2))
    email = "".join(local) + "@" + domain
    return email if _EMAIL.fullmatch(email) else ""


def said_email(email: str, texts: list[str]) -> bool:
    """Did the customer say this address? Spelled ('M-A-I-C-O-L, Caldera, one nine nine three at G. Mail'), read out
    ('dave at espresso corner dot com') or written: the letters of the name and of the domain must appear, in order and
    without the gaps, in what the customer said."""
    if not email or "@" not in email or email.endswith("@example.com"):
        return False
    joined = ""
    for t in texts:
        t = t.lower()
        for w, d in DIGIT_WORDS.items():
            t = re.sub(rf"\b{w}\b", d, t)
        t = re.sub(r"\b(dot|punto|point|punkt|at|chiocciola|arroba|underscore|dash|hyphen|trattino)\b", " ", t)
        joined += re.sub(r"[^a-z0-9]", "", t)
    local, domain = email.lower().split("@", 1)
    local = re.sub(r"[^a-z0-9]", "", local)
    name = re.sub(r"[^a-z0-9]", "", domain.split(".")[0])
    return bool(local) and local in joined and name in joined


def digits_in(text: str) -> str:
    """'zero four one, three zero two' or '041302' -> '041302' (only when it looks like a serial)."""
    found = serials_in(text)
    return found[0] if found else ""


def for_customer(text: str) -> str:
    """The steps are written for an operator who relays them; the assistant talks to the customer directly."""
    t = re.sub(r"^Have them ", "Please ", text)
    t = re.sub(r"\bhave them\b", "please", t)
    t = re.sub(r"\bHave the customer\b", "Please", t)
    t = re.sub(r"\bCan the customer\b", "Can you", t)
    t = re.sub(r"\bthe customer\b", "you", t)
    return t


_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
          "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
          "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
          "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
ORDINALS = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4}
# a word on one side in the answer and the other side in the label: they disagree (on/off, open/closed...)
ANTONYMS = [("on", "off"), ("open", "closed"), ("full", "empty"), ("hot", "cold"), ("weak", "strong"), ("yes", "no"),
            ("clicks", "silent"), ("drains", "stays"), ("flat", "domed"),
            ("acceso", "spento"), ("accesa", "spenta"), ("aperto", "chiuso"), ("pieno", "vuoto"), ("caldo", "freddo"),
            ("sì", "no"), ("forte", "debole")]
_SIDES = {w: i for pair in ANTONYMS for i, w in enumerate(pair)}
_PAIR = {w: pair for pair in ANTONYMS for w in pair}


def _negated(words: list[str]) -> set[str]:
    """Content words within three tokens after a negation ('not from the group' -> {'group'})."""
    out: set[str] = set()
    for k, w in enumerate(words):
        if w in ("not", "no", "never", "without", "isn't", "doesn't", "don't", "nor"):
            out |= content_words(" ".join(words[k + 1:k + 4]))
    return out


def numbers_in(text: str) -> set[str]:
    """Numbers said in words or digits: 'one hundred ten volts' -> {'110'}, 'at one point two' -> {'1.2'}."""
    out: set[str] = set()
    toks = re.findall(r"[a-z]+|\d+(?:\.\d+)?", text.lower())
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        if re.fullmatch(r"\d+(?:\.\d+)?", t):
            out.add(t.rstrip("0").rstrip(".") if "." in t else t)
            i += 1
            continue
        if t in _UNITS:
            val, j, seen, expect = 0, i, False, "any"          # "twenty" may take a unit, "fifteen" ends the number
            while j < n and (toks[j] in _UNITS or toks[j] in ("hundred", "and")):
                w = toks[j]
                if w == "hundred":
                    val = (val or 1) * 100
                    expect = "any"
                elif w == "and":
                    if expect != "any":
                        break
                else:
                    v = _UNITS[w]
                    if expect == "unit" and not (1 <= v <= 9):
                        break
                    if expect == "none":
                        break
                    val += v
                    expect = "unit" if 20 <= v <= 90 else "none"
                seen = seen or w != "and"
                j += 1
            if j + 1 < n and toks[j] == "point" and toks[j + 1] in _UNITS and _UNITS[toks[j + 1]] < 10:
                dec = []
                j += 1
                while j < n and toks[j] in _UNITS and _UNITS[toks[j]] < 10:
                    dec.append(str(_UNITS[toks[j]]))
                    j += 1
                out.add(f"{val}.{''.join(dec)}")
            elif seen:
                out.add(str(val))
            i = j
            continue
        i += 1
    return out


_NOT_FIXED = re.compile(r"\b(doesn'?t|does not|didn'?t|did not|won'?t|not|nothing|no)\s+(work\w*|help\w*|chang\w*|fix\w*|better)\b|"
                        r"\bno (change|difference|luck)\b|\bsame (problem|thing|as before)\b|\bstill\b|"
                        r"\bnon (funziona|è cambiato|cambia|va)\b|\bancora\b|\bniente\b|\bsigue\b|\btodav[ií]a\b|"
                        r"\bno funciona\b|\bimmer noch\b|\bfunktioniert nicht\b|\btoujours\b|\bne marche pas\b|\bainda\b")
_FIXED = re.compile(r"\b(it )?works\b|\bworking (again|now)\b|\bfixed\b|\bsolved\b|\bresolved\b|\bgone\b|"
                    r"\bnow it'?s (fine|ok|okay|good)\b|\bfunziona\b|\brisolto\b|\bfunciona\b|\bfunktioniert\b|\bmarche\b")
# "I'd rather have a technician", "non vorrei smontare": the customer cannot or will not do it (the "No" option), even
# when the sentence also says "damage" ("...e poi creare dei danni" once picked "Yes, but the plunger is damaged")
_REFUSAL = re.compile(r"\bprefer\w*\b[^.]{0,40}\b(tecnico|technician|techniker|t[ée]cnico|technicien)|"
                      r"\b(rather not|i'?d rather have|i can'?t|i cannot|i won'?t|i don'?t want to|not able to|"
                      r"non (posso|riesco|voglio|vorrei|me la sento|saprei)|no (puedo|quiero|s[ée])|"
                      r"ich (kann|will|möchte) (das )?nicht|je ne (peux|veux|sais) pas|não (consigo|quero|sei))\b", re.I)
def cannot_options(branches: list[dict]) -> list[int]:
    """The options that mean "no / cannot do it" ("No", "Cannot find the button"), not "Still spits"."""
    return [k for k, b in enumerate(branches) if re.match(r"(no|not|cannot|can't|unable)\b", b["label_en"].strip(), re.I)]


_FIXED_LABEL = re.compile(r"\b(fixed|works|solved|resolved)\b")
_STILL_LABEL = re.compile(r"^(still|no change|same)\b|\bstill\b")


def classify_branch(text: str, branches: list[dict], similarities: Callable[[str, list[str]], list[float]] | None = None,
                    question: str = "") -> tuple[int | None, float]:
    """Which branch did the customer's answer pick? Meaning (embedding similarity with the branch labels) plus cheap
    signals that the embedding misses: numbers ('110 volts'), on/off-style antonyms, yes/no polarity, shared words,
    and 'the first one' after the options were read out. Returns (index, confidence) or (None, best score)."""
    labels = [b["label_en"] for b in branches]
    words = re.findall(r"[a-zàèéìòùí']+", text.lower())
    # "the first one", "the second", "la prima": an ordinal is a choice only as a short reply, not inside a sentence
    # ("book the first slot" is not option 1)
    if len(words) <= 4 or re.search(r"\b(first|second|third|fourth|fifth)\s+(one|option)\b", text.lower()):
        for w in words:
            if w in ORDINALS and ORDINALS[w] < len(labels):
                return ORDINALS[w], 1.0
    sims = similarities(text, labels) if similarities else [0.0] * len(labels)
    # yes/no counts only as an answer at the start ("No, still cold", "Yes, I hear it"), not inside a description
    # ("lights and buttons are on, but there are no alarms" is not a "no")
    # ... a "yes" also at the end ("... the boiler is full. It works."), where a "no" is usually a description ("no steam")
    tw, tn, pol_t = content_words(text), numbers_in(text), polarity(" ".join(words[:3]))
    if pol_t == 0 and polarity(" ".join(words[-3:])) > 0 and polarity(text) >= 0:
        pol_t = 1
    # "not from the group above": the words right after a negation count against a label that affirms them,
    # and for a label that negates them too ("Clicks, but no heat")
    negated = _negated(words)
    tw = tw - negated
    q_numbers = numbers_in(question) if question else set()
    def label_polarity(lab: str) -> int:
        # the label's yes/no is its first word ("No click"), or a "yes" anywhere ("Cleaned: fixed"); a "no" inside a
        # label describes ("Clicks, but no heat")
        p = polarity(lab.split()[0] if lab.split() else "")
        return 1 if p == 0 and polarity(lab) > 0 else p

    pols = [label_polarity(lab) for lab in labels]
    # the result of something the customer tried: "I've tried it, but it doesn't work" is "Still spits", "now it works"
    # is "Fixed"; the negative forms are read first, "doesn't work" contains "work"
    low = text.lower()
    tried_bad = bool(_NOT_FIXED.search(low))
    tried_good = not tried_bad and bool(_FIXED.search(low))
    refused = bool(_REFUSAL.search(low))
    negatives = cannot_options(branches)
    if refused and len(negatives) == 1:
        return negatives[0], 1.0                               # a refusal is decisive when the step has one "No"
    scores = []
    for k, (lab, sim) in enumerate(zip(labels, sims)):
        lw, ln, lwords = content_words(lab), numbers_in(lab), set(re.findall(r"[a-z']+", lab.lower()))
        l_neg = _negated(re.findall(r"[a-z']+", lab.lower()))
        s = sim
        if lw:
            s += 0.12 * len(lw & tw) / len(lw)
            s -= 0.15 * len((lw & negated) - l_neg)
            s += 0.15 * len(negated & l_neg)
        if ln and tn:
            # share of the label's numbers the customer said ("MB2, 230 V" vs "MB2, 110 V": the 2 alone is not enough)
            s += 0.5 * len(ln & tn) / len(ln) if ln & tn else -0.2
        for w in lwords & set(_SIDES):
            if w in words:
                s += 0.1                                          # same side of an on/off pair
            elif any(o in words for o in _PAIR[w] if o != w):
                s -= 0.3                                          # the opposite side
        pol_l = pols[k]
        if pol_t and pol_l:
            s += 0.2 if pol_t == pol_l else -0.2
        elif pol_t and -pol_t in pols and pol_t not in pols:
            s += 0.2          # "Yes, I hear the click": the other option is the explicit "No click", so this one is the yes
        if pol_l > 0 and len(lwords) <= 2 and q_numbers & tn:
            s += 0.5                                              # "Is it at 1.2 bar?" - "it is at 1.2": yes
        lab_fixed, lab_still = bool(_FIXED_LABEL.search(lab.lower())), bool(_STILL_LABEL.search(lab.lower()))
        if refused and pols[k]:
            s += 0.5 if pols[k] < 0 else -0.4                   # "No" wins, "Yes, ..." loses
        if tried_bad and (lab_still or lab_fixed):
            s += 0.4 if lab_still else -0.4
        elif tried_good and (lab_still or lab_fixed):
            s += 0.4 if lab_fixed else -0.4
        scores.append(s)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    best = order[0]
    margin = scores[best] - (scores[order[1]] if len(order) > 1 else 0.0)
    if scores[best] < 0.35 or margin < 0.08:
        return None, round(scores[best], 3)
    return best, round(scores[best], 3)
