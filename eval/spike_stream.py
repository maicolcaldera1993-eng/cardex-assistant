"""Spike: stream a 16 kHz PCM wav to AssemblyAI Streaming v3 at real-time pace and
print the final turns with latency, with or without keyterms + prompt.

Usage:
  .venv/Scripts/python eval/spike_stream.py eval/spike_audio/en_de_katja.wav --config bare
  .venv/Scripts/python eval/spike_stream.py eval/spike_audio/en_de_katja.wav --config keyterms

Cost: billed on session duration; each file is ~60 s.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import wave
from pathlib import Path
from urllib.parse import urlencode

import websockets
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
API_KEY = os.environ["ASSEMBLYAI_API_KEY"]
WS = "wss://streaming.assemblyai.com/v3/ws"
CHUNK_MS = 50

KEYTERMS = [
    "Marea 2", "Marea 2 Plus", "Marea 2 Evo", "Giglio 1", "Giglio 1 Plus",
    "Onda MB2", "Onda MB3", "Onda MB2 Evo", "Monda 65", "Monda 65 Digit", "Vaniglia",
    "Sereni", "Cardex",
    "GE-2140", "GE-2150", "GE-2410", "CA-1180", "EL-3010", "ID-4010", "VA-5015", "MC-7010",
    "group gasket", "shower screen", "heating element", "control board", "steam valve",
    "guarnizione sottocoppa", "doccetta", "resistenza", "centralina", "pompa", "macine",
    "portafiltro", "burrs", "probe alarm", "sonda livello",
]

PROMPT = (
    "Spare-parts help desk call of Sereni, an Italian espresso machine manufacturer. "
    "Models are Marea, Giglio, Onda and Monda, with a Vaniglia edition; customers are foreign and "
    "pronounce these Italian names with an English accent. Part codes are two letters, a dash and four digits, "
    "for example GE-2140, spoken as letters and numbers. Conversation in English or Italian."
)


def configs(name: str) -> dict:
    base = {"sample_rate": 16000, "speech_model": "universal-3-5-pro", "format_turns": "false",
            "language_codes": json.dumps(["en", "it"])}
    if name == "bare":
        return base
    if name == "keyterms":
        return {**base, "keyterms_prompt": json.dumps(KEYTERMS)}
    if name == "keyterms+prompt":
        return {**base, "keyterms_prompt": json.dumps(KEYTERMS), "prompt": PROMPT}
    raise SystemExit(f"unknown config {name}")


async def run(path: Path, config: str, verbose: bool) -> list[dict]:
    params = configs(config)
    url = f"{WS}?{urlencode(params)}"
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2, "need 16k mono pcm16"
        pcm = w.readframes(w.getnframes())
    chunk = 16000 * 2 * CHUNK_MS // 1000
    turns: list[dict] = []
    t0 = time.perf_counter()
    sent_seconds = 0.0

    async with websockets.connect(url, additional_headers={"Authorization": API_KEY}, max_size=None) as ws:
        async def sender():
            nonlocal sent_seconds
            for i in range(0, len(pcm), chunk):
                await ws.send(pcm[i:i + chunk])
                sent_seconds = (i + chunk) / 32000
                await asyncio.sleep(CHUNK_MS / 1000)
            await asyncio.sleep(1.0)
            await ws.send(json.dumps({"type": "Terminate"}))

        async def receiver():
            async for raw in ws:
                msg = json.loads(raw)
                t = msg.get("type")
                if t == "Begin":
                    print(f"  session {msg['id']}")
                elif t == "Turn":
                    if msg.get("end_of_turn"):
                        now = time.perf_counter() - t0
                        last_word_end = max((w_.get("end", 0) for w_ in msg.get("words", [])), default=0) / 1000
                        latency = now - last_word_end
                        turns.append({"transcript": msg["transcript"], "latency_s": round(latency, 2),
                                      "min_conf": round(min((w_.get("confidence", 1) for w_ in msg.get("words", [])), default=1), 2)})
                        print(f"  [{now:6.1f}s  lat {latency:4.2f}s  minconf {turns[-1]['min_conf']:.2f}] {msg['transcript']}")
                    elif verbose:
                        print(f"     … {msg['transcript']}")
                elif t == "Termination":
                    print(f"  terminated: audio {msg.get('audio_duration_seconds')}s, session {msg.get('session_duration_seconds')}s")
                    return
                elif t == "Error" or "error" in msg:
                    print("  ERROR", msg)
                    return

        await asyncio.gather(sender(), receiver())
    return turns


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("wav", type=Path)
    ap.add_argument("--config", default="bare", choices=["bare", "keyterms", "keyterms+prompt"])
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    print(f"{a.wav.name}  config={a.config}")
    turns = asyncio.run(run(a.wav, a.config, a.v))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps({"file": a.wav.name, "config": a.config, "turns": turns}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
