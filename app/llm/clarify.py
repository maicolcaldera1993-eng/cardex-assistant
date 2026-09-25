"""The 'clear version': what the customer meant, in the operator's language.

One LLM call per batch through AssemblyAI LLM Gateway (OpenAI-compatible). A free
AssemblyAI account gets one model (qwen3.5-4b-32k-fast) and about two requests per
minute, so turns are queued and clarified together as soon as a slot is free. The
transcript never waits for this: the clear version arrives later, or not at all.
Endpoint, model and rate are environment settings, so a better model needs no code change.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Awaitable, Callable

import httpx

GATEWAY_URL = os.getenv("LLM_BASE_URL", "https://llm-gateway.assemblyai.com/v1/chat/completions")
MODEL = os.getenv("LLM_MODEL", "qwen3.5-4b-32k-fast")
MAX_PER_MINUTE = int(os.getenv("LLM_MAX_PER_MINUTE", "2"))
MAX_BATCH = 6

LANG_NAME = {"it": "Italian", "en": "English"}

GLOSSARY = ("shower screen = doccetta, group gasket = guarnizione sottocoppa, portafilter = portafiltro, "
            "steam wand = lancia vapore, blind filter = filtro cieco, boiler = caldaia, gauge = manometro, "
            "burrs = macine, heating element = resistenza, control board = centralina, touchpad = pulsantiera")


def system_prompt(lang: str) -> str:
    target = LANG_NAME.get(lang, "Italian")
    glossary = f" Use these Italian trade words: {GLOSSARY}." if lang == "it" else ""
    return (
        "You help a help-desk operator understand a foreign customer on a phone call about a professional espresso "
        "machine. The customer speaks broken English or their own language; the text comes from speech recognition and "
        f"may contain errors. For each numbered line, write what the customer MEANT in clear {target}: faithful and "
        "complete, in one to three short sentences. Never drop what the customer reports or answers, above all the "
        "result at the end ('no change', 'still the same', 'now it works', yes or no): it is what the operator needs. "
        "Keep every part code (like GE-2140), model name (Marea, Giglio, Onda, Monda, Vaniglia) and number exactly as "
        f"written; people in the shop are staff, not friends.{glossary} Do not add information. Do not explain. "
        "Answer with the same numbers, one line each, in the form '1) sentence'."
    )


class Clarifier:
    def __init__(self, api_key: str, lang: str, on_result: Callable[[int, str], Awaitable[None]]):
        self.api_key, self.lang, self.on_result = api_key, lang, on_result
        self.queue: list[tuple[int, str]] = []
        self.calls: list[float] = []          # monotonic timestamps of recent calls
        self.enabled = True
        self._wake = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._client = httpx.AsyncClient(timeout=30)

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
        await self._client.aclose()

    def submit(self, turn_id: int, text: str) -> None:
        if self.enabled and len(text.split()) >= 3:
            self.queue = [(i, t) for i, t in self.queue if i != turn_id]   # the utterance grew: keep only its latest text
            self.queue.append((turn_id, text))
            self._wake.set()

    def _wait_needed(self) -> float:
        now = time.monotonic()
        self.calls = [t for t in self.calls if now - t < 60]
        if len(self.calls) < MAX_PER_MINUTE:
            return 0.0
        return 60 - (now - self.calls[0]) + 0.5

    async def _run(self) -> None:
        while True:
            await self._wake.wait()
            wait = self._wait_needed()
            if wait:
                await asyncio.sleep(wait)
            batch, self.queue = self.queue[:MAX_BATCH], self.queue[MAX_BATCH:]
            if not self.queue:
                self._wake.clear()
            if not batch:
                continue
            self.calls.append(time.monotonic())
            try:
                results = await self._call(batch)
            except Exception:  # noqa: BLE001 - the transcript must never depend on this
                results = {}
            for turn_id, _ in batch:
                if turn_id in results:
                    await self.on_result(turn_id, results[turn_id])

    async def _call(self, batch: list[tuple[int, str]]) -> dict[int, str]:
        numbered = "\n".join(f"{i + 1}) {text}" for i, (_, text) in enumerate(batch))
        r = await self._client.post(GATEWAY_URL, headers={"Authorization": self.api_key}, json={
            "model": MODEL, "temperature": 0.1, "max_tokens": 120 * len(batch),
            "messages": [{"role": "system", "content": system_prompt(self.lang)}, {"role": "user", "content": numbered}]})
        if r.status_code == 429:
            self.queue = batch + self.queue      # try again at the next slot
            self.calls.append(time.monotonic())
            self._wake.set()
            return {}
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        out: dict[int, str] = {}
        for m in re.finditer(r"^\s*(\d+)[\)\.:]\s*(.+)$", content, re.M):
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(batch):
                out[batch[idx][0]] = m.group(2).strip()
        if not out and len(batch) == 1:
            out[batch[0][0]] = content.strip()
        return out
