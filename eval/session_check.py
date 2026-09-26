"""What did the customer's microphone really carry? Transcribes the user channel (left) of a Voice Agent recording with
AssemblyAI's pre-recorded model and prints it next to what the agent understood live, turn by turn.

    .venv/Scripts/python eval/session_check.py sess_...      # after eval/session_fetch.py sess_...

The API key is read from .env and never printed.
"""
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
H = {"Authorization": os.environ["ASSEMBLYAI_API_KEY"]}
API = "https://api.assemblyai.com/v2"


def main() -> None:
    sid = sys.argv[1]
    folder = ROOT / "eval" / "logs" / "sessions" / sid
    audio = (folder / "audio.ogg").read_bytes()
    url = httpx.post(f"{API}/upload", headers=H, content=audio, timeout=300).json()["upload_url"]
    job = httpx.post(f"{API}/transcript", headers=H, timeout=60,
                     json={"audio_url": url, "multichannel": True, "speech_models": ["universal"],
                           "language_detection": True}).json()
    if "id" not in job:
        print(job)
        return
    while True:
        r = httpx.get(f"{API}/transcript/{job['id']}", headers=H, timeout=60).json()
        if r["status"] in ("completed", "error"):
            break
        time.sleep(3)
    if r["status"] == "error":
        print(r.get("error"))
        return
    (folder / "offline.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    timeline = json.loads((folder / "timeline.json").read_text(encoding="utf-8"))
    t0 = timeline["started_at_unix_ms"]
    user_words = [w for w in r.get("words", []) if str(w.get("channel")) == "1"]
    print(f"offline model: {r.get('speech_model_used') or r.get('speech_model')}, language {r.get('language_code')}")
    for turn in timeline.get("turns", []):
        live = turn.get("user_transcript")
        a, b = turn.get("user_speech_started_at_ms"), turn.get("user_speech_ended_at_ms")
        if not live or not a:
            continue
        a, b = a - t0 - 300, (b or a) - t0 + 300
        heard = " ".join(w["text"] for w in user_words if a <= w["start"] <= b)
        mark = "" if heard.lower().strip(" .?!") == live.lower().strip(" .?!") else "   <-- differs"
        print(f"{a / 1000:6.1f}s LIVE   : {live}\n{'':8}OFFLINE: {heard}{mark}")


if __name__ == "__main__":
    main()
