"""Headless customer for the AssemblyAI Voice Agent mode: does what the browser does (two sockets, relays
transcripts and tool calls to our server, tool results back to the agent) and speaks the scenario lines with a
synthetic voice, one after each agent reply. Costs agent minutes (about 4.50 $/h).

    .venv/Scripts/python eval/ws_voice.py                 # Dave, Chicago
    .venv/Scripts/python eval/ws_voice.py 8000 lena
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
WHO = sys.argv[2] if len(sys.argv) > 2 else "dave"
CACHE = Path(__file__).resolve().parent / "spike_audio" / "voice"     # ignored by git
RATE = 24000
CHUNK_MS = 50

SCENARIOS = {
    "dave": ("en-US-GuyNeural", [
        "Hi, this is Dave from Espresso Corner in Chicago. We have the Marea 2, the two group. Since this morning the machine stays cold, the pressure gauge is at zero, no steam.",
        "The serial number is zero four one, three zero two.",
        "Yes, everything is on, the lights, the buttons. No alarm. But it is cold.",
        "Okay, I found the red button, I pressed it. Ten minutes later it is still cold.",
        "Yes, I hear the click when I switch on. But no heat.",
        "It is one hundred ten volts, the American version.",
        "How much will that cost me in total, and when do the parts arrive?",
        "Yes, please book it.",
        "No, that's all. Thank you, goodbye.",
    ]),
    "mario": ("it-IT-DiegoNeural", [          # Italian customer, Italian agent (lang=it): Carmen's level alarm
        "Buongiorno, sono Mario del Bar Centrale di Lucca. Abbiamo la Marea 2. La macchina non carica l'acqua, la spia del livello lampeggia e la pompa va sempre.",
        "La matricola è zero quattro uno, uno otto otto.",
        "Sì, il rubinetto sotto il banco è aperto, e l'acqua calda esce bene, piena.",
        "Sì, sento un clic dietro, ma non carica.",
        "L'ho svitata. La punta è tutta bianca di calcare.",
        "L'ho pulita e rimessa. Adesso la pompa si è fermata e la caldaia è piena, funziona.",
        "No, grazie, è tutto. Arrivederci.",
    ]),
    "lena": ("de-DE-KatjaNeural", [
        "Hello, this is Lena from Kaffeehaus Nord in Berlin, about our Marea 2 Plus. The steam is very weak, foaming the milk takes forever.",
        "The serial is zero four eight, five three zero.",
        "Weak steam, it does not drip.",
        "The needle is at one point two.",
        "I did it, the holes were closed with milk. Now the steam is strong again. Fixed.",
        "No, thank you, goodbye.",
    ]),
}


async def clip(text: str, voice: str) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha1(f"{voice}|{text}|{RATE}".encode()).hexdigest()[:16] + ".raw")
    if not f.exists():
        import edge_tts
        mp3 = f.with_suffix(".mp3")
        await edge_tts.Communicate(text, voice, rate="-6%").save(str(mp3))
        dec = miniaudio.decode_file(str(mp3), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=RATE)
        f.write_bytes(dec.samples.tobytes())
        mp3.unlink()
    return f.read_bytes()


async def main() -> None:
    voice, lines = SCENARIOS[WHO]
    queue = list(lines)
    lang = {"mario": "it"}.get(WHO, "en")
    agent = httpx.get(f"http://127.0.0.1:{PORT}/api/voice/agent", params={"lang": lang}, timeout=60).json()
    token = httpx.get(f"http://127.0.0.1:{PORT}/api/voice/token", timeout=30).json()["token"]
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/call?source=voice&lang=it", max_size=None) as ours, \
            websockets.connect(f"wss://agents.assemblyai.com/v1/ws?token={token}", max_size=None) as agent_ws:
        await agent_ws.send(json.dumps({"type": "session.update", "session": agent["session"]}))
        step = RATE * 2 * CHUNK_MS // 1000
        talking = False
        done = asyncio.Event()

        async def say_next():
            nonlocal talking
            if not queue:
                return
            text = queue.pop(0)
            pcm = await clip(text, voice)
            print(f"[customer] {text}")
            talking = True
            for i in range(0, len(pcm), step):
                await agent_ws.send(json.dumps({"type": "input.audio", "audio": base64.b64encode(pcm[i:i + step].ljust(step, b"\x00")).decode()}))
                await asyncio.sleep(CHUNK_MS / 1000)
            talking = False

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
                    if ev["type"] == "tool_result":
                        await agent_ws.send(json.dumps({"type": "tool.result", "call_id": ev["call_id"], "result": ev["result"], "is_error": False}))
                        print(f"    <- {ev['name']}: {ev['result'][:160]}")
                        if ev.get("end"):
                            await asyncio.sleep(3)
                            await agent_ws.send(json.dumps({"type": "session.end"}))
                    elif ev["type"] == "diagnosis":
                        print(f"    ## {ev['symptom']} -> {'done ' + ev['outcome'] if ev['done'] else 'step ' + ev['step']['id']}")
                    elif ev["type"] == "agent" and ("Prenotato" in ev["text"] or "Nota" in ev["text"]):
                        print(f"    ## {ev['text']}")
                    elif ev["type"] == "summary":
                        s = ev["summary"]
                        print("== summary:", s["outcome"], "| booking:", (s.get("booking") or {}).get("label"), "| notes:", s.get("notes"),
                              "| parts:", [p["code"] for p in s["parts_proposed"] + s["parts_confirmed"]])
                        done.set()
                        return
            except websockets.ConnectionClosed:
                done.set()

        asyncio.create_task(silence())
        asyncio.create_task(from_ours())
        speaking_task = None
        try:
            async for raw in agent_ws:
                m = json.loads(raw)
                t = m["type"]
                if t == "session.ready":
                    print("[session ready]")
                elif t == "transcript.user":
                    await ours.send(json.dumps({"type": "control", "action": "transcript", "role": "customer", "text": m["text"]}))
                    print(f"    (heard: {m['text']})")
                elif t == "transcript.agent":
                    await ours.send(json.dumps({"type": "control", "action": "transcript", "role": "agent", "text": m["text"]}))
                    print(f"[agent] {m['text']}")
                elif t == "tool.call":
                    print(f"    -> {m['name']} {json.dumps(m.get('arguments') or {})[:120]}")
                    await ours.send(json.dumps({"type": "control", "action": "tool", "call_id": m["call_id"], "name": m["name"], "arguments": m.get("arguments") or {}}))
                elif t == "reply.done":
                    # speak only once the agent has really finished: a tool call or a new reply within 1.5 s cancels it
                    if queue and m.get("status") != "interrupted" and (speaking_task is None or speaking_task.done()):
                        async def later():
                            await asyncio.sleep(1.5)
                            await say_next()
                        speaking_task = asyncio.create_task(later())
                elif t in ("tool.call", "reply.audio") and speaking_task and not speaking_task.done() and not talking:
                    speaking_task.cancel()
                    speaking_task = None
                elif t in ("session.error", "error"):
                    print("   !!", m)
                elif t == "session.ended":
                    print(f"[session ended] {m.get('audio_duration_seconds')} s of audio")
                    break
        except websockets.ConnectionClosed as e:
            print(f"[agent socket closed] code={e.code} reason={e.reason!r}")
        finally:
            await ours.send(json.dumps({"type": "control", "action": "voice_end"}))
            try:
                await asyncio.wait_for(done.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass


asyncio.run(main())
