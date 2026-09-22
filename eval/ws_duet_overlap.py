"""Reproduces the operator's complaint: an "operator" voice (Windows Zira, English) speaks through the
microphone path, and the recorded German customer line is clicked IMMEDIATELY after, with no pause.
Prints what the assistant attributed to whom."""
import asyncio
import json
import subprocess
import sys
import wave
from pathlib import Path

import miniaudio
import websockets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "spike_audio"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
OPERATOR_LINES = [
    "Sereni service, good morning, this is Marco speaking. What is the problem?",
    "Okay, since when do you have this problem, and which machine is it?",
    "I understand. How long does a double shot take, from the button until it stops?",
]
CUSTOMER_LINES = [1, 2, 3, 4]      # clip numbers of samples/duet/jonas-marea


def zira(text: str, name: str) -> bytes:
    raw = OUT / f"{name}_raw.wav"
    txt = OUT / f"{name}.txt"
    txt.write_text(text, encoding="utf-8")
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.SelectVoice('Microsoft Zira Desktop'); $s.SetOutputToWaveFile('{raw}'); "
          f"$s.Speak([IO.File]::ReadAllText('{txt}', [Text.Encoding]::UTF8)); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    dec = miniaudio.decode_file(str(raw), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=16000)
    return bytes(dec.samples)


async def main() -> None:
    op = [zira(t, f"op{i}") for i, t in enumerate(OPERATOR_LINES)]
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/call?source=duet:jonas-marea&lang=it", max_size=None) as ws:
        done = asyncio.Event()

        async def send_mic(pcm: bytes):
            step = 1600
            for i in range(0, len(pcm), step):
                await ws.send(pcm[i:i + step].ljust(step, b"\x00"))
                await asyncio.sleep(0.05)

        async def driver():
            await asyncio.sleep(2)
            for i, n in enumerate(CUSTOMER_LINES):
                if i < len(op):
                    await send_mic(op[i])                        # operator talks...
                done.clear()
                await ws.send(json.dumps({"type": "control", "action": "play_line", "n": n}))   # ...customer clicked at once
                await done.wait()
            await send_mic(op[-1])
            await asyncio.sleep(3)
            await ws.send(json.dumps({"type": "control", "action": "end_call"}))

        asyncio.create_task(driver())
        async for raw in ws:
            ev = json.loads(raw)
            if ev["type"] == "duet" and ev["state"] == "done":
                done.set()
            elif ev["type"] == "turn" and ev["final"]:
                print(f"[{ev['role']:8s}|{ev.get('speaker')}|x{ev.get('merged', 1)}] {ev['text']}")
            elif ev["type"] == "summary":
                print("DIARIZZAZIONE:", ev["summary"].get("diarization_check"))
                return
            elif ev["type"] == "error":
                print("!!", ev["text"])


asyncio.run(main())
