"""FastAPI entry point: one page, one WebSocket per call, a few read-only endpoints."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

import markdown  # noqa: E402

from .session import CATALOG, DEFECTS, SAMPLES, SEMANTIC, VOCAB, CallSession  # noqa: E402

API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "")
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_SESSIONS", "2"))
_active = 0

app = FastAPI(title="Cardex Assistant")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


@app.middleware("http")
async def no_cache_for_the_app_itself(request, call_next):
    """The page and its script change every day of the hackathon: never let a browser keep an old copy."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response
if (ROOT / "samples" / "duet").is_dir():
    app.mount("/duet-audio", StaticFiles(directory=ROOT / "samples" / "duet"), name="duet-audio")


@app.on_event("startup")
async def load_semantic_model() -> None:
    """The embedding model takes a few seconds to load: do it off the event loop, calls can start meanwhile."""
    asyncio.get_running_loop().run_in_executor(None, SEMANTIC.load)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "active_sessions": _active, "key_configured": bool(API_KEY), "semantic_ready": SEMANTIC.ready}


@app.get("/api/samples")
def samples() -> list[dict]:
    manifest = SAMPLES / "manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []


@app.get("/api/duets")
def duets() -> list[dict]:
    out = []
    for f in sorted((ROOT / "samples" / "duet").glob("*/script.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.append({"id": d["id"], "title_it": d["title_it"], "title_en": d["title_en"], "lines": len(d["lines"])})
    return out


@app.get("/api/tts/{key}.mp3")
def tts_audio(key: str) -> Response:
    """The automatic assistant's sentences, synthesised on demand and kept in memory."""
    from .agent.tts import TTS
    data = TTS.cache.get(key)
    if data is None:
        raise HTTPException(404)
    return Response(content=data, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


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


@app.get("/api/docs/render")
def render_doc(page: str, hl: str | None = None, lang: str = "it") -> dict:
    """A knowledge-base page as HTML, headings carrying the same anchors as the section index,
    and the sentence that matches what was said wrapped in <mark>."""
    from .data_slug import slug  # noqa: PLC0415
    kb = (ROOT / "data" / "kb").resolve()
    f = (kb / page).resolve()
    if lang == "en" and f.with_suffix(".en.md").exists():
        f = f.with_suffix(".en.md")                      # same anchors, English text
    if kb not in f.parents or f.suffix != ".md" or not f.exists():
        raise HTTPException(404, "unknown page")
    text = f.read_text(encoding="utf-8")
    if hl:
        key = hl.strip().rstrip(".:;")[:80]
        i = text.find(key[:40])
        if i >= 0:
            j = i + len(key) if text[i:i + len(key)] == key else text.find("\n", i)
            j = j if j > i else len(text)
            text = text[:i] + "<mark>" + text[i:j] + "</mark>" + text[j:]
    md = markdown.Markdown(extensions=["tables", "toc", "attr_list"], extension_configs={
        "toc": {"slugify": lambda value, sep: slug(__import__("re").sub(r"^\d+\.\s*", "", value))}})
    return {"page": page, "html": md.convert(text)}


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
                except Exception as e:  # noqa: BLE001 - a broken click must show up in the log, not vanish
                    await session.emit({"type": "error", "text": f"control {msg['text'][:80]}: {type(e).__name__}: {e}"})
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
