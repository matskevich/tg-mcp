# Scope: project
# Priority: 70
# Telegram-инварианты (MUST)

MUST:
- Все Telethon-вызовы — через tganalytics.TelegramGateway.safe_call
- FLOOD_WAIT: обязательный экспоненциальный backoff; единый RPS-лимит на сессию (лимитер tganalytics) не обходить
- Единый структурный логгер tganalytics (опц. JSON); PII не логировать
- Базовые тесты на лимитер/ретраи — зелёные; изменения, ломающие их, запрещены

NEVER:
- Прямые Telethon-вызовы из project code (gconf/, vahue/, apps/*)
- Вшивать ключи/ID/сессии в код/логи

SHOULD:
- Хранить .session вне VCS; .env.sample — без секретов

SLO:
- Не снижать производительность >10% от текущих показателей без одобренного ADR.

Observability (метрики):
- rate_limit_requests_total — количество запросов, прошедших через лимитер
- rate_limit_throttled_total — количество запросов, задержанных/отклонённых лимитером
- flood_wait_events_total — количество событий FLOOD_WAIT (по уровням)
- tele_call_latency_seconds (histogram) — задержка вызовов к Telegram API

## data/pii policy
- Персональные выгрузки и списки (blacklist и т.п.) не коммитить; хранить в `gconf/data/*` (см. `.cursor/rules/65-data-policy.md`) или `<project>/data/*`
- Отчёты аналитики по умолчанию писать в `gconf/export/*` или `<project>/export/*`, избегая PII
