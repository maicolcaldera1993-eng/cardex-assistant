"""Headless check of operator practice: a synthetic OPERATOR (Edge TTS) talks to the simulated customer (Voice Agent
playing a persona); both transcripts are relayed to Cardex like the page does, and we print what Cardex does.

    .venv/Scripts/python -u eval/ws_roleplay.py 8000 klaus
"""
import asyncio
import base64
import hashlib
import json
import sys
from pathlib import Path

import httpx
import miniaudio
import websockets

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
WHO = sys.argv[2] if len(sys.argv) > 2 else "klaus"
CACHE = Path(__file__).resolve().parent / "spike_audio" / "roleplay"
RATE, CHUNK_MS = 24000, 50
VOICE = "it-IT-DiegoNeural"          # an Italian operator speaking English

OPERATOR = {
    "klaus": ["Sereni service, good morning, this is Michael. How can I help you?",
              "I'm sorry to hear that. Can you read me the serial number on the plate at the back?",
              "Thank you. Is the steam boiler switched on on the panel, is the steam icon lit?",
              "Does the display show a pressure sensor error, or does the pressure just stay at zero?",
              "What voltage is the machine, 230 or 110 volts?",
              "The steam boiler heating element has failed. It is under warranty, so there is no charge. I ship it with the gasket, and we book a video call to fit it. Is Wednesday morning okay?",
              "Perfect, it's booked. Thank you for calling, goodbye."],
}


async def clip(text: str) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha1(f"{VOICE}|{text}|{RATE}".encode()).hexdigest()[:16] + ".raw")
    if not f.exists():
        import edge_tts
        mp3 = f.with_suffix(".mp3")
        await edge_tts.Communicate(text, VOICE, rate="-6%").save(str(mp3))
        dec = miniaudio.decode_file(str(mp3), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=RATE)
        f.write_bytes(dec.samples.tobytes())
        mp3.unlink()
    return f.read_bytes()


async def main() -> None:
    lines = list(OPERATOR[WHO])
    cfg = httpx.get(f"http://127.0.0.1:{PORT}/api/voice/customer", params={"persona": WHO}, timeout=60).json()
    token = httpx.get(f"http://127.0.0.1:{PORT}/api/voice/token", timeout=30).json()["token"]
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/call?source=roleplay:{WHO}&lang=it", max_size=None) as ours, \
            websockets.connect(f"wss://agents.assemblyai.com/v1/ws?token={token}", max_size=None) as agent_ws:
        await agent_ws.send(json.dumps({"type": "session.update", "session": cfg["session"]}))
        step = RATE * 2 * CHUNK_MS // 1000
        talking = False
        done = asyncio.Event()

        async def say_next():
            nonlocal talking
            if not lines:
                return
            text = lines.pop(0)
            pcm = await clip(text)
            print(f"[operator] {text}")
            talking = True
            for i in range(0, len(pcm), step):
                await agent_ws.send(json.dumps({"type": "input.audio", "audio": base64.b64encode(pcm[i:i + step].ljust(step, b"\x00")).decode()}))
                await asyncio.sleep(CHUNK_MS / 1000)
            talking = False
            if not lines:
                await asyncio.sleep(4)
                await ours.send(json.dumps({"type": "control", "action": "end_call"}))
                await agent_ws.send(json.dumps({"type": "session.end"}))

        async def silence():
            try:
                while not done.is_set():
                    if not talking:
                        await agent_ws.send(json.dumps({"type": "input.audio", "audio": base64.b64encode(b"\x00" * step).decode()}))
                    await asyncio.sleep(CHUNK_MS / 1000)
            except websockets.ConnectionClosed:
                return

        async def from_ours():
            try:
                async for raw in ours:
                    ev = json.loads(raw)
                    if ev["type"] == "diagnosis":
                        print(f"    ## {ev['symptom']} -> {'done ' + ev['outcome'] if ev['done'] else 'step ' + ev['step']['id']}")
                    elif ev["type"] == "machine_record":
                        print(f"    ## machine {ev['serial']} {ev['model']} warranty={ev['in_warranty']}")
                    elif ev["type"] == "agent":
                        print(f"    .. {ev['text'][:120]}")
                    elif ev["type"] == "clear":
                        print(f"    (clear: {ev['text'][:120]})")
                    elif ev["type"] == "summary":
                        s = ev["summary"]
                        print("== summary:", s["symptom"], "| machine:", s["machine"], s["serial"])
                        done.set()
                        return
            except websockets.ConnectionClosed:
                done.set()

        asyncio.create_task(silence())
        asyncio.create_task(from_ours())
        await asyncio.sleep(1.5)
        asyncio.create_task(say_next())               # the operator answers the phone first
        pending = None
        try:
            async for raw in agent_ws:
                m = json.loads(raw)
                t = m["type"]
                if t == "transcript.user":
                    await ours.send(json.dumps({"type": "control", "action": "transcript", "role": "operator", "text": m["text"]}))
                elif t == "transcript.agent":
                    await ours.send(json.dumps({"type": "control", "action": "transcript", "role": "customer", "text": m["text"]}))
                    print(f"[customer] {m['text']}")
                elif t == "reply.done" and m.get("status") != "interrupted" and lines:
                    if pending is None or pending.done():
                        async def later():
                            await asyncio.sleep(1.5)
                            await say_next()
                        pending = asyncio.create_task(later())
                elif t in ("session.error", "error"):
                    print("   !!", m)
                elif t == "session.ended":
                    break
        except websockets.ConnectionClosed:
            pass
        try:
            await asyncio.wait_for(done.wait(), timeout=10)
        except asyncio.TimeoutError:
            pass


asyncio.run(main())
