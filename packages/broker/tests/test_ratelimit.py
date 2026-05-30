"""Per-client rate-limiting (ratelimit.py).

Pure tests — no network, no Docker. A deterministic clock (``FakeClock``) is
injected so the sliding-window semantics are observable without `sleep`.

Three things to verify:

  1. ``SlidingWindow.allow`` admits exactly ``limit`` requests in any
     ``window_seconds`` interval and reports a sensible ``retry_after``.
  2. ``RateLimiter`` keeps per-(route, client) windows independent so one
     client's flood doesn't poison another's quota, and one route's quota
     doesn't poison another route's.
  3. ``RateLimitMiddleware`` returns 429 with the right ``Retry-After``
     header on deny, lets unlisted routes through unconditionally, and
     respects the trust-proxy-headers toggle for client identification.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hearme_broker.ratelimit import (
    RateLimitMiddleware,
    RateLimiter,
    Rule,
    SlidingWindow,
    client_id_from_request,
)


class FakeClock:
    """Monotonic ``time.monotonic``-like fake we step manually."""

    def __init__(self) -> None:
        self.t = 1_000_000.0  # arbitrary base so test never sees 0

    def now(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


# ----- SlidingWindow primitive -------------------------------------------


def test_sliding_window_admits_up_to_limit_then_denies():
    clock = FakeClock()
    w = SlidingWindow(rule=Rule(limit=3, window_seconds=60))
    for _ in range(3):
        ok, retry = w.allow(clock.now())
        assert ok is True
        assert retry == 0.0
    ok, retry = w.allow(clock.now())
    assert ok is False
    # Retry-after points at when the OLDEST in-window request expires —
    # since we just submitted 3 at t=now, that's ``window_seconds`` away.
    assert pytest.approx(retry, abs=1e-6) == 60.0


def test_sliding_window_admits_again_after_window_slides():
    clock = FakeClock()
    w = SlidingWindow(rule=Rule(limit=2, window_seconds=10))
    assert w.allow(clock.now())[0] is True
    clock.advance(3)
    assert w.allow(clock.now())[0] is True
    # At t=3, both requests still in [t-10, t]; window full.
    assert w.allow(clock.now())[0] is False
    # Advance just past the first request's expiry — capacity reopens.
    clock.advance(8)  # now t=11; first request was at t=0
    ok, _ = w.allow(clock.now())
    assert ok is True


# ----- RateLimiter (per-route, per-client) -------------------------------


def test_rule_limit_zero_disables_route():
    clock = FakeClock()
    limiter = RateLimiter({"POST /x": Rule(limit=0, window_seconds=60)}, now_fn=clock.now)
    # Limit=0 means "no rule" — every request allowed.
    for _ in range(100):
        ok, _ = limiter.check(route="POST /x", client_id="c1")
        assert ok is True


def test_unlisted_route_is_not_limited():
    clock = FakeClock()
    limiter = RateLimiter({"POST /x": Rule(limit=1, window_seconds=60)}, now_fn=clock.now)
    assert limiter.check(route="POST /x", client_id="c1")[0] is True
    assert limiter.check(route="POST /x", client_id="c1")[0] is False
    # Different route — no rule, free pass.
    for _ in range(5):
        assert limiter.check(route="GET /y", client_id="c1")[0] is True


def test_clients_are_independent():
    clock = FakeClock()
    limiter = RateLimiter({"POST /x": Rule(limit=2, window_seconds=60)}, now_fn=clock.now)
    # Client A exhausts its quota.
    assert limiter.check(route="POST /x", client_id="A")[0] is True
    assert limiter.check(route="POST /x", client_id="A")[0] is True
    assert limiter.check(route="POST /x", client_id="A")[0] is False
    # Client B is fresh, fully independent.
    assert limiter.check(route="POST /x", client_id="B")[0] is True
    assert limiter.check(route="POST /x", client_id="B")[0] is True


def test_routes_are_independent_per_client():
    clock = FakeClock()
    limiter = RateLimiter(
        {
            "POST /a": Rule(limit=1, window_seconds=60),
            "POST /b": Rule(limit=1, window_seconds=60),
        },
        now_fn=clock.now,
    )
    # Same client, two routes — exhausting one must not affect the other.
    assert limiter.check(route="POST /a", client_id="c")[0] is True
    assert limiter.check(route="POST /a", client_id="c")[0] is False
    assert limiter.check(route="POST /b", client_id="c")[0] is True


# ----- RateLimitMiddleware integration -----------------------------------


def _app_with_limiter(limiter: RateLimiter, *, trust_proxy: bool = True) -> TestClient:
    app = FastAPI()

    @app.post("/v1/envelopes")
    def post_envelopes():
        return {"ok": True}

    @app.get("/v1/questions/open")
    def get_questions():
        return []

    app.add_middleware(
        RateLimitMiddleware,
        limiter=limiter,
        trust_proxy_headers=trust_proxy,
    )
    return TestClient(app)


def test_middleware_returns_429_with_retry_after():
    clock = FakeClock()
    limiter = RateLimiter(
        {"POST /v1/envelopes": Rule(limit=2, window_seconds=60)}, now_fn=clock.now
    )
    client = _app_with_limiter(limiter)
    assert client.post("/v1/envelopes").status_code == 200
    assert client.post("/v1/envelopes").status_code == 200
    resp = client.post("/v1/envelopes")
    assert resp.status_code == 429
    # Retry-After is an integer seconds in the future.
    assert "Retry-After" in resp.headers
    assert int(resp.headers["Retry-After"]) >= 1
    body = resp.json()
    assert body == {"error": "rate_limited", "retry_after_seconds": int(resp.headers["Retry-After"])}


def test_middleware_lets_unlisted_routes_through_always():
    clock = FakeClock()
    limiter = RateLimiter(
        {"POST /v1/envelopes": Rule(limit=1, window_seconds=60)}, now_fn=clock.now
    )
    client = _app_with_limiter(limiter)
    # Spam the read endpoint hard — no limit configured for it.
    for _ in range(50):
        assert client.get("/v1/questions/open").status_code == 200


def test_middleware_trusts_x_real_ip_when_enabled():
    """Two distinct ``X-Real-IP`` values get distinct quotas; without the
    header trust both fall back to the same TestClient peer and share one."""
    clock = FakeClock()
    limiter = RateLimiter(
        {"POST /v1/envelopes": Rule(limit=1, window_seconds=60)}, now_fn=clock.now
    )
    client = _app_with_limiter(limiter, trust_proxy=True)
    assert client.post("/v1/envelopes", headers={"X-Real-IP": "1.1.1.1"}).status_code == 200
    assert client.post("/v1/envelopes", headers={"X-Real-IP": "2.2.2.2"}).status_code == 200
    # Same X-Real-IP — second one denied.
    assert client.post("/v1/envelopes", headers={"X-Real-IP": "1.1.1.1"}).status_code == 429


def test_middleware_ignores_x_real_ip_when_disabled():
    """With trust_proxy=False both 'tenants' collapse to the TestClient peer
    and the limit catches both."""
    clock = FakeClock()
    limiter = RateLimiter(
        {"POST /v1/envelopes": Rule(limit=1, window_seconds=60)}, now_fn=clock.now
    )
    client = _app_with_limiter(limiter, trust_proxy=False)
    assert client.post("/v1/envelopes", headers={"X-Real-IP": "1.1.1.1"}).status_code == 200
    assert client.post("/v1/envelopes", headers={"X-Real-IP": "2.2.2.2"}).status_code == 429


# ----- client_id extraction ----------------------------------------------


def test_client_id_prefers_x_real_ip_over_x_forwarded_for_over_peer():
    from starlette.requests import Request

    def _req(headers: dict[str, str]):
        scope = {
            "type": "http",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "client": ("9.9.9.9", 12345),
        }
        return Request(scope)

    assert (
        client_id_from_request(
            _req({"X-Real-IP": "1.1.1.1", "X-Forwarded-For": "2.2.2.2"}),
            trust_proxy_headers=True,
        )
        == "1.1.1.1"
    )
    # No X-Real-IP — first hop of X-Forwarded-For.
    assert (
        client_id_from_request(
            _req({"X-Forwarded-For": "3.3.3.3, 4.4.4.4, 5.5.5.5"}),
            trust_proxy_headers=True,
        )
        == "3.3.3.3"
    )
    # No proxy headers — direct peer.
    assert (
        client_id_from_request(_req({}), trust_proxy_headers=True) == "9.9.9.9"
    )
    # trust_proxy_headers=False — never honor headers even when present.
    assert (
        client_id_from_request(
            _req({"X-Real-IP": "1.1.1.1", "X-Forwarded-For": "2.2.2.2"}),
            trust_proxy_headers=False,
        )
        == "9.9.9.9"
    )
