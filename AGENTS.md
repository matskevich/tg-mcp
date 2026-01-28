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

## MCP Server (tganalytics)

Read-only MCP сервер для доступа к Telegram API из Claude Code.

- **Код**: `tganalytics/mcp_server.py` (147 строк, 9 tools)
- **Конфиг**: `.mcp.json` (stdio transport, venv/bin/python3)
- **Python**: 3.12 через Homebrew (`/opt/homebrew/bin/python3.12`), venv пересоздан
- **Дефолтная сессия**: `gconf_support`

### Статус (2026-01-28)

**Готово:**
- `mcp_server.py` написан, все 9 tools зарегистрированы (проверено)
- `.mcp.json` создан с правильными путями
- `requirements.txt` обновлён (`mcp>=1.0.0`)
- Python 3.12 установлен, venv пересоздан, все зависимости установлены
- Импорты проверены — всё работает

**Нужно сделать:**
- Перезапустить Claude Code чтобы MCP сервер подхватился
- Проверить `/mcp` — должен быть виден `tganalytics` с 9 tools
- Протестировать `tg_list_sessions` → должен показать `[dmatskevich, gconf_support, s16_session]`
- Протестировать `tg_use_session("dmatskevich")` → переключение сессии
- Протестировать `tg_get_group_info` на реальной группе

### Tools

| Tool | Параметры | Назначение |
|------|-----------|------------|
| `tg_list_sessions` | — | Список сессий в `data/sessions/` |
| `tg_use_session` | `session_name` | Переключить сессию |
| `tg_get_group_info` | `group` | Инфо о группе |
| `tg_get_participants` | `group, limit?=100` | Участники группы |
| `tg_search_participants` | `group, query, limit?=50` | Поиск участников |
| `tg_get_messages` | `group, limit?=100, min_id?=0` | Сообщения |
| `tg_get_message_count` | `group` | Количество сообщений |
| `tg_get_group_creation_date` | `group` | Дата создания группы |
| `tg_get_stats` | — | Статистика anti-spam |

### Использование из другого проекта

```json
{
  "mcpServers": {
    "tganalytics": {
      "command": "/Users/dmitrymatskevich/tganalytics/venv/bin/python3",
      "args": ["/Users/dmitrymatskevich/tganalytics/tganalytics/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/dmitrymatskevich/tganalytics/tganalytics:/Users/dmitrymatskevich/tganalytics",
        "TG_SESSIONS_DIR": "/Users/dmitrymatskevich/tganalytics/data/sessions"
      }
    }
  }
}
```

## Команды

```bash
# gconf: список org-чатов
PYTHONPATH=. python3 gconf/src/tools/list_org_chats.py

# gconf: участники группы
PYTHONPATH=. python3 gconf/src/cli.py participants <group_id> --limit 100

# тесты
PYTHONPATH=. python3 -m pytest tests/ -q

# MCP server (ручной запуск для отладки)
PYTHONPATH=tganalytics:. venv/bin/python3 tganalytics/mcp_server.py
```
