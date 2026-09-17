"""FastAPI entry point: one page, one WebSocket per call, a few read-only endpoints."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from .session import CATALOG, DEFECTS, SAMPLES, VOCAB, CallSession  # noqa: E402

API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "")
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_SESSIONS", "2"))
_active = 0

app = FastAPI(title="Cardex Assistant")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "active_sessions": _active, "key_configured": bool(API_KEY)}


@app.get("/api/samples")
def samples() -> list[dict]:
    manifest = SAMPLES / "manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []


@app.get("/api/models")
def models() -> list[dict]:
    return [{"id": i, "name": n} for i, n in VOCAB.model_names.items()]


@app.get("/api/symptoms")
def symptoms(lang: str = "it") -> list[dict]:
    return [{"id": sid, "title": s[f"symptom_{lang if lang in ('it', 'en') else 'it'}"], "models": s["models"]}
            for sid, s in DEFECTS.symptoms.items()]


@app.get("/api/parts/{code}")
def part(code: str, model_id: str | None = None) -> dict:
    if not CATALOG.exists(code):
        raise HTTPException(404, "unknown part code")
    card = CATALOG.card(code, 1.0, "lookup", model_id)
    sheet = ROOT / "data" / "kb" / "parts" / f"{code}.md"
    return {"card": card.__dict__, "sheet_markdown": sheet.read_text(encoding="utf-8") if sheet.exists() else None}


@app.get("/api/manuals/{model_id}", response_class=PlainTextResponse)
def manual(model_id: str) -> str:
    f = ROOT / "data" / "kb" / "manuals" / f"{model_id}.md"
    if model_id not in VOCAB.model_names or not f.exists():
        raise HTTPException(404, "no manual for this model yet")
    return f.read_text(encoding="utf-8")


@app.websocket("/ws/call")
async def call(ws: WebSocket, source: str = "mic", lang: str = "it") -> None:
    global _active
    await ws.accept()
    if not API_KEY:
        await ws.send_json({"type": "error", "text": "ASSEMBLYAI_API_KEY is not configured on the server"})
        return await ws.close()
    if _active >= MAX_CONCURRENT:
        await ws.send_json({"type": "error", "text": "The demo is busy (max concurrent calls reached). Try again in a minute."})
        return await ws.close()
    _active += 1
    lock = asyncio.Lock()

    async def emit(event: dict) -> None:
        async with lock:
            try:
                await ws.send_json(event)
            except Exception:  # noqa: BLE001 - browser went away
                pass

    session = CallSession(API_KEY, emit, source=source, lang=lang if lang in ("it", "en") else "it")
    runner = asyncio.create_task(session.run())
    try:
        while not runner.done():
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes"):
                await session.push_audio(msg["bytes"])
            elif msg.get("text"):
                try:
                    await session.control(json.loads(msg["text"]))
                except (ValueError, KeyError):
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        await session.end()
        try:
            await asyncio.wait_for(runner, timeout=10)
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            runner.cancel()
        _active -= 1
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
