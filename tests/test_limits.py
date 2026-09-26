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


def test_token_waits_for_the_call_that_is_opening():
    """26/9 on Railway: the page asks for the token while the call socket is still opening; the token must wait
    for the call instead of failing with 429."""
    import asyncio
    from fastapi import HTTPException
    import app.main as main
    b = DemoBudget()
    main.BUDGET = b
    main.API_KEY = main.API_KEY or "test"

    async def fake_token(key, seconds=600):
        return "tok"

    import app.voice.agent as agent
    orig = agent.session_token
    agent.session_token = fake_token

    class Req:
        headers = {"x-forwarded-for": "5.5.5.5"}
        client = None

    async def scenario():
        async def open_call_later():
            await asyncio.sleep(0.5)
            b.start(99, "5.5.5.5", 1)
        asyncio.create_task(open_call_later())
        return await main.voice_token(Req())
    try:
        assert asyncio.run(scenario())["token"] == "tok"
        try:
            asyncio.run(main.voice_token(type("R", (), {"headers": {"x-forwarded-for": "6.6.6.6"}, "client": None})()))
            assert False, "a caller without a call must be refused"
        except HTTPException as e:
            assert e.status_code == 429
    finally:
        agent.session_token = orig
