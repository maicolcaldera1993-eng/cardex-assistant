"""Download what AssemblyAI's Voice Agent actually heard in a past call: the recording, the timeline (what it
understood in each turn, with confidence and timings, and the tool calls) and the metadata.

    .venv/Scripts/python eval/session_fetch.py                 # list the latest sessions
    .venv/Scripts/python eval/session_fetch.py sess_...        # download one into eval/logs/sessions/<id>/

The API key is read from .env and never printed.
"""
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
BASE = "https://agents.assemblyai.com/v1"
HEADERS = {"Authorization": os.environ["ASSEMBLYAI_API_KEY"]}


def main() -> None:
    if len(sys.argv) < 2:
        page = httpx.get(f"{BASE}/sessions", params={"limit": 20}, headers=HEADERS, timeout=30).json()
        for s in page.get("sessions", []):
            print(s["id"], s["status"], s.get("created_at", "")[:19], f"{s.get('duration_seconds') or 0:6.1f}s",
                  s.get("public_close_reason"))
        return
    sid = sys.argv[1]
    session = httpx.get(f"{BASE}/sessions/{sid}", headers=HEADERS, timeout=30).json()
    out = ROOT / "eval" / "logs" / "sessions" / sid
    out.mkdir(parents=True, exist_ok=True)
    (out / "session.json").write_text(json.dumps({k: v for k, v in session.items() if k != "artifacts"}, indent=1,
                                                 ensure_ascii=False), encoding="utf-8")
    for a in session.get("artifacts", []):
        ext = {"audio": ".ogg", "timeline": ".json", "metadata": ".meta.json"}.get(a["type"], "")
        data = httpx.get(a["url"], timeout=120).content                    # pre-signed URL: no auth header
        (out / f"{a['type']}{ext}").write_bytes(data)
        print(a["type"], len(data), "bytes")
    print("saved in", out)


if __name__ == "__main__":
    main()
