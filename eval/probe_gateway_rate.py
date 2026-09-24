"""How many LLM Gateway requests per minute does our account accept? Fires a burst of short requests and
counts 200 vs 429. Costs a few hundred tokens.    .venv/Scripts/python eval/probe_gateway_rate.py [model] [n]"""
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
KEY = os.environ["ASSEMBLYAI_API_KEY"]
URL = "https://llm-gateway.assemblyai.com/v1/chat/completions"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.5-4b-32k-fast"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 8

t0 = time.perf_counter()
for i in range(N):
    t = time.perf_counter()
    r = httpx.post(URL, headers={"Authorization": KEY}, timeout=30, json={
        "model": MODEL, "max_tokens": 8, "messages": [{"role": "user", "content": f"Reply with the number {i}."}]})
    dt = time.perf_counter() - t
    note = "" if r.status_code == 200 else " " + r.text[:160].replace("\n", " ")
    print(f"{time.perf_counter() - t0:5.1f}s  #{i}  {r.status_code}  {dt:4.1f}s{note}")
    if r.status_code == 429:
        ra = r.headers.get("retry-after") or r.headers.get("x-ratelimit-reset")
        print("       retry-after:", ra, "| limit headers:", {k: v for k, v in r.headers.items() if "ratelimit" in k.lower()})
