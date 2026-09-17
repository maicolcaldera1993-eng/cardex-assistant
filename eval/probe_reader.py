"""Level 3 probe: can the only LLM a free account gets (qwen3.5-4b-32k-fast) READ a messy call
transcript and fill in a call sheet? Each conversation is read at growing cut points, the way
the app would do every ~30 seconds. Free tier allows ~2 requests per minute, so calls are spaced."""
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
KEY = os.environ["ASSEMBLYAI_API_KEY"]
URL = "https://llm-gateway.assemblyai.com/v1/chat/completions"
MODEL = os.getenv("LLM_MODEL", "qwen3.5-4b-32k-fast")
GAP = float(os.getenv("PROBE_GAP", "33"))

defects = json.loads((ROOT / "data/kb/defects/marea.json").read_text(encoding="utf-8"))
SYMPTOMS = {s["id"]: s["symptom_en"] for s in defects["symptoms"]}
SYMPTOMS.update({"monda-grinds-slow-hot": "Grinder grinds slowly, gets hot, coffee tastes burnt",
                 "monda-does-not-start": "Grinder does not start, or starts and stops"})
MODELS = ["Marea 2", "Marea 2 Plus", "Marea 2 Evo", "Giglio 1", "Giglio 1 Plus", "Onda MB2", "Onda MB3",
          "Onda MB2 Evo", "Monda 65", "Monda 65 Digit"]

SYSTEM = (
    "You read the live transcript of a technical support phone call for Sereni, an Italian maker of professional "
    "espresso machines and grinders. The text comes from speech recognition of people speaking broken English with "
    "strong accents, so words may be wrong. Fill in the call sheet from what has been said SO FAR. "
    "Never invent: use null when something was not said.\n\n"
    "Machine models (pick exactly one of these names or null; customers mispronounce them, e.g. 'Maria' means Marea, "
    "'giggly' means Giglio, 'Honda' means Onda, 'Monday' means Monda):\n- " + "\n- ".join(MODELS) + "\n\n"
    "Known symptoms (pick exactly one id or null):\n" + "\n".join(f"- {k}: {v}" for k, v in SYMPTOMS.items()) + "\n\n"
    "Part codes look like two letters, a dash and four digits (GE-2140).\n\n"
    "Answer with ONE JSON object and nothing else, with these keys: "
    '"machine" (string or null), "edition_vaniglia" (true/false), "serial" (string of digits or null), '
    '"voltage" (string or null), "symptom_id" (string or null), "part_codes" (list of strings), '
    '"customer_wants" (one short Italian sentence), '
    '"clear_it" (list of short Italian sentences, one for each CUSTOMER line of the transcript, same order).'
)

CONVERSATIONS = {
    "A tedesco, sintomo spezzato, modello detto tardi": {
        "turns": [
            ("OPERATOR", "Sereni service, good morning, this is Laura."),
            ("CUSTOMER", "Ja hello, here is Jonas from Cafe Berlin in Hamburg."),
            ("CUSTOMER", "We have problem since, ah, two week maybe."),
            ("CUSTOMER", "The coffee, you know, she is not good anymore."),
            ("OPERATOR", "Okay, what is the problem exactly?"),
            ("CUSTOMER", "It come very quick. Like, ah, how you say, no body. Is like water with colour."),
            ("OPERATOR", "I understand. Which machine do you have?"),
            ("CUSTOMER", "Is the Maria, the two group, the plus one. The cream colour, vanilla."),
            ("CUSTOMER", "Serial number is zero four seven two one nine."),
            ("CUSTOMER", "And last year we buy the rubber for the group, on invoice is written GE-2140, maybe we need again."),
        ],
        "cuts": [4, 7, 10],
        "expected": {"machine": "Marea 2 Plus", "edition_vaniglia": True, "serial": "047219",
                     "symptom_id": "marea-weak-coffee", "part_codes": ["GE-2140"]},
    },
    "B turco, non scalda, tensione 110": {
        "turns": [
            ("OPERATOR", "Sereni service, Laura speaking."),
            ("CUSTOMER", "Hello, I am Emre, from Istanbul, coffee shop Galata."),
            ("CUSTOMER", "Machine is giggly one, we buy two thousand twenty four."),
            ("CUSTOMER", "This morning I open the shop, I switch on, I wait, I wait. Nothing."),
            ("OPERATOR", "Nothing at all? Are the lights on?"),
            ("CUSTOMER", "Light yes, button yes. But the needle, the pressure, stay zero. Water is cold. No steam."),
            ("CUSTOMER", "Our electric here in this place is one hundred ten volt, special."),
            ("CUSTOMER", "I think is the resistance. You have code? I see in the book CA-1191."),
        ],
        "cuts": [4, 8],
        "expected": {"machine": "Giglio 1", "edition_vaniglia": False, "serial": None, "voltage": "110",
                     "symptom_id": "marea-no-heat", "part_codes": ["CA-1191"]},
    },
    "C spagnolo, macinacaffè": {
        "turns": [
            ("OPERATOR", "Sereni service, good afternoon."),
            ("CUSTOMER", "Hola, good afternoon, Carmen from Bar Sol, Valencia."),
            ("CUSTOMER", "I call for the grinder, the Monday sixty five, the one with the display."),
            ("CUSTOMER", "It take very long for one dose now, before five second, now twelve."),
            ("CUSTOMER", "And the coffee powder come out warm, and taste a little burn."),
            ("OPERATOR", "How many kilos did you grind with these burrs?"),
            ("CUSTOMER", "Uf, I don't know, maybe seven hundred, eight hundred kilo. Never changed."),
        ],
        "cuts": [4, 7],
        "expected": {"machine": "Monda 65 Digit", "edition_vaniglia": False, "serial": None,
                     "symptom_id": "monda-grinds-slow-hot", "part_codes": []},
    },
}


def call(transcript: str) -> tuple[dict | None, str, float]:
    t = time.perf_counter()
    for attempt in range(4):
        r = httpx.post(URL, headers={"Authorization": KEY}, timeout=60, json={
            "model": MODEL, "temperature": 0, "max_tokens": 700,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": "TRANSCRIPT SO FAR:\n" + transcript}]})
        if r.status_code != 429:
            break
        time.sleep(31)
    dt = time.perf_counter() - t
    if r.status_code != 200:
        return None, r.text[:300], dt
    raw = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        return json.loads(m.group(0)) if m else None, raw, dt
    except ValueError:
        return None, raw, dt


def norm(v):
    if isinstance(v, str):
        return re.sub(r"\D", "", v) if re.fullmatch(r"[\d\s\-V volt]+", v) else v.strip().lower()
    return v


results = []
first = True
for name, conv in CONVERSATIONS.items():
    print(f"\n=== {name}")
    for cut in conv["cuts"]:
        if not first:
            time.sleep(GAP)
        first = False
        transcript = "\n".join(f"{who}: {text}" for who, text in conv["turns"][:cut])
        sheet, raw, dt = call(transcript)
        final = cut == conv["cuts"][-1]
        print(f"\n--- dopo {cut} turni ({dt:.1f}s){'  [LETTURA FINALE]' if final else ''}")
        if sheet is None:
            print("   RISPOSTA NON VALIDA:", raw[:400])
            results.append((name, cut, final, None))
            continue
        for k in ("machine", "edition_vaniglia", "serial", "voltage", "symptom_id", "part_codes", "customer_wants"):
            print(f"   {k:17s}: {sheet.get(k)}")
        for line in sheet.get("clear_it", [])[-3:]:
            print(f"   chiaro           : {line}")
        if final:
            exp = conv["expected"]
            checks = {}
            for k, v in exp.items():
                got = sheet.get(k)
                if k == "part_codes":
                    checks[k] = sorted(got or []) == sorted(v)
                elif k in ("serial", "voltage"):
                    checks[k] = (re.sub(r"\D", "", str(got or "")) or None) == (re.sub(r"\D", "", str(v or "")) or None)
                else:
                    checks[k] = norm(got) == norm(v)
            print("   CONTROLLO        :", "  ".join(f"{k}={'OK' if ok else 'NO'}" for k, ok in checks.items()))
            results.append((name, cut, final, checks))

print("\n\n=== RIEPILOGO LETTURE FINALI")
tot = ok = 0
for name, cut, final, checks in results:
    if final and checks:
        tot += len(checks)
        ok += sum(checks.values())
        print(f"   {name}: {sum(checks.values())}/{len(checks)}")
print(f"   campi giusti: {ok}/{tot}")
