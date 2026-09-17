"""Thin async client for AssemblyAI Streaming v3 (Universal-3.5 Pro).

Only what the documented WebSocket protocol offers: connect with query parameters,
send binary PCM frames, receive Begin / Turn / SpeakerRevision / Termination,
change keyterms and prompt mid-stream with UpdateConfiguration, Terminate.
"""
from __future__ import annotations

import json
from typing import AsyncIterator
from urllib.parse import urlencode

import websockets

WS_URL = "wss://streaming.assemblyai.com/v3/ws"


class AssemblyAIStream:
    def __init__(self, api_key: str, *, keyterms: list[str] | None = None, prompt: str | None = None,
                 speaker_labels: bool = True, max_speakers: int = 2, language_codes: tuple[str, ...] = ("en", "it"),
                 inactivity_timeout: int = 60, sample_rate: int = 16000):
        self.api_key = api_key
        params = {"sample_rate": sample_rate, "speech_model": "universal-3-5-pro", "format_turns": "false",
                  "language_codes": json.dumps(list(language_codes)), "inactivity_timeout": inactivity_timeout}
        if speaker_labels:
            params.update({"speaker_labels": "true", "max_speakers": max_speakers})
        if keyterms:
            params["keyterms_prompt"] = json.dumps(keyterms)
        if prompt:
            params["prompt"] = prompt
        self.url = f"{WS_URL}?{urlencode(params)}"
        self.ws: websockets.ClientConnection | None = None
        self.session_id: str | None = None

    async def __aenter__(self) -> "AssemblyAIStream":
        self.ws = await websockets.connect(self.url, additional_headers={"Authorization": self.api_key}, max_size=None)
        return self

    async def __aexit__(self, *exc) -> None:
        if self.ws is not None:
            await self.ws.close()

    async def send_audio(self, pcm: bytes) -> None:
        await self.ws.send(pcm)

    async def update(self, *, keyterms: list[str] | None = None, prompt: str | None = None) -> None:
        """UpdateConfiguration is a delta: only the fields sent change, effective immediately."""
        msg: dict = {"type": "UpdateConfiguration"}
        if keyterms is not None:
            msg["keyterms_prompt"] = keyterms
        if prompt is not None:
            msg["prompt"] = prompt
        await self.ws.send(json.dumps(msg))

    async def terminate(self) -> None:
        try:
            await self.ws.send(json.dumps({"type": "Terminate"}))
        except websockets.ConnectionClosed:
            pass

    async def messages(self) -> AsyncIterator[dict]:
        try:
            async for raw in self.ws:
                if isinstance(raw, bytes):
                    continue
                msg = json.loads(raw)
                if msg.get("type") == "Begin":
                    self.session_id = msg.get("id")
                yield msg
                if msg.get("type") == "Termination":
                    return
        except websockets.ConnectionClosed:
            return
