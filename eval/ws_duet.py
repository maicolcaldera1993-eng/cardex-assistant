"""Headless check of a two-voice rehearsal: plays a few recorded customer lines through the server
(no operator voice; roles are swapped after the first line so the voice counts as the customer) and prints
what the assistant does.    python eval/ws_duet.py 1,2,3,4 8000 dave-chicago"""
import asyncio
import json
import sys

import websockets

LINES = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "1,2,3,9").split(",")]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
DUET = sys.argv[3] if len(sys.argv) > 3 else "jonas-marea"


async def main() -> None:
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/call?source=duet:{DUET}&lang=it", max_size=None) as ws:
        queue = list(LINES)
        idle = None

        async def player():
            nonlocal idle
            await asyncio.sleep(2)
            first = True
            for n in queue:
                await ws.send(json.dumps({"type": "control", "action": "play_line", "n": n}))
                idle = asyncio.Event()
                await idle.wait()
                await asyncio.sleep(2.5)
                if first:      # no operator voice here: the first (only) speaker would be taken for the operator
                    await ws.send(json.dumps({"type": "control", "action": "swap_roles"}))
                    first = False
            await asyncio.sleep(3)
            await ws.send(json.dumps({"type": "control", "action": "end_call"}))

        asyncio.create_task(player())
        async for raw in ws:
            ev = json.loads(raw)
            t = ev["type"]
            if t == "duet" and ev["state"] == "done" and idle:
                idle.set()
            elif t == "turn" and ev["final"]:
                print(f"[{ev['role']:8s}|{ev['speaker']}|x{ev.get('merged', 1)}] {ev['text']}")
            elif t == "agent":
                print(f"   >> {ev['text']}")
            elif t == "parts":
                for c in ev["cards"]:
                    print(f"   [] {c['code']} {c['reason']} compat={c['compatible']}")
            elif t == "diagnosis" and not ev["done"]:
                print(f"   ## passo {ev['step']['id']}")
            elif t == "open_doc":
                print(f"   >> DOC {ev['page']}#{ev['anchor']} ({ev['reason']})")
            elif t == "summary":
                print("   == fine")
                return
            elif t == "error":
                print("   !! ", ev["text"])


asyncio.run(main())
