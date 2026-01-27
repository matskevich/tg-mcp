"""
Minimal metrics for observability.

Exports counters and a simple latency histogram in-memory.

Metrics:
- rate_limit_requests_total
- rate_limit_throttled_total
- flood_wait_events_total
- tele_call_latency_seconds (histogram)
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List


_lock = threading.Lock()

# Counters
rate_limit_requests_total: int = 0
rate_limit_throttled_total: int = 0
flood_wait_events_total: int = 0

# Histogram buckets (seconds): 0.05, 0.1, 0.25, 0.5, 1, 2, 5, +Inf
_latency_buckets = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
tele_call_latency_buckets: Dict[float, int] = {b: 0 for b in _latency_buckets}
tele_call_latency_inf: int = 0


def increment_rate_limit_requests_total() -> None:
    global rate_limit_requests_total
    with _lock:
        rate_limit_requests_total += 1


def increment_rate_limit_throttled_total() -> None:
    global rate_limit_throttled_total
    with _lock:
        rate_limit_throttled_total += 1


def increment_flood_wait_events_total() -> None:
    global flood_wait_events_total
    with _lock:
        flood_wait_events_total += 1


def observe_tele_call_latency_seconds(value_seconds: float) -> None:
    global tele_call_latency_inf
    with _lock:
        placed = False
        for b in _latency_buckets:
            if value_seconds <= b:
                tele_call_latency_buckets[b] = tele_call_latency_buckets.get(b, 0) + 1
                placed = True
                break
        if not placed:
            tele_call_latency_inf += 1


def time_call_seconds(func, *args, **kwargs) -> float:
    start = time.perf_counter()
    _ = func(*args, **kwargs)
    end = time.perf_counter()
    return end - start


def snapshot() -> Dict[str, object]:
    with _lock:
        return {
            "rate_limit_requests_total": rate_limit_requests_total,
            "rate_limit_throttled_total": rate_limit_throttled_total,
            "flood_wait_events_total": flood_wait_events_total,
            "tele_call_latency_seconds": {
                **{str(b): tele_call_latency_buckets.get(b, 0) for b in _latency_buckets},
                "+Inf": tele_call_latency_inf,
            },
        }


