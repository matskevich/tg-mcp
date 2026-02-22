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
4. **Telegram write only via Action MCP** — direct `client.send_*` и `client.delete_messages` запрещены по умолчанию

## MCP Server

Read/Actions MCP tools для доступа к Telegram API:

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
| `tg_send_message` | Отправка сообщения (actions profile: dry_run -> approval_code -> confirm=true + confirmation_text) |
| `tg_send_file` | Отправка файла (actions profile: dry_run -> approval_code -> confirm=true + confirmation_text) |
| `tg_get_actions_policy` | Активные write-ограничения |

## Использование из другого проекта

Добавь в `.mcp.json` или `.claude/settings.json`:
```json
{
  "mcpServers": {
    "tganalytics": {
      "command": "/Users/dmitrymatskevich/tg-mcp/venv/bin/python3",
      "args": ["/Users/dmitrymatskevich/tg-mcp/tganalytics/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/dmitrymatskevich/tg-mcp/tganalytics:/Users/dmitrymatskevich/tg-mcp",
        "TG_SESSIONS_DIR": "/Users/dmitrymatskevich/tg-mcp/data/sessions"
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
