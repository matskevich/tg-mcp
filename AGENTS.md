# CLAUDE.md — контекст для AI-агентов

Этот файл — точка входа для Claude Code, Cline, Cursor и других AI-агентов.

## Что это за репозиторий

Монорепо с несколькими проектами, объединёнными общей Telegram-инфраструктурой:

| Проект | Путь | Описание |
|--------|------|----------|
| **gconf** | `gconf/` | Образовательный проект по AI (метанавыки, vibe coding) |
| **vahue** | `vahue/` | Проект ретритов/практик |
| **tganalytics** | `tganalytics/` | Telegram-инфраструктура (клиенты, rate limiting, anti-spam, exporters) |

## Куда идти за контекстом

### gconf
- **Главный контекст**: `gconf/CONTEXT.md` ← ЧИТАЙ ЭТО
- Точка входа для AI: `gconf/CLAUDE.md`
- Cursor rule: `.cursor/rules/67-gconf-project.md`
- Документация: `gconf/docs/`
- Аналитика: `gconf/analytics/`
- Приватные данные: `gconf/data/` (gitignored)

### vahue
- **Главный контекст**: `vahue/CONTEXT.md` ← ЧИТАЙ ЭТО
- Точка входа для AI: `vahue/CLAUDE.md`
- Cursor rule: `.cursor/rules/68-vahue-project.md`
- Документация: `vahue/docs/`
- Аналитика: `vahue/analytics/`
  - `vahue/analytics/satia/` — кампания satia (README.md, FILES.md)
- Приватные данные: `vahue/data/` (gitignored)

### Общая инфраструктура
- Архитектура: `.cursor/rules/60-arch-current.md`
- Telegram правила: `.cursor/rules/70-telegram-invariants.md`
- Data policy: `.cursor/rules/65-data-policy.md`

## Ключевые правила

1. **Проекты изолированы**: gconf и vahue — разные домены, не смешивать данные/метрики
2. **Telegram через tganalytics**: никаких прямых telethon импортов в проектном коде
3. **PII не коммитить**: все выгрузки в gitignored папках (`*/data/`, `*/analytics/raw/`)
4. **Blacklist обязателен**: при метриках участия исключать организаторов

## Структура проекта

```
/
├── tganalytics/            # Telegram-инфраструктура (ядро)
│   ├── tganalytics/        # пакет (clients, domain, exporters, antispam)
│   ├── examples/           # примеры использования
│   └── pyproject.toml
├── gconf/                  # проект gconf
│   ├── CONTEXT.md          # ← контекст для AI
│   ├── CLAUDE.md           # точка входа для AI-агентов
│   ├── docs/               # методология (коммитим)
│   ├── src/                # код
│   ├── analytics/          # Telegram-статистика (gitignored)
│   └── data/               # приватные данные (gitignored)
├── vahue/                  # проект vahue
│   ├── CONTEXT.md          # ← контекст для AI
│   ├── CLAUDE.md           # точка входа для AI-агентов
│   ├── docs/               # методология (если будет)
│   ├── src/                # код (если будет)
│   ├── analytics/          # Telegram-аналитика (gitignored)
│   │   └── satia/          # кампания satia
│   └── data/               # приватные данные (gitignored)
├── apps/                   # legacy apps (s16leads, etc)
├── data/                   # общие данные (sessions, logs)
├── .cursor/rules/          # Cursor rules
└── docs/                   # общие документы
```

## Команды

```bash
# gconf: список org-чатов
PYTHONPATH=. python3 gconf/src/tools/list_org_chats.py

# gconf: участники группы
PYTHONPATH=. python3 gconf/src/cli.py participants <group_id> --limit 100

# тесты
PYTHONPATH=. python3 -m pytest tests/ -q
```
