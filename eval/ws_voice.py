"""Headless customer for the AssemblyAI Voice Agent mode: does what the browser does (two sockets, relays
transcripts and tool calls to our server, tool results back to the agent) and speaks with a synthetic voice.
Costs agent minutes (about 4.50 $/h).

The customer answers what the agent actually asked: each scenario is a list of (pattern, line) rules in the order of
a good call; after each agent turn the first unused rule whose pattern matches what the agent just said is spoken.
A confirmation question nobody scripted gets "Yes, that's correct."; when the agent asks "anything else?" the
customer says goodbye. The call ends when the agent hangs up, and the script prints what the work order says.

    .venv/Scripts/python eval/ws_voice.py                 # Dave, Chicago
    .venv/Scripts/python eval/ws_voice.py 8000 lena
"""
import asyncio
import base64
import hashlib
import json
import re
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
WAIT_S = 1.5              # the agent has finished when no new reply or tool call starts for this long
TIMEOUT_S = 420           # the whole call; a scripted call takes 4-5 minutes

OPENING = r"."            # the agent's greeting: anything it says first
ANYTHING_ELSE = r"anything else|something else|qualcos'altro|altro per lei|posso aiutarla in altro"
AGENT_GOODBYE = r"\b(goodbye|bye|have a (good|great|nice) day|arrivederci|buona giornata)\b"
CONFIRMATION = r"\b(correct|right|confirm|is that|am i|conferm|giusto|corretto)\b"

SCENARIOS = {
    "dave": ("en-US-GuyNeural", "en", [
        (OPENING, "Hi, this is Dave from Espresso Corner in Chicago. We have the Marea 2, the two group. Since this "
                  "morning the machine stays cold, the pressure gauge is at zero, no steam."),
        (r"serial|rating plate|number on the", "The serial number is zero four one, three zero two."),
        # one sentence per answer: a pause at a full stop lets the agent answer half of it
        (r"light|touchpad|alarm", "Yes, the lights and the buttons are on and there is no alarm, but it is cold."),
        (r"red button|reset|rear panel", "Okay, I found the red button, I pressed it and waited ten minutes, but it is still cold."),
        (r"click", "Yes, I hear the click when I switch it on, but there is no heat."),
        (r"volt", "Yes, correct, one hundred ten volts, the American version."),
        (r"replace|element", "How much will that cost me in total, and when do the parts arrive?"),
        (r"total|working days|convert", "Okay, that's fine, let's do it. When can we have the video call?"),
        (r"monday|tuesday|wednesday|thursday|friday|slot|available", "Yes, that works for me, please book it."),
        (r"e-?mail|address", "Yes, that email is correct."),
        (r"order|go ahead|proceed|shall i", "Yes, please order the parts."),
    ], "Yes, that's correct.", "No, that's all. Thank you, goodbye."),
    "lena": ("de-DE-KatjaNeural", "en", [
        (OPENING, "Hello, this is Lena from Kaffeehaus Nord in Berlin, about our Marea 2 Plus. The steam is very "
                  "weak, foaming the milk takes forever."),
        (r"serial|rating plate|number on the", "The serial is zero four eight, five three zero."),
        (r"drip|weak steam|which", "It is weak steam. It does not drip."),
        (r"needle|bar|gauge|pressure", "The needle is at one point two."),
        (r"tip|unscrew|holes|tablet", "I did it, the holes were closed with milk. Now the steam is strong again. It's fixed."),
    ], "Yes, that's right.", "No, thank you, that's all. Goodbye."),
    "mario": ("it-IT-DiegoNeural", "it", [      # Italian customer, Italian agent: the level alarm
        (OPENING, "Buongiorno, sono Mario del Bar Centrale di Lucca. Abbiamo la Marea 2. La macchina non carica "
                  "l'acqua, la spia del livello lampeggia e la pompa va sempre."),
        (r"matricola|numero di serie|targhetta", "La matricola è zero quattro uno, uno otto otto."),
        (r"rubinetto|flusso|acqua calda", "Sì, il rubinetto sotto il banco è aperto, e l'acqua calda esce bene, piena."),
        (r"clic|click|elettrovalvola", "Sì, sento un clic dietro, ma non carica."),
        (r"sonda|svit|chiave", "L'ho svitata e pulita, era bianca di calcare. Adesso la caldaia è piena, funziona."),
    ], "Sì, esatto.", "No, grazie, è tutto. Arrivederci."),
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


class Customer:
    """Picks the line that answers what the agent just said."""

    def __init__(self, rules, confirm_line, goodbye_line):
        self.rules, self.confirm_line, self.goodbye_line = list(rules), confirm_line, goodbye_line
        self.said_goodbye = False

    def reply(self, agent_text: str) -> str | None:
        t = agent_text.lower()
        if self.said_goodbye:
            return None
        if re.search(ANYTHING_ELSE, t):
            self.said_goodbye = True
            return self.goodbye_line
        if re.search(AGENT_GOODBYE, t):
            return None                                      # the agent is closing: nothing to answer
        # the agent's last question decides ("booked for Monday... is that email still correct?" is about the email)
        questions = [q for q in re.split(r"(?<=[.?!])\s+", t) if q.endswith("?")]
        for scope in ([questions[-1]] if questions else []) + [t]:
            for k, (pattern, line) in enumerate(self.rules):
                if re.search(pattern, scope):
                    del self.rules[k]
                    return line
        if "?" in agent_text and re.search(CONFIRMATION, t):
            return self.confirm_line
        if "?" in agent_text:
            print(f"   !! no scripted answer to: {agent_text[-160:]}")
        return None


async def main() -> None:
    voice, lang, rules, confirm_line, goodbye_line = SCENARIOS[WHO]
    customer = Customer(rules, confirm_line, goodbye_line)
    agent = httpx.get(f"http://127.0.0.1:{PORT}/api/voice/agent", params={"lang": lang}, timeout=60).json()
    # the call is opened first, as the page does: the server gives Voice Agent tokens only to an open call
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/call?source=voice&lang=en", max_size=None) as ours:
        token = httpx.get(f"http://127.0.0.1:{PORT}/api/voice/token", timeout=30).json()["token"]
        agent_ws = await websockets.connect(f"wss://agents.assemblyai.com/v1/ws?token={token}", max_size=None)
        await agent_ws.send(json.dumps({"type": "session.update", "session": agent["session"]}))
        step = RATE * 2 * CHUNK_MS // 1000
        talking = False
        done = asyncio.Event()
        gate = {"last": None, "pending": []}      # tool results only when the reply is done (AssemblyAI docs)
        heard = []                                # what the agent said since the customer last spoke
        closing = asyncio.Event()                 # end_call accepted: hang up after the agent's last reply, as the page does
        last_reply = {"started": False}           # a reply started after end_call was accepted (the goodbye)

        async def flush():
            if gate["last"] == "reply.done":
                while gate["pending"]:
                    await agent_ws.send(json.dumps(gate["pending"].pop(0)))

        async def speak(text: str):
            nonlocal talking
            pcm = await clip(text, voice)
            print(f"[customer] {text}")
            heard.clear()
            talking = True
            for i in range(0, len(pcm), step):
                await agent_ws.send(json.dumps({"type": "input.audio", "audio": base64.b64encode(pcm[i:i + step].ljust(step, b"\x00")).decode()}))
                await asyncio.sleep(CHUNK_MS / 1000)
            talking = False

        async def answer_later():
            await asyncio.sleep(WAIT_S)
            line = customer.reply(" ".join(heard))
            if line:
                await speak(line)

        async def silence():
            try:
                while not done.is_set():
                    if not talking:
                        await agent_ws.send(json.dumps({"type": "input.audio", "audio": base64.b64encode(b"\x00" * step).decode()}))
                    await asyncio.sleep(CHUNK_MS / 1000)
            except websockets.ConnectionClosed:
                return

        async def hang_up(after: float = 3):
            await asyncio.sleep(after)
            try:
                await agent_ws.send(json.dumps({"type": "session.end"}))
            except websockets.ConnectionClosed:
                pass

        async def from_ours():
            try:
                async for raw in ours:
                    ev = json.loads(raw)
                    if ev["type"] == "tool_result":
                        gate["pending"].append({"type": "tool.result", "call_id": ev["call_id"], "result": ev["result"], "is_error": False})
                        await flush()
                        print(f"    <- {ev['name']}: {ev['result'][:160]}")
                        if ev.get("end"):
                            closing.set()
                            asyncio.create_task(hang_up(15))       # reserve, if no reply follows
                    elif ev["type"] == "hangup":
                        print("    ## hangup after the goodbye")
                        asyncio.create_task(hang_up())
                    elif ev["type"] == "diagnosis":
                        print(f"    ## {ev['symptom']} -> {'done ' + ev['outcome'] if ev['done'] else 'step ' + ev['step']['id']}")
                    elif ev["type"] == "agent" and ev["text"].startswith(("Booked:", "Prenotato:", "Note for", "Nota per")):
                        print(f"    ## {ev['text']}")
                    elif ev["type"] == "summary":
                        s = ev["summary"]
                        print("== summary:", s["outcome"], "| booking:", (s.get("booking") or {}).get("label"),
                              "| confirmed:", [p["code"] for p in s["parts_confirmed"]],
                              "| proposed:", [p["code"] for p in s["parts_proposed"]], "| notes:", s.get("notes"))
                        done.set()
                        return
            except websockets.ConnectionClosed:
                done.set()

        async def deadline():
            await asyncio.sleep(TIMEOUT_S)
            print(f"   !! no end after {TIMEOUT_S} s: hanging up")
            await hang_up()

        asyncio.create_task(silence())
        asyncio.create_task(from_ours())
        asyncio.create_task(deadline())
        pending_answer = None
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
                    heard.append(m["text"])
                elif t == "tool.call":
                    print(f"    -> {m['name']} {json.dumps(m.get('arguments') or {})[:120]}")
                    await ours.send(json.dumps({"type": "control", "action": "tool", "call_id": m["call_id"], "name": m["name"], "arguments": m.get("arguments") or {}}))
                elif t in ("reply.started", "input.speech.started"):
                    gate["last"] = t
                    if t == "reply.started" and closing.is_set():
                        last_reply["started"] = True
                if t == "reply.done":
                    gate["last"] = t
                    if m.get("status") == "interrupted":
                        gate["pending"].clear()
                    else:
                        await flush()
                    if last_reply["started"]:
                        asyncio.create_task(hang_up(2))           # the goodbye has been said
                    # answer only once the agent has really finished: a tool call or a new reply within WAIT_S cancels it
                    if m.get("status") != "interrupted" and not talking:
                        if pending_answer and not pending_answer.done():
                            pending_answer.cancel()
                        pending_answer = asyncio.create_task(answer_later())
                elif t in ("tool.call", "reply.audio") and pending_answer and not pending_answer.done() and not talking:
                    pending_answer.cancel()
                    pending_answer = None
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
