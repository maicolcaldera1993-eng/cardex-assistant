"""Headless check of the whole loop: connects to the local server like the browser does,
asks for a sample call, prints every event, answers the diagnosis steps from a script.

    .venv/Scripts/python eval/ws_client.py dev-de-codes --answers 1,1,0,0
"""
import argparse
import asyncio
import json

import websockets


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sample")
    ap.add_argument("--answers", default="")
    ap.add_argument("--lang", default="it")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    answers = [int(x) for x in a.answers.split(",") if x]
    async with websockets.connect(f"ws://127.0.0.1:{a.port}/ws/call?source=sample:{a.sample}&lang={a.lang}", max_size=None) as ws:
        async for raw in ws:
            ev = json.loads(raw)
            t = ev["type"]
            if t == "turn":
                if ev["final"]:
                    print(f"[{ev['role']:8s}|x{ev.get('merged', 1)}] {ev['text']}")
            elif t == "clear":
                print(f"      chiaro #{ev['turn_id']}: {ev['text']}")
            elif t == "agent":
                print(f"   >> {ev['text']}")
            elif t == "parts":
                for c in ev["cards"]:
                    print(f"   [] {c['code']} {c['reason']} {c['score']} compat={c['compatible']} {c['description'][:60]}")
            elif t == "diagnosis":
                if ev["done"]:
                    print(f"   ## ESITO {ev['outcome']} {ev['parts']}")
                else:
                    print(f"   ## passo {ev['step']['id']}: {ev['step']['text'][:70]} | rami: {ev['step']['branches']}")
                    if answers:
                        await ws.send(json.dumps({"type": "control", "action": "answer_step", "branch": answers.pop(0)}))
            elif t == "summary":
                s = ev["summary"]
                print("   == RESOCONTO:", {k: s[k] for k in ("duration_s", "machine", "edition", "symptom", "outcome", "maintenance_skipped")})
            elif t == "open_doc":
                print(f"   >> DOC [{ev['kind']}] {ev['page']}#{ev['anchor']} ({ev['reason']})")
                if ev.get("highlight"):
                    print(f"        evidenzia: «{ev['highlight']}»")
            elif t == "symptom_choice":
                print("   ?? scelta tra:", [(o["title"], o["score"]) for o in ev["options"]])
            elif t in ("error", "context", "vocabulary"):
                print(f"   -- {t}: { {k: v for k, v in ev.items() if k not in ('type', 'sample')} }")


asyncio.run(main())
