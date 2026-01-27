## GPT‑5 Architecture Discussion: Modular Split and Future Evolution

### Objective
Подготовить обсуждение архитектуры с GPT‑5 для реорганизации проекта:
- Выделить независимый `core` (Telegram API adapter, anti‑spam, логирование, утилиты, базовые доменные интерфейсы)
- Разнести прикладные части в отдельные проекты: `gconf/` (аналитика/отчеты), `vahue/`, и потенциальные новые (папки в корне). Legacy: `apps/*`.
- Сохранить совместимость, упростить расширение и эксплуатацию.

---

### Current Context (as‑is)
- Язык/стек: Python 3.9+, Telethon, pytest, dotenv, asyncio
- Директории (ключевые):
  - `src/core/` — `group_manager.py`, `s16_config.py`, (+ `gender_analyzer.py`)
  - `src/infra/` — `tele_client.py`, `limiter.py` (token bucket, safe_call, smart_pause), (+ `monitors.py` планировался)
  - `src/cli.py` — CLI с командами `info`, `participants`, `search`, `export`, `creation-date`
  - `scripts/` — setup/security/checks/sync_env и утилиты
  - `data/export/…` — агрегированные JSON (офлайн-ивенты, сравнения со space)
  - `tests/` — unit/integration для GroupManager/CLI
  - `docs/` — анти‑спам, гайды, playbook для seeders
  - `memory_bank/` — контекст, прогресс, рефлексии
- Анти‑спам: централизованный лимитер (4 RPS), `safe_call`, backoff, квоты, `smart_pause`, отчеты. Покрывает все API вызовы (prod‑ready, в логах есть SAFE‑инициализация).
- Доменные правила:
  - Референсная группа экосистемы: `s16 space` (ID: -1002188344480). Сверка ведется против нее.
  - Персональные данные TG участников не коммитить в GitHub (экспорт — только локально/в защищенных хранилищах).
- Операционный процесс Seeders: выбрать next‑10 (не в space, не stale), отметить их `stale` на 180 дней, верифицировать — зафиксировано в `docs/LEADS_SEEDERS_PLAYBOOK.md`.

Нефункциональные свойства:
- Надежность: устойчивость к FLOOD_WAIT, без блокировок (в проде подтверждено)
- Производительность: <5–10% overhead при включенном rate limiting
- Конфигурируемость: через `.env`, вспомогательные скрипты для sync/validate
- Тестируемость: pytest + моки Telethon

---

### Target Architecture (to‑be)

#### 1) Monorepo c модулями: `core` как пакет, приложения в `apps/*`
- `packages/core` (distributable wheel):
  - `core/infra/tele_client.py` — Telegram client adapter (инициализация, безопасные вызовы)
  - `core/infra/limiter.py` — token bucket, `RateLimiter`, `safe_call`, `smart_pause`
  - `core/infra/logging.py` — централизованный логгер, корелляция, SAFE‑теги
  - `core/infra/monitors.py` — AntiSpamMonitor, метрики (план)
  - `core/domain/groups.py` — `GroupManager` интерфейс и реализация
  - `core/config/` — загрузка/валидация конфигов (dotenv + pydantic/typer опционально)
  - `core/typing.py` — общие типы/DTO (User, GroupInfo, Participant, ResultPage)
  - `core/testing/` — фреймворк моков (утилиты для pytest)

- `apps/s16-leads`
  - CLI/команды (info/participants/search/export/creation-date)
  - Исп. только публичные API `core`
  - Доменные сценарии: сбор/экспорт, seeders workflow (операционные команды)

- `gconf/` (analytics/config)
  - Аналитика/отчеты (сравнение групп, метрики, графики)
  - Генераторы отчетов (JSON/CSV/HTML), возможно API/сервер (FastAPI) на перспективу

- (Опционально) `apps/ingest`, `apps/seeders` как самостоятельные пакеты команд, если потребуется изоляция версий/зависимостей.

Плюсы:
- Чёткие границы: `core` без бизнес‑логики конкретных приложений
- Повторное использование: любой новый app использует те же безопасные адаптеры
- Тестируемость: тесты на уровне core изолированы от прикладного слоя

Минусы:
- Потребуется миграция путей/импортов и разнесение зависимостей

#### 2) Пакетирование и версии
- `packages/core/pyproject.toml` (Poetry/uv/PEX) или `setup.cfg` (pip)
- Версионирование `core`: SemVer (`MAJOR.MINOR.PATCH`)
- `apps/*` зависят от `core>=X.Y` (локально — editable install)

#### 3) Конфигурации и секреты
- Единый loader (dotenv+pydantic) в `core.config`
- Раздельные `.env` для приложений (`apps/s16-leads/.env.sample` и т.д.)
- Политики: исключение персональных данных из VCS

#### 4) Логи/Метрики/Мониторинг
- `core.infra.logging`: формат/теги, JSON‑логирование (опционально), корелляция
- `core.infra.monitors`: счётчики квот/метрики лимитера, health‑команды
- Хуки для экспорта метрик (stdout/Prometheus pushgateway — опционально)

#### 5) Тесты/CI
- `packages/core/tests` — unit/integration
- `apps/*/tests` — прикладные сценарии
- GitHub Actions (линты/тесты); анти‑спам проверки на PR (сохраняем)

---

### Proposed Repository Layout (monorepo)
```
/ (repo)
├─ packages/
│  └─ core/
│     ├─ pyproject.toml (или setup.cfg)
│     └─ core/
│        ├─ infra/
│        │  ├─ tele_client.py
│        │  ├─ limiter.py
│        │  ├─ logging.py
│        │  └─ monitors.py
│        ├─ domain/
│        │  └─ groups.py
│        ├─ config/
│        │  └─ loader.py
│        ├─ typing.py
│        └─ tests/
├─ apps/
│  ├─ s16-leads/
│  │  ├─ cli.py
│  │  ├─ commands/
│  │  ├─ services/ (seeders workflow)
│  │  └─ tests/
│  └─ gconf/
│     ├─ reports/
│     ├─ analytics/
│     └─ tests/
├─ docs/
│  ├─ GPT5_ARCHITECTURE_DISCUSSION.md (этот документ)
│  ├─ LEADS_SEEDERS_PLAYBOOK.md
│  └─ ...
└─ scripts/
```

---

### Public APIs (draft)
- `core.infra.tele_client.get_client(config: CoreConfig) -> TelegramClient`
- `core.infra.limiter`:
  - `RateLimiter`; `safe_call(callable, operation_type, ...)`
  - `smart_pause(operation_type, count)`
- `core.domain.groups.GroupManager`:
  - `get_group_info(group: str|int) -> GroupInfo`
  - `get_participants(group: str|int, limit: int) -> list[Participant]`
  - `search_participants(group: str|int, query: str, limit: int) -> list[Participant]`
  - `get_group_creation_date(group: str|int) -> datetime`
- `core.config.loader.load()` -> `CoreConfig` (api_id/hash, лимиты, квоты, теги логов)
- Событийная шина (опционально): `core.infra.events.emit(event)` для мониторинга/алертов

Контракты данных (минимум):
- `Participant { id:int, username:str|None, first_name:str|None, last_name:str|None, ... }`
- `GroupInfo { id:int, title:str, username:str|None, participants_count:int|None, ... }`

---

### Migration Plan (high‑level)
1) Подготовить пакет `core`: перенести `tele_client.py`, `limiter.py`, `GroupManager` в `packages/core/core/*` (с корректировкой импортов), добавить `logging.py`, `config.loader`.
2) Собрать минимальные тесты в `packages/core/tests` (перенос имеющихся + фиксы путей).
3) В `apps/s16-leads` перенести `src/cli.py` и прикладную логику (seeders сервисы) — импорты только из `core.*`.
4) Настроить локальную разработку: `pip install -e packages/core` и запуск `apps/s16-leads/cli.py`.
5) Перенести аналитические скрипты/отчёты в `gconf/` (из текущих `data/export` рабочих скриптов), оформить интерфейсы.
6) CI: линтеры/тесты для `core` и `apps` (раздельные job‑ы), публикация артефактов (опционально Internal PyPI).
7) Документация: ADR на ключевые решения; обновление README по запуску `apps/*`.

Риски/митигация:
- Разрыв импортов — поэтапный перенос + `pip install -e` для core
- Скрытые зависимые утилиты — инвентаризация через grep (Telethon usage, env loaders)
- Стабильность анти‑спам — тесты на `safe_call`/лимитер прежде чем выносить

---

### Non‑functional Requirements (NFR) & Policies
- Анти‑спам комплаенс — обязателен для всех приложений через `core`
- Логи — единый формат и теги (SAFE) + возможность JSON‑логирования
- Конфигурации — через `core.config`, без дублирования
- Безопасность — персональные TG‑данные не коммитить; снапшоты держать локально/в приватном хранилище
- Производительность — удерживать RPS/квоты конфигурируемыми

---

### Open Questions for GPT‑5
1) Monorepo vs multi‑repo: когда целесообразно выделять `gconf/` в отдельный репозиторий?
2) Событийная шина/observer в `core`: нужны ли domain events для мониторинга (e.g., `RateLimitExceeded`, `FloodWaitHandled`) и как их экспонировать?
3) Контракты API: где провести границу между `GroupManager` и прикладными сервисами (например, seeders/analytics)?
4) Версионирование core: SemVer + Internal PyPI vs локальная сборка? Требуются ли runtime feature‑flags для анти‑спам стратегии?
5) Observability: встроить ли Prometheus/TextfileExporter для квот/лимитов?
6) Конфиг: перейти на pydantic v2 и схемы валидации/генерацию `.env.sample`?

---

### Decision Drivers
- Повторное использование безопасной интеграции с Telegram
- Ускорение запуска новых приложений (линейка `apps/*`)
- Уменьшение регрессий за счёт unit‑тестов на уровне `core`
- Сокращение coupling’а, повышение читаемости и управляемости

---

### References
- Anti‑Spam System: SAFE wrappers, 4 RPS лимитер, backoff
- Playbook: `docs/LEADS_SEEDERS_PLAYBOOK.md`
- Политики: `s16 space` — референсная группа; не коммитить персональные данные в GitHub
