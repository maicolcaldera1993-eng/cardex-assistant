"""Does the agent cut in while the customer is still talking? Measured on the final product (29 Sept): the six
accented spike recordings (about 50 s of one customer talking, with the natural pauses between sentences) are streamed
into AssemblyAI Voice Agent sessions configured as Cardex does ("product": transcription_mode max_accuracy) and the
same with the default transcription mode ("default"). Counted: replies the agent starts before the recording is over
(each one is the agent talking over a customer who has not finished), and the customer turns the speech was cut into.
Costs a few minutes of agent time; the API key is read from .env and never printed.

    .venv/Scripts/python eval/turns_ab.py          # results in eval/turns_ab_results.json
"""
import asyncio
import base64
import copy
import json
import os
import sys
import time
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
OUT = ROOT / "eval" / "turns_ab_results.json"
RATE, STEP = 24000, 2400                              # 50 ms of 16-bit mono


def config(kind: str) -> dict:
    cfg = copy.deepcopy(session_config(VocabularyManager().keyterms, "en"))
    if kind == "default":
        cfg["input"].pop("transcription_mode", None)
    cfg["tools"] = []                                  # listening and replying only
    return cfg


async def run(wav: Path, kind: str) -> dict:
    pcm = miniaudio.decode_file(str(wav), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1,
                                sample_rate=RATE).samples.tobytes()
    token = await session_token(os.environ["ASSEMBLYAI_API_KEY"])
    state = {"streaming": False, "cut_in": 0, "turns": 0}
    async with websockets.connect(f"wss://agents.assemblyai.com/v1/ws?token={token}", max_size=None) as ws:
        await ws.send(json.dumps({"type": "session.update", "session": config(kind)}))

        async def receive():
            async for raw in ws:
                m = json.loads(raw)
                if m["type"] == "reply.started" and state["streaming"]:
                    state["cut_in"] += 1                   # a reply while the customer is still talking
                elif m["type"] == "transcript.user":
                    state["turns"] += 1

        reader = asyncio.create_task(receive())
        await asyncio.sleep(6)                          # session.ready and the whole greeting
        state["streaming"] = True
        t0 = time.monotonic()
        for i in range(0, len(pcm), STEP):
            await ws.send(json.dumps({"type": "input.audio", "audio": base64.b64encode(pcm[i:i + STEP].ljust(STEP, b"\x00")).decode()}))
            await asyncio.sleep(max(0.0, t0 + (i + STEP) / 2 / RATE - time.monotonic()))
        state["streaming"] = False
        silence = base64.b64encode(b"\x00" * STEP).decode()
        for _ in range(60):                             # three seconds of silence to close the last turn
            await ws.send(json.dumps({"type": "input.audio", "audio": silence}))
            await asyncio.sleep(0.05)
        await ws.send(json.dumps({"type": "session.end"}))
        try:
            await asyncio.wait_for(reader, 10)
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            reader.cancel()
    return {"cut_in": state["cut_in"], "turns": state["turns"], "seconds": round(len(pcm) / 2 / RATE, 1)}


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
            results[key] = await run(AUDIO / item["file"], kind)
        OUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    await asyncio.gather(*(one(item, kind) for item in manifest for kind in ("product", "default")))
    print("\n| voice | config | agent cut in | customer turns | seconds |")
    print("|---|---|---|---|---|")
    totals = {}
    for item in manifest:
        for kind in ("product", "default"):
            r = results[f"{Path(item['file']).stem}|{kind}"]
            t = totals.setdefault(kind, [0, 0])
            t[0] += r["cut_in"]; t[1] += r["turns"]  # noqa: E702
            print(f"| {Path(item['file']).stem} | {kind} | {r['cut_in']} | {r['turns']} | {r['seconds']} |")
    for kind, (c, t) in totals.items():
        print(f"TOTAL {kind}: agent cut in {c} times, customer speech cut into {t} turns")


if __name__ == "__main__":
    asyncio.run(main())
