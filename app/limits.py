"""Public demo guard: the Voice Agent costs money on the owner's AssemblyAI account, so a public URL gets limits.

Everything is set from environment variables (Railway → Variables), no code change needed:
  MAX_VOICE_CALLS        calls with a Voice Agent running at the same time                 (default 2)
  DAILY_AGENT_MINUTES    agent minutes per day, all callers together; a two-AI call counts twice (default 180)
  CALLS_PER_IP_PER_HOUR  calls one address may start in an hour                            (default 8)
  DEMO_UNTIL             last day voice calls are open, YYYY-MM-DD; empty = no end date    (default empty)
The real ceiling is the AssemblyAI balance itself: with auto-recharge off, spending stops when the credits end.
Counters live in memory: a redeploy resets the day's minutes.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from datetime import date

MAX_VOICE_CALLS = int(os.getenv("MAX_VOICE_CALLS", "2"))
DAILY_AGENT_MINUTES = float(os.getenv("DAILY_AGENT_MINUTES", "180"))
CALLS_PER_IP_PER_HOUR = int(os.getenv("CALLS_PER_IP_PER_HOUR", "8"))
DEMO_UNTIL = os.getenv("DEMO_UNTIL", "").strip()
TOKENS_PER_CALL = 6            # a call may hand over to another language's voice, a two-AI call needs two


class DemoBudget:
    def __init__(self) -> None:
        self.day = date.today()
        self.used_seconds = 0.0
        self.calls: dict[str, deque] = defaultdict(deque)        # ip -> start times in the last hour
        self.active: dict[int, dict] = {}                        # call id -> {ip, agents, started, tokens}

    def _roll(self) -> None:
        if date.today() != self.day:
            self.day, self.used_seconds = date.today(), 0.0

    def minutes_left(self) -> float:
        self._roll()
        running = sum((time.monotonic() - c["started"]) * c["agents"] for c in self.active.values())
        return max(0.0, DAILY_AGENT_MINUTES - (self.used_seconds + running) / 60)

    def refuse_call(self, ip: str) -> str | None:
        """Why a new voice call cannot start now, or None."""
        self._roll()
        if DEMO_UNTIL and date.today().isoformat() > DEMO_UNTIL:
            return "The live voice demo has ended. The recorded call on the home page still works."
        if len(self.active) >= MAX_VOICE_CALLS:
            return "The demo is busy: two calls are running. Please try again in a few minutes."
        if self.minutes_left() < 3:
            return "Today's demo minutes are used up. Please try again tomorrow."
        recent = self.calls[ip]
        while recent and time.monotonic() - recent[0] > 3600:
            recent.popleft()
        if len(recent) >= CALLS_PER_IP_PER_HOUR:
            return "Too many calls from this connection in the last hour. Please try again later."
        return None

    def start(self, call_id: int, ip: str, agents: int) -> None:
        self.calls[ip].append(time.monotonic())
        self.active[call_id] = {"ip": ip, "agents": max(1, min(2, agents)), "started": time.monotonic(), "tokens": 0}

    def end(self, call_id: int) -> None:
        c = self.active.pop(call_id, None)
        if c:
            self._roll()
            self.used_seconds += (time.monotonic() - c["started"]) * c["agents"]

    def allow_token(self, ip: str) -> bool:
        """A Voice Agent token only for a caller with a call open, a few per call: no tokens minted on the side."""
        for c in self.active.values():
            if c["ip"] == ip and c["tokens"] < TOKENS_PER_CALL:
                c["tokens"] += 1
                return True
        return False

    def status(self) -> dict:
        return {"voice_calls": len(self.active), "max_voice_calls": MAX_VOICE_CALLS,
                "minutes_left_today": round(self.minutes_left()), "demo_until": DEMO_UNTIL or None}


BUDGET = DemoBudget()


def client_ip(headers, client) -> str:
    """The caller's address behind Railway's proxy."""
    fwd = headers.get("x-forwarded-for") if headers else None
    if fwd:
        return fwd.split(",")[0].strip()
    return getattr(client, "host", None) or "unknown"
