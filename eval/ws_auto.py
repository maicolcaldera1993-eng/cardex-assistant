"""Headless customer for the automatic assistant: a synthetic voice (Edge TTS) says each line of a scenario
into the call, waits for the assistant to answer (its 'speak' events), and prints the whole dialogue.
No microphone, no browser: the audio goes straight into the websocket like the browser's worklet would.

    .venv/Scripts/python eval/ws_auto.py                 # Dave, Chicago: no heat, 110 V, out of warranty
    .venv/Scripts/python eval/ws_auto.py 8000 lena       # another scenario from SCENARIOS
"""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import miniaudio
import websockets

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
WHO = sys.argv[2] if len(sys.argv) > 2 else "dave"
CACHE = Path(__file__).resolve().parent / "spike_audio" / "auto"     # ignored by git
CHUNK_MS = 50

SCENARIOS = {
    "dave": ("en-US-GuyNeural", [
        "Hi, this is Dave from Espresso Corner in Chicago. We have the Marea 2, the two group. Since this morning the machine stays cold, the pressure gauge is at zero, no steam.",
        "Yes, everything is on, the lights, the buttons. No alarm. But it is cold.",
        "Okay, I found the red button, I pressed it. Ten minutes later it is still cold.",
        "Yes, I hear the click when I switch on. But no heat.",
        "It is one hundred ten volts, the American version.",
        "The serial number is zero four one, three zero two.",
        "Yes, please book it.",
        "No, that's all. Thank you, goodbye.",
    ]),
    "lena": ("de-DE-KatjaNeural", [
        "Hello, this is Lena from Kaffeehaus Nord in Berlin, about our Marea 2 Plus. The steam is very weak, foaming the milk takes forever.",
        "Weak steam, it does not drip.",
        "The needle is at one point two.",
        "I did it, the holes were closed with milk. Now the steam is strong again. Fixed.",
        "No, thank you, goodbye.",
    ]),
}


async def clip(text: str, voice: str) -> bytes:
    """16 kHz mono PCM16 for one line, cached on disk."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha1(f"{voice}|{text}".encode()).hexdigest()[:16] + ".raw")
    if not f.exists():
        import edge_tts
        mp3 = f.with_suffix(".mp3")
        await edge_tts.Communicate(text, voice, rate="-6%").save(str(mp3))
        dec = miniaudio.decode_file(str(mp3), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=16000)
        f.write_bytes(dec.samples.tobytes())
        mp3.unlink()
    return f.read_bytes()


async def main() -> None:
    voice, lines = SCENARIOS[WHO]
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/call?source=auto&lang=it", max_size=None) as ws:
        spoken = asyncio.Event()          # set when the assistant has finished a sentence
        queue = list(lines)
        talking = False
        step = 16000 * 2 * CHUNK_MS // 1000

        async def silence():
            # like an open microphone in a quiet room: the stream never stops, so the session never times out
            try:
                while True:
                    if not talking:
                        await ws.send(b"\x00" * step)
                    await asyncio.sleep(CHUNK_MS / 1000)
            except websockets.ConnectionClosed:
                return

        async def speaker():
            nonlocal talking
            # after every assistant sentence: "play" it (wait), tell the server, then say the next customer line
            while queue:
                await spoken.wait()
                spoken.clear()
                text = queue.pop(0)
                pcm = await clip(text, voice)
                print(f"[customer] {text}")
                talking = True
                for i in range(0, len(pcm), step):
                    await ws.send(pcm[i:i + step].ljust(step, b"\x00"))   # AssemblyAI wants 50-1000 ms per chunk
                    await asyncio.sleep(CHUNK_MS / 1000)
                talking = False

        asyncio.create_task(silence())
        asyncio.create_task(speaker())
        async for raw in ws:
            ev = json.loads(raw)
            t = ev["type"]
            if t == "speak":
                print(f"[assistant] {ev['text']}")
                await asyncio.sleep(min(ev["seconds"], 6.0))
                await ws.send(json.dumps({"type": "control", "action": "spoken"}))
                spoken.set()
            elif t == "turn" and ev["final"]:
                print(f"    (heard: {ev['text']})")
            elif t == "diagnosis":
                print(f"    ## {ev['symptom']} -> {'done ' + ev['outcome'] if ev['done'] else 'step ' + ev['step']['id']}")
            elif t == "machine_record":
                print(f"    ## machine {ev['serial']} {ev['model']} warranty={ev['in_warranty']}")
            elif t == "agent" and ("Prenotato" in ev["text"] or "Booked" in ev["text"]):
                print(f"    ## {ev['text']}")
            elif t == "summary":
                s = ev["summary"]
                print("== summary:", s["outcome"], "| booking:", (s.get("booking") or {}).get("label"), "| parts:", [p["code"] for p in s["parts_proposed"] + s["parts_confirmed"]])
                return
            elif t == "error":
                print("   !!", ev["text"])


asyncio.run(main())
