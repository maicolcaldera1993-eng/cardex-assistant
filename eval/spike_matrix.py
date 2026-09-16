"""Runs spike_stream over every spike audio file and configuration, 3 sessions at a
time, then prints a comparison table of recognised models and codes."""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from spike_stream import run  # noqa: E402

AUDIO = Path(__file__).parent / "spike_audio"
RESULTS = Path(__file__).parent / "spike_results"
CONFIGS = ["bare", "keyterms", "keyterms+prompt"]

MODELS = {"Marea 2 Plus": r"marea\s*2\s*plus", "Giglio 1 Plus": r"giglio\s*1\s*plus",
          "Monda 65 Digit": r"monda\s*65\s*digit", "Onda MB2": r"\bonda\s*mb\s*2", "Vaniglia": r"vaniglia"}
CODES = ["GE-2140", "GE-2150", "CA-1180", "EL-3010", "ID-4010", "VA-5015", "MC-7010", "GE-2410"]


def code_found(text: str, code: str) -> bool:
    letters, digits = code.split("-")
    compact = re.sub(r"[\s\-\.]", "", text).upper()
    return (letters + digits) in compact


async def main() -> None:
    files = sorted(AUDIO.glob("*.wav"))
    sem = asyncio.Semaphore(3)
    rows = {}

    async def one(f: Path, cfg: str):
        out = RESULTS / f"{f.stem}.{cfg}.json"
        if out.exists():
            turns = json.loads(out.read_text(encoding="utf-8"))["turns"]
        else:
            async with sem:
                print(f"--- {f.name} / {cfg}")
                turns = await run(f, cfg, False)
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps({"file": f.name, "config": cfg, "turns": turns}, indent=2, ensure_ascii=False), encoding="utf-8")
        text = " ".join(t["transcript"] for t in turns)
        rows[(f.stem, cfg)] = {
            "models": {m: bool(re.search(p, text, re.I)) for m, p in MODELS.items()},
            "codes": {c: code_found(text, c) for c in CODES},
            "text": text,
        }

    await asyncio.gather(*(one(f, c) for f in files for c in CONFIGS))

    print("\n| voce | config | modelli | codici | Onda? | dettagli mancanti |")
    print("|---|---|---|---|---|---|")
    for f in files:
        for cfg in CONFIGS:
            r = rows[(f.stem, cfg)]
            miss = [m for m, ok in r["models"].items() if not ok] + [c for c, ok in r["codes"].items() if not ok]
            print(f"| {f.stem} | {cfg} | {sum(r['models'].values())}/5 | {sum(r['codes'].values())}/8 | "
                  f"{'sì' if r['models']['Onda MB2'] else 'no'} | {', '.join(miss)} |")
    (RESULTS / "summary.json").write_text(json.dumps({f"{k[0]}|{k[1]}": v for k, v in rows.items()}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
