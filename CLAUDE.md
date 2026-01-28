# CLAUDE.md — контекст для AI-агентов

Этот файл — точка входа для Claude Code, Cline, Cursor и других AI-агентов.

## Что это за репозиторий

**tg-mcp** — MCP-сервер + Python-библиотека для работы с Telegram API.

Предоставляет:
- Telegram-клиенты с управлением сессиями
- Rate limiting и anti-spam защита (TokenBucket, safe_call, дневные квоты)
- Экспорт данных (участники, сообщения, группы)
- MCP-сервер для доступа из Claude Code

## Структура

```
/
├── tganalytics/            # Telegram-инфраструктура
│   ├── tganalytics/        # пакет (infra, domain, config)
│   ├── mcp_server.py       # MCP-сервер (9 tools)
│   ├── examples/           # примеры использования
│   └── pyproject.toml
├── tests/                  # тесты
├── scripts/                # утилиты (compliance, security)
├── docs/                   # документация
├── data/                   # runtime данные (gitignored)
│   ├── sessions/           # Telegram-сессии
│   ├── anti_spam/          # дневные счётчики
│   └── logs/
├── .cursor/rules/          # AI governance
├── .github/workflows/      # CI
├── .mcp.json               # MCP конфигурация
└── requirements.txt
```

## Ключевые правила

1. **Все Telegram-вызовы через safe_call** — никаких прямых telethon вызовов
2. **PII не коммитить** — все выгрузки в gitignored папках
3. **Session-файлы защищены** — chmod 700/600, не коммитить

## MCP Server

9 tools для доступа к Telegram API:

| Tool | Назначение |
|------|------------|
| `tg_list_sessions` | Список сессий |
| `tg_use_session` | Переключить сессию |
| `tg_get_group_info` | Инфо о группе |
| `tg_get_participants` | Участники группы |
| `tg_search_participants` | Поиск участников |
| `tg_get_messages` | Сообщения |
| `tg_get_message_count` | Количество сообщений |
| `tg_get_group_creation_date` | Дата создания группы |
| `tg_get_stats` | Статистика anti-spam |

## Использование из другого проекта

Добавь в `.mcp.json` или `.claude/settings.json`:
```json
{
  "mcpServers": {
    "telegram": {
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
# тесты
PYTHONPATH=tganalytics:. python3 -m pytest tests/ -q

# MCP server (ручной запуск для отладки)
PYTHONPATH=tganalytics:. venv/bin/python3 tganalytics/mcp_server.py

# проверка anti-spam compliance
python3 scripts/check_anti_spam_compliance.py
```

## Документация

- `docs/ANTISPAM_SECURITY.md` — архитектура антиспам-системы
- `docs/ANTISPAM_IMPROVEMENTS_PLAN.md` — план улучшений
- `.cursor/rules/70-telegram-invariants.md` — обязательные правила
