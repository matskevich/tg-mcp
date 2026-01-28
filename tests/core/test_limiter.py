import asyncio
import types
from pathlib import Path
import sys

# Ensure tg_core package is importable without editable install
sys.path.append(str(Path(__file__).resolve().parents[2] / "packages" / "tg_core"))

import tg_core.infra.limiter as limiter
from types import SimpleNamespace


class _FakeBucket:
    async def acquire(self, tokens_needed: int = 1) -> bool:
        return True


class _FakeLimiter:
    def __init__(self):
        self.bucket = _FakeBucket()
        self.rps = 4.0
        self.daily_counters = {"api_calls": 0, "dm_count": 0, "join_count": 0}

    async def check_dm_quota(self) -> bool:
        return True

    async def check_join_quota(self) -> bool:
        return True

    async def increment_api_counter(self):
        self.daily_counters["api_calls"] += 1

    async def increment_dm_counter(self):
        self.daily_counters["dm_count"] += 1

    async def increment_join_counter(self):
        self.daily_counters["join_count"] += 1

    async def increment_flood_counter(self, wait_time: int):
        # no-op for test speed
        pass


async def _no_sleep(_seconds: float):
    return None


def test_token_bucket_basic_allows_quick_burst():
    bucket = limiter.TokenBucket(capacity=2, refill_rate=1000.0)

    async def run():
        # two immediate acquires should not block at high refill_rate
        assert await bucket.acquire(1) is True
        assert await bucket.acquire(1) is True

    asyncio.run(run())


def test_safe_call_retries_on_floodwait_and_succeeds(monkeypatch):
    fake = _FakeLimiter()
    monkeypatch.setattr(limiter, "get_rate_limiter", lambda: fake)
    monkeypatch.setattr(limiter.asyncio, "sleep", _no_sleep)

    call_state = {"attempt": 0}

    # Provide a minimal FloodWaitError replacement compatible with limiter
    class _FakeFloodWaitError(Exception):
        def __init__(self, seconds: int):
            self.seconds = seconds

    # monkeypatch limiter's FloodWaitError to our fake
    monkeypatch.setattr(limiter, "FloodWaitError", _FakeFloodWaitError, raising=False)

    async def flaky_func():
        call_state["attempt"] += 1
        if call_state["attempt"] < 3:
            raise limiter.FloodWaitError(seconds=0)
        return 42

    result = asyncio.run(limiter.safe_call(flaky_func, operation_type="api", max_retries=3))
    assert result == 42
    assert call_state["attempt"] == 3


