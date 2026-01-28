import asyncio
from types import SimpleNamespace

import tg_core.infra.metrics as metrics


def test_counters_increment_sanity(monkeypatch):
    # snapshot initial
    start = metrics.snapshot()

    # simulate events
    metrics.increment_rate_limit_requests_total()
    metrics.increment_rate_limit_requests_total()
    metrics.increment_rate_limit_throttled_total()
    metrics.increment_flood_wait_events_total()
    metrics.observe_tele_call_latency_seconds(0.12)
    metrics.observe_tele_call_latency_seconds(0.8)

    snap = metrics.snapshot()

    assert snap["rate_limit_requests_total"] >= start["rate_limit_requests_total"] + 2
    assert snap["rate_limit_throttled_total"] >= start["rate_limit_throttled_total"] + 1
    assert snap["flood_wait_events_total"] >= start["flood_wait_events_total"] + 1

    # latency histogram has counted in some bucket(s)
    lat = snap["tele_call_latency_seconds"]
    assert any(count > 0 for count in lat.values())
