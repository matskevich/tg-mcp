# vahue — CLAUDE.md

**Если работаешь с проектом vahue — читай `CONTEXT.md` в этой же папке.**

```
vahue/CONTEXT.md  ← полный контекст проекта
```

## Быстрая справка

- **vahue** = проект ретритов и практик (телесные/созерцательные практики)
- **Не путать с gconf** — это разные проекты

### Структура

| Папка | Что там |
|-------|---------|
| `docs/` | Методология (если будет) |
| `src/` | Код (если будет vahue-specific логика) |
| `analytics/` | Telegram-аналитика, CRM, кампании (gitignored) |
| `data/` | Приватные данные, sessions (gitignored) |

### Кампании

Каждая кампания — отдельная папка в `analytics/`:

- **satia**: `vahue/analytics/satia/` — ретрит Satia Bali (февраль 2025)
  - README.md, FILES.md — документация
  - raw/ — сырые выгрузки
  - processed/ — обработанные данные
  - notes/ — заметки, WORKLOG

### Команды

```bash
# экспорт аналитики vahue
PYTHONPATH=. python3 examples/export_project_analytics.py \
  --workspace vahue/analytics/satia \
  --groups-file vahue/analytics/satia/notes/groups.txt \
  --participants-limit 2000
```

---

**Полный контекст: `vahue/CONTEXT.md`**
