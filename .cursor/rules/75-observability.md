# Scope: project
# Priority: 75
# Observability (minimal metrics)

метрики (минимальный набор):
- rate_limit_requests_total — количество запросов, прошедших через rate limiter
- rate_limit_throttled_total — количество запросов, задержанных/отклонённых лимитером
- flood_wait_events_total — количество событий FLOOD_WAIT
- tele_call_latency_seconds (histogram) — задержка вызовов Telegram API

требования:
- инкремент и измерение — в core (`tg_core.infra.*`), без импорта apps
- доступ к метрикам через модуль `tg_core.infra.metrics`
