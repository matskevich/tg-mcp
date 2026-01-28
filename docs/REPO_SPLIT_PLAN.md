# План: tganalytics → tg-mcp

## Что делаем

Текущий монорепо `tganalytics` → чистый репо `tg-mcp` (MCP-сервер + Telegram-библиотека).
gconf и vahue → отдельные папки/репо, подключают tg-mcp как MCP-сервер.

---

## Шаг 1: Вынести gconf и vahue из репо

Скопировать в отдельные папки на диске (пока без git):
```
~/gconf/          ← из gconf/
~/vahue/          ← из vahue/
```

Что копируем:
- `gconf/` → `~/gconf/` (целиком: src, app, docs, analytics, data, CONTEXT.md, CLAUDE.md)
- `vahue/` → `~/vahue/` (целиком: src, app, docs, analytics, data, CONTEXT.md, CLAUDE.md)

После копирования — удалить из текущего репо:
```
rm -rf gconf/ vahue/
```

---

## Шаг 2: Удалить legacy и мусор

Удалить из репо:
```
apps/                              # legacy приложения (пустые/устаревшие)
src/                               # старый shared source (заменён tganalytics/)
packages/                          # пустая директория
memory_bank/                       # локальный контекст AI (не нужен в репо)
config/                            # старые конфиги (проверить, нужно ли что-то)

# legacy файлы в корне
export_3_jsons.py
export_tantra_men_csv.py
s16_coliving_all_participants.json
s16_coliving_participants.json
s16_space_all_participants.json
page.html
s16-leads.code-workspace

# миграционные доки (уже выполнены)
PROJECT_MAP.md
PROJECT_MAP_AND_RENAME_PLAN.md
IMPORT_REWRITE.md
MIGRATION_PLAN.md
MOVE_MAP.md
PROPOSED_TREE.md
QUICK_TRANSFER_CHECKLIST.md
GITHUB_RENAME_INSTRUCTIONS.md
RENAME_INSTRUCTIONS.md
```

---

## Шаг 3: Почистить docs/

Оставить только релевантные для tg-mcp:
```
docs/
├── ANTISPAM_SECURITY.md           # ← оставить
├── ANTISPAM_IMPROVEMENTS_PLAN.md  # ← оставить
├── SECURITY.md                    # ← оставить
├── TELEGRAM_API_PATTERNS.md       # ← оставить
├── SAFE_EXPORT_STRATEGY.md        # ← оставить
├── EXPORT_MESSAGES_GUIDE.md       # ← оставить
├── adr/                           # ← оставить (архитектурные решения)
└── ...остальное проверить
```

Удалить доки, специфичные для gconf/vahue/s16leads/tantra/coliving.

---

## Шаг 4: Почистить .cursor/rules/

Оставить общие правила для tg-mcp:
```
00-constitution.md                 # ← оставить (общие принципы AI)
04-style-lowercase.md              # ← оставить
60-arch-current.md                 # ← ПЕРЕПИСАТЬ (убрать gconf/vahue, описать tg-mcp)
65-data-policy.md                  # ← оставить
70-telegram-invariants.md          # ← оставить
75-observability.md                # ← оставить
```

Удалить:
```
05-persona-wise-pro.md             # ← специфичное
66-gconf-separation.md             # ← gconf-specific
67-gconf-project.md                # ← gconf-specific
68-vahue-project.md                # ← vahue-specific
```

---

## Шаг 5: Почистить .gitignore

Убрать строки про gconf/vahue:
```diff
- gconf/data/
- gconf/export/
- gconf/analytics/
- vahue/data/
- vahue/export/
- vahue/analytics/
```

Оставить общие: `data/`, `*.session`, `venv/`, etc.

---

## Шаг 6: Обновить корневые файлы

- **CLAUDE.md** — переписать: это tg-mcp, MCP-сервер для Telegram
- **README.md** — переписать: описание tg-mcp, как подключить, как использовать
- **.mcp.json** — оставить как есть (уже корректный)
- **requirements.txt** — оставить как есть
- **Makefile** — проверить, убрать gconf/vahue таргеты если есть
- **.github/workflows/** — обновить ci.yaml (убрать ссылки на packages/tg_core, apps/)
- **.pre-commit-config.yaml** — оставить

---

## Шаг 7: Переименовать репо на GitHub

```bash
# На GitHub: Settings → Repository name → tg-mcp
# Или через gh cli:
gh repo rename tg-mcp
```

GitHub автоматически создаст redirect с `tganalytics` → `tg-mcp`.

Локально обновить remote:
```bash
git remote set-url origin git@github.com:dmatskevich/tg-mcp.git
```

---

## Шаг 8: Настроить gconf как отдельный проект

В `~/gconf/`:
1. `git init`
2. Добавить `.claude/settings.json` с MCP-подключением:
```json
{
  "mcpServers": {
    "telegram": {
      "command": "python3",
      "args": ["/Users/dmitrymatskevich/tg-mcp/tganalytics/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/dmitrymatskevich/tg-mcp/tganalytics:.",
        "TG_SESSIONS_DIR": "/Users/dmitrymatskevich/tg-mcp/data/sessions"
      }
    }
  }
}
```
3. Перенести cursor rules: `67-gconf-project.md`, `66-gconf-separation.md`
4. Свой `CLAUDE.md`, `README.md`
5. `gh repo create gconf --private`

---

## Итоговая структура tg-mcp

```
tg-mcp/
├── tganalytics/
│   ├── tganalytics/          # библиотека (infra, domain, config)
│   ├── mcp_server.py         # MCP-сервер
│   ├── examples/             # примеры
│   └── pyproject.toml
├── tests/                    # тесты
├── scripts/                  # утилиты (compliance, security, etc.)
├── docs/                     # документация
├── data/                     # runtime данные (gitignored)
│   ├── sessions/
│   ├── anti_spam/
│   └── logs/
├── .cursor/rules/            # AI governance
├── .github/workflows/        # CI
├── .mcp.json
├── .gitignore
├── .env.sample
├── requirements.txt
├── Makefile
├── CLAUDE.md
└── README.md
```

---

## Порядок выполнения

| # | Что | Риск |
|---|-----|------|
| 1 | Скопировать gconf/ и vahue/ в ~/gconf/ и ~/vahue/ | нулевой — копия |
| 2 | Удалить из репо gconf/, vahue/, apps/, legacy | средний — коммит с удалением |
| 3 | Почистить docs/, .cursor/rules/, .gitignore | низкий |
| 4 | Обновить CLAUDE.md, README.md, ci.yaml | низкий |
| 5 | Коммит + пуш | низкий |
| 6 | Переименовать репо на GitHub | низкий (redirect автоматический) |
| 7 | Настроить gconf как отдельный проект | отдельная задача |

Шаги 1-6 можно сделать за одну сессию. Шаг 7 — отдельно.
