# HELLO AGENT — контекст и рамки

## Что это
Живая экосистема вокруг Telegram (с безопасными вызовами и лимитером). Есть несколько проектов (папки в корне) — например `gconf/`, `vahue/` — и legacy-`apps/*` для старых сценариев. Всё ОБЩЕЕ — в ядре (core): антиспам/лимитер, логгер, доступ к Telegram, конфиг, метрики. Любой проект использует только публичный API core.

## Как есть (as-is, кратко)
- `src/infra/` — `tele_client.py`, `limiter.py` (safe_call, 4 RPS)
- `src/core/` — `group_manager.py`, `s16_config.py` (+ иногда спец-логика для S16)
- `src/cli.py`, `scripts/`, `tests/`, `docs/`, `data/…`
Антиспам и доступ к Telegram уже реализованы, но живут внутри текущего проекта.

## Куда идём (to-be)
- `packages/tg_core` — переиспользуемый пакет:
  - `tg_core/infra/{tele_client.py, limiter.py, logging.py, monitors.py?}`
  - `tg_core/domain/groups.py` (интерфейс + реализация)
  - `tg_core/config/loader.py` (dotenv+pydantic), `tg_core/typing.py`
- `apps/s16-leads` — тонкое приложение (CLI/сценарии), использует `core.*` (legacy)
- `gconf/` — проект gconf: docs + CLI/tools/pipelines + exports
- `vahue/` — проект vahue: docs + аналитика/скрипты/экспорты
- `tests/core/*` — базовые тесты для перенесённых модулей

## Инварианты (НЕ обсуждаются)
- Любой Telethon-вызов — ТОЛЬКО через `tg_core.infra.TelegramGateway.safe_call` (+ backoff FLOOD_WAIT).
- Глобальный лимитер RPS — общий на всю сессию (честное распределение между apps).
- Структурные логи (опционально JSON); PII не логируем; секреты/сессии — вне VCS (.env.sample без секретов).
- core не импортирует apps; apps не импортируют друг друга.

## Что трогать/что не трогать
- ✅ Выносить в `core` общий код infra/domain/config/typing.
- ✅ В apps оставлять только прикладные сценарии/CLI/крон.
- ❌ Не тащить app-специфику (напр. `s16_config.py`) в `core`.
- ❌ Не менять поведение прод-сервиса без явной команды.

## План миграции (партии)
1) **Scaffold** целевой каркас: `packages/core/*`, `apps/s16-leads/*`, `tests/core/*`.
2) **Move common**: `src/infra/{tele_client,limiter} → core/infra/…`, `src/core/group_manager.py → core/domain/groups.py`; добавить `core/config/loader.py`, `core/infra/logging.py`, `core/typing.py`.  
3) **App split**: `src/cli.py → apps/s16-leads/cli.py`; s16-скрипты из `examples/` → в app.  
4) **Fix imports**: все старые импорты → `core.*`; установить core локально (editable).  
5) **Tests & guardrails**: sanity-тесты лимитера/ретраев; тесты-сторожки (нет прямых Telethon в apps, нет импортов apps в core).

## MOVE MAP (ядро — из текущего «как есть»)
- `src/infra/tele_client.py` → `packages/tg_core/tg_core/infra/tele_client.py`
- `src/infra/limiter.py`     → `packages/tg_core/tg_core/infra/limiter.py`
- `src/core/group_manager.py`→ `packages/tg_core/tg_core/domain/groups.py`
- `src/cli.py`               → `apps/s16-leads/cli.py`
- `src/core/s16_config.py`   → `apps/s16-leads/app/config.py` (не в core)

## Процедура работы с агентом
- Всегда **dry-run → diff → apply** (мелкими партиями).
- Приоритет правил: **project > external** (любые Memory Bank/Custom Modes — baseline ниже проекта).
- Если встречаешь неизвестную зависимость/конфликт — остановись и спроси.

## Готовность (Definition of Done)
- `core` собран, тесты зелёные; `apps/*` собираются на новых импорт-путях.
- Глобальный лимитер и FLOOD_WAIT работают как прежде (по логам/метрикам).
- В репо есть: `MIGRATION_PLAN.md`, `PROPOSED_TREE.md`, `docs/onboarding/start.md`.


