"""Can the only model a free account gets (qwen3.5-4b-32k-fast) do the 'clear version' job?"""
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
KEY = os.environ["ASSEMBLYAI_API_KEY"]
URL = "https://llm-gateway.assemblyai.com/v1/chat/completions"

SYSTEM = (
    "You help an Italian help-desk operator understand a foreign customer on a phone call about a professional "
    "espresso machine. The customer speaks broken English with a strong accent; the text comes from speech "
    "recognition and may contain errors. Rewrite what the customer MEANT as one or two short, clear Italian "
    "sentences. Keep every part code (like GE-2140), model name (Marea, Giglio, Onda, Monda, Vaniglia) and number "
    "exactly as written. Use the Italian trade words: shower screen = doccetta, group gasket = guarnizione sottocoppa, "
    "portafilter = portafiltro, steam wand = lancia vapore, blind filter = filtro cieco, boiler = caldaia, "
    "gauge = manometro, burrs = macine. Do not add information. Do not explain. Answer with the Italian sentence only."
)

TURNS = [
    "Hi, ja, we have a Marea 2 Plus, the coffee she come out sin and fast like water since two week.",
    "I unscrew ze shower screen, is full of white stuff but the holes they are okay, not broken.",
    "Also when I lock the portafilter it go very far to the right and water come around, last year we order GE-2140.",
    "The machine she no heat, gauge is zero, lights are on, I press red button behind but nothing happen.",
    "How long it take to arrive in Hamburg? We are closed Monday.",
]

import sys
GAP = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
for turn in TURNS:
    time.sleep(GAP)
    t = time.perf_counter()
    r = httpx.post(URL, headers={"Authorization": KEY}, timeout=30, json={
        "model": "qwen3.5-4b-32k-fast", "max_tokens": 160, "temperature": 0.1,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": turn}]})
    dt = time.perf_counter() - t
    body = r.json()
    out = body["choices"][0]["message"]["content"] if r.status_code == 200 else json.dumps(body)[:300]
    print(f"[{dt:.1f}s] {turn}\n     -> {out}\n")
