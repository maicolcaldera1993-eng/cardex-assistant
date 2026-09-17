"""Can a small local multilingual embedding model map a free description of a fault,
in any language, onto one of the known symptoms? No keyword lists for the test phrases:
none of them appears in the defects file."""
import json
import time
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

ROOT = Path(__file__).resolve().parents[1]
doc = json.loads((ROOT / "data/kb/defects/marea.json").read_text(encoding="utf-8"))

# Reference texts per symptom: titles + spoken forms, all in Italian and English only.
refs, owner = [], []
for s in doc["symptoms"]:
    for t in [s["symptom_en"], s["symptom_it"]] + s["spoken_forms"]:
        refs.append(t)
        owner.append(s["id"])

TESTS = [
    # (language, sentence, expected symptom)
    ("it", "il caffè esce in maniera debole, è un po' annacquato", "marea-weak-coffee"),
    ("it", "la macchina stamattina è rimasta gelata, non va in temperatura", "marea-no-heat"),
    ("it", "esce acqua tutto intorno al manico quando faccio il caffè", "marea-group-leak"),
    ("en", "ze coffee she come out sin, no taste, run very quick", "marea-weak-coffee"),
    ("en", "when I take off the handle after the coffee it explodes everywhere", "marea-spits-end-of-shot"),
    ("en", "milk is not foaming anymore, the steam is very poor", "marea-steam-weak-or-dripping"),
    ("de", "Der Kaffee ist wässrig und läuft viel zu schnell durch", "marea-weak-coffee"),
    ("de", "Die Maschine wird nicht mehr heiß, der Kessel bleibt kalt", "marea-no-heat"),
    ("de", "Am Siebträger tropft Wasser heraus, wenn ich einen Kaffee mache", "marea-group-leak"),
    ("es", "el café sale aguado y muy rápido, sin crema", "marea-weak-coffee"),
    ("es", "la máquina no carga agua y suena una alarma de nivel", "marea-level-alarm"),
    ("es", "un botón ya no responde y las dosis salen mal", "marea-doses-and-buttons"),
    ("tr", "kahve çok sulu ve hızlı akıyor", "marea-weak-coffee"),
    ("tr", "makine ısınmıyor, kazan soğuk kalıyor", "marea-no-heat"),
    ("tr", "buhar çubuğu kapalıyken damlatıyor", "marea-steam-weak-or-dripping"),
    ("fr", "la machine siffle quand elle chauffe le matin", "marea-hiss-at-startup"),
    ("fr", "la pompe fait du bruit et la pression ne monte pas", "marea-pump-pressure-low"),
    ("zh", "咖啡很淡，像水一样，流得太快", "marea-weak-coffee"),
    ("zh", "机器不加热，锅炉是冷的", "marea-no-heat"),
    ("pt", "a máquina está completamente morta, não acende nenhuma luz", "marea-machine-dead"),
    # small talk that must NOT match anything
    ("en", "good morning, this is Jonas calling from Cafe Berlin", None),
    ("it", "buongiorno, la chiamo da Amburgo, mi sente bene?", None),
    ("de", "können Sie mir die Rechnung per E-Mail schicken?", None),
]

for model_name in ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",):
    t0 = time.perf_counter()
    model = TextEmbedding(model_name)
    R = np.array(list(model.embed(refs)))
    R /= np.linalg.norm(R, axis=1, keepdims=True)
    load = time.perf_counter() - t0
    ok = 0
    times = []
    rows = []
    for lang, text, expected in TESTS:
        t1 = time.perf_counter()
        v = np.array(list(model.embed([text])))[0]
        times.append(time.perf_counter() - t1)
        v /= np.linalg.norm(v)
        sims = R @ v
        best = int(np.argmax(sims))
        rows.append((lang, expected, owner[best], float(sims[best]), text))
    print(f"{model_name}: loaded in {load:.1f}s, {1000 * sum(times) / len(times):.0f} ms per sentence\n")
    for thr in (0.45, 0.50, 0.55):
        good = sum(1 for _, exp, got, s, _ in rows if (got if s >= thr else None) == exp)
        print(f"  threshold {thr}: {good}/{len(rows)} correct")
    print()
    for lang, exp, got, s, text in rows:
        flag = "OK " if (got if s >= 0.50 else None) == exp else "XX "
        print(f"  {flag}{lang} {s:.2f} {got:32s} <- {text[:70]}")
