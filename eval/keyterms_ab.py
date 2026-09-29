"""What the product's listening set-up buys, measured on the final product (29 Sept): the six accented recordings of
the 16 September spike (each names 5 machines and 8 part codes) are streamed into AssemblyAI Voice Agent sessions
configured exactly as Cardex does ("product": key terms + transcription prompt + language codes + max_accuracy) and
the same without key terms and prompt ("bare"). Only what the agent heard is scored (transcript.user), with the same
rules as the spike. Costs a few minutes of agent time; the API key is read from .env and never printed.

    .venv/Scripts/python eval/keyterms_ab.py          # results in eval/keyterms_ab_results.json
"""
import asyncio
import base64
import copy
import json
import os
import re
import sys
from pathlib import Path

import miniaudio
import websockets
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from app.core.vocabulary import VocabularyManager  # noqa: E402
from app.voice.agent import session_config, session_token  # noqa: E402

AUDIO = ROOT / "eval" / "spike_audio"
OUT = ROOT / "eval" / "keyterms_ab_results.json"
RATE, STEP = 24000, 2400                              # 50 ms of 16-bit mono
MODELS = {"Marea 2 Plus": r"marea\s*(2|two)\s*plus", "Giglio 1 Plus": r"giglio\s*(1|one)\s*plus",
          "Monda 65 Digit": r"monda\s*(65|sixty[\s-]*five)\s*digit", "Onda MB2": r"\bonda\s*mb\s*(2|two)",
          "Vaniglia": r"vaniglia"}
CODES = ["GE-2140", "GE-2150", "CA-1180", "EL-3010", "ID-4010", "VA-5015", "MC-7010", "GE-2410"]


def code_found(text: str, code: str) -> bool:
    letters, digits = code.split("-")
    return (letters + digits) in re.sub(r"[\s\-\.]", "", text).upper()


def config(kind: str) -> dict:
    cfg = session_config(VocabularyManager().keyterms, "en")
    if kind == "bare":
        cfg = copy.deepcopy(cfg)
        cfg["input"].pop("keyterms", None)
        cfg["input"].pop("transcription_prompt", None)
    cfg["tools"] = []                                  # listening only: no tool may interrupt the recording
    return cfg


async def listen(wav: Path, kind: str) -> str:
    pcm = miniaudio.decode_file(str(wav), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1,
                                sample_rate=RATE).samples.tobytes()
    token = await session_token(os.environ["ASSEMBLYAI_API_KEY"])
    heard: list[str] = []
    async with websockets.connect(f"wss://agents.assemblyai.com/v1/ws?token={token}", max_size=None) as ws:
        await ws.send(json.dumps({"type": "session.update", "session": config(kind)}))

        async def receive():
            async for raw in ws:
                m = json.loads(raw)
                if m["type"] == "transcript.user":
                    heard.append(m["text"])
                elif m["type"] in ("session.error", "error"):
                    print("   !!", wav.stem, kind, m)

        reader = asyncio.create_task(receive())
        await asyncio.sleep(2)                          # session.ready and the greeting
        audio = pcm + b"\x00" * (RATE * 2 * 4)          # four seconds of silence to close the last turn
        for i in range(0, len(audio), STEP):
            await ws.send(json.dumps({"type": "input.audio", "audio": base64.b64encode(audio[i:i + STEP].ljust(STEP, b"\x00")).decode()}))
            await asyncio.sleep(STEP / 2 / RATE)
        await asyncio.sleep(3)
        await ws.send(json.dumps({"type": "session.end"}))
        try:
            await asyncio.wait_for(reader, 10)
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            reader.cancel()
    return " ".join(heard)


async def main() -> None:
    manifest = json.loads((AUDIO / "manifest.json").read_text(encoding="utf-8"))
    results = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    sem = asyncio.Semaphore(2)

    async def one(item: dict, kind: str):
        key = f"{Path(item['file']).stem}|{kind}"
        if key in results:
            return
        async with sem:
            print("---", key)
            text = await listen(AUDIO / item["file"], kind)
        results[key] = {"models": {m: bool(re.search(p, text, re.I)) for m, p in MODELS.items()},
                        "codes": {c: code_found(text, c) for c in CODES}, "text": text}
        OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    await asyncio.gather(*(one(item, kind) for item in manifest for kind in ("product", "bare")))
    print("\n| voice | config | models | codes | missed |")
    print("|---|---|---|---|---|")
    totals = {}
    for item in manifest:
        for kind in ("product", "bare"):
            r = results[f"{Path(item['file']).stem}|{kind}"]
            m, c = sum(r["models"].values()), sum(r["codes"].values())
            t = totals.setdefault(kind, [0, 0, 0, 0])
            t[0] += m; t[1] += len(r["models"]); t[2] += c; t[3] += len(r["codes"])  # noqa: E702
            missed = [k for k, ok in r["models"].items() if not ok] + [k for k, ok in r["codes"].items() if not ok]
            print(f"| {Path(item['file']).stem} | {kind} | {m}/5 | {c}/8 | {', '.join(missed)} |")
    for kind, (m, mt, c, ct) in totals.items():
        print(f"TOTAL {kind}: models {m}/{mt}, codes {c}/{ct}")


if __name__ == "__main__":
    asyncio.run(main())
