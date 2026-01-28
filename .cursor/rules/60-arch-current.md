# Scope: project
# Priority: 60
# Архитектура tg-mcp

Модель: отдельный репозиторий с MCP-сервером + Telegram-библиотекой. Проекты-потребители (gconf, vahue) живут в своих репозиториях и подключают tg-mcp как MCP-сервер.

Структура:
- `tganalytics/tganalytics/` — Python-пакет (infra, domain, config)
- `tganalytics/mcp_server.py` — MCP-сервер (9 tools)
- `tests/` — тесты
- `scripts/` — утилиты (compliance, security)
- `docs/` — документация
- `data/` — runtime данные (sessions, anti_spam, logs) — gitignored

Правила:
- Любой доступ к Telegram — ТОЛЬКО через safe_call / _safe_api_call
- FLOOD_WAIT: обязательный экспоненциальный backoff
- Единый RPS-лимит на сессию (TokenBucket, 4 RPS)
- PII не коммитить; session-файлы защищены (chmod 700/600)

Public API:
- `TelegramGateway`, `RateLimiter`, `GroupManager`, `Settings`
- MCP tools: tg_list_sessions, tg_use_session, tg_get_group_info, и др.

Стоп-условия:
- Расширение API без обновления docs — спросить
- Конфликт с `.cursor/rules/70-telegram-invariants.md` — спросить
