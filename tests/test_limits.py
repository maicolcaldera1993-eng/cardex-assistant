"""Public demo guard: concurrency, per-address rate, daily minutes, end date, tokens only for an open call."""
import app.limits as limits
from app.limits import DemoBudget


def test_concurrency_and_tokens():
    b = DemoBudget()
    assert b.refuse_call("1.1.1.1") is None
    b.start(1, "1.1.1.1", 1)
    assert b.allow_token("1.1.1.1") and not b.allow_token("2.2.2.2")      # no call open from 2.2.2.2
    b.start(2, "2.2.2.2", 2)
    assert "busy" in b.refuse_call("3.3.3.3")
    b.end(1)
    assert b.refuse_call("3.3.3.3") is None
    for _ in range(limits.TOKENS_PER_CALL):
        b.allow_token("2.2.2.2")
    assert not b.allow_token("2.2.2.2")                                   # a handful per call, not a token mint


def test_rate_per_address_and_daily_minutes(monkeypatch):
    b = DemoBudget()
    for i in range(limits.CALLS_PER_IP_PER_HOUR):
        b.start(i, "9.9.9.9", 1)
        b.end(i)
    assert "Too many calls" in b.refuse_call("9.9.9.9")
    b.used_seconds = (limits.DAILY_AGENT_MINUTES - 1) * 60
    assert "minutes are used up" in b.refuse_call("8.8.8.8")


def test_end_date(monkeypatch):
    monkeypatch.setattr(limits, "DEMO_UNTIL", "2000-01-01")
    assert "ended" in DemoBudget().refuse_call("1.1.1.1")
