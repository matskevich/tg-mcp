# Scope: project
# Priority: 60
# Архитектура (to-be)

Модель: монорепо с единым ядром (packages/tganalytics) и несколькими проектами (папки в корне: gconf/, vahue/, …). Legacy-структура `apps/*` может существовать во время миграции, но целевое состояние — проекты в корне.

Правила:
- Любой доступ к Telegram — ТОЛЬКО через core (Gateway/safe_call), общий глобальный лимитер на сессию
- код проектов (gconf/, vahue/, apps/*) использует только публичный API core; импортов между проектами нет
- Прикладную логику apps/* не переносить в core без ADR
- Выделение app в отдельный проект — зависимость от core по SemVer

Уточнения:
- Имя модуля выбрано: `tganalytics` (импорты `from tganalytics.*`).
- Экстракция app: вынос приложения — через git subtree/отдельный репозиторий; зависимость от core по SemVer.
- Public API core: зафиксированные экспортируемые поверхности — `TelegramGateway`, `RateLimiter`, `GroupManager`, `Settings`. В apps запрещено импортировать приватные детали.

Партии миграции (строго в порядке):
1) Scaffold: создать каркас packages/tganalytics/tganalytics/{infra,domain,config}, tganalytics/typing.py; apps/s16-leads/*; tests/core/*
2) Move common: перенести tele_client.py, limiter.py, group_manager.py в tganalytics; добавить tganalytics/infra/logging.py, tganalytics/config/loader.py, tganalytics/typing.py
3) App split: src/cli.py → apps/s16-leads/cli.py; s16-скрипты из examples/ → apps/s16-leads/examples/
4) Fix imports: переписать `src.infra/*`, `src.core/*` → `tganalytics.*`; установить tganalytics локально (editable)
5) Tests & guardrails: базовые тесты на лимитер/ретраи; проверки — нет прямых Telethon в apps, core не импортирует apps

Стоп-условия:
- Любое расширение скопа за пределы партий — спросить
- Конфликт с .cursor/rules/70-telegram-invariants.md — спросить

## data locations (см. `.cursor/rules/65-data-policy.md`)
- `gconf/app/*` — код, загрузчики и sample-файлы (без pii)
- `gconf/data/*` — локальные приватные артефакты gconf (blacklist, выгрузки); .gitignored
- `gconf/export/*` — отчёты/выходы gconf (избегать pii), пишутся по умолчанию сюда
- `vahue/app/*` — код, загрузчики и sample-файлы (без pii)
- `vahue/data/*` — локальные приватные артефакты vahue; .gitignored
- `vahue/export/*` — отчёты/выходы vahue (избегать pii), пишутся по умолчанию сюда
- `packages/tganalytics/*` — никогда не читает `data/*`; только публичный api

## примечание по областям
- gconf — отдельное комьюнити/продукт, не тождественно s16-leads (см. `.cursor/rules/66-gconf-separation.md`).
