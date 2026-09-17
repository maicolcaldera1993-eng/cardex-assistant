"""One-off probe: does LLM Gateway answer with our key, which model ids work, how fast."""
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
KEY = os.environ["ASSEMBLYAI_API_KEY"]
URL = "https://llm-gateway.assemblyai.com/v1/chat/completions"

candidates = sys.argv[1:] or ["gemini-2.5-flash-lite", "claude-haiku-4-5", "gpt-5-nano", "qwen3.5-4b-32k-fast", "gemini-3-flash-preview"]
for model in candidates:
    t = time.perf_counter()
    try:
        r = httpx.post(URL, headers={"Authorization": KEY}, timeout=30, json={
            "model": model, "max_tokens": 120,
            "messages": [{"role": "user", "content": "Rewrite in correct Italian, one sentence: 'ze coffee she come out sin and fast like water since two week'"}]})
        dt = time.perf_counter() - t
        if r.status_code == 200:
            body = r.json()
            print(f"OK  {model:28s} {dt:4.1f}s  {body['choices'][0]['message']['content'][:120]!r}")
        else:
            print(f"ERR {model:28s} {r.status_code} {r.text[:300]}")
    except Exception as e:  # noqa: BLE001
        print(f"EXC {model:28s} {e}")
