# scope: project
# priority: 68

## vahue project rules

vahue — проект ретритов и практик (телесные/созерцательные практики, комьюнити). **Не путать с gconf или s16-leads.**

### структура

- `vahue/docs/` — методология (если будет)
- `vahue/src/` — код (если будет vahue-specific логика)
- `vahue/analytics/` — рабочее пространство для Telegram-аналитики (gitignored)
  - `vahue/analytics/satia/` — кампания satia (Бали, февраль 2025)
  - (другие кампании...)
- `vahue/data/` — приватные артефакты (sessions, списки) (gitignored)

### контекст

**Читай `vahue/CONTEXT.md`** — там полное описание проекта, структуры, workflow.

### правила

1. **разделение данных**
   - evergreen docs → `vahue/docs/`
   - analytics/кампании → `vahue/analytics/`
   - не смешивать

2. **telegram через tganalytics**
   - никаких прямых telethon импортов в `vahue/*`
   - использовать `from tganalytics.infra.tele_client import get_client_for_session`
   - использовать `from tganalytics.domain.groups import GroupManager`

3. **формат выходов**
   - данные: TSV (tab-separated)
   - summary: Markdown
   - naming: `YYMMDD__source__what__scope_vN.ext`

4. **pii policy**
   - не коммитить: `vahue/analytics/*/raw/`, `vahue/analytics/*/processed/`, `vahue/data/`
   - все выгрузки gitignored
   - в MD-summary избегать PII где возможно

5. **worklog**
   - вести `vahue/analytics/*/notes/WORKLOG.md` для каждой кампании
   - записывать: что экспортировали, какие решения приняли, какие файлы создали

### кампании vahue

Текущие кампании:
- **satia** (`vahue/analytics/satia/`) — ретрит Satia Bali (февраль 2025)
  - Документация: README.md, FILES.md
  - Группы: notes/groups.txt
  - WORKLOG: notes/WORKLOG.md

### cohorts vahue (примерная структура)

типичные когорты (уточнить при сборе):
- `bali_2024_01` — ретрит Бали (январь 2024)
- `india_2024_09` — ретрит Индия (сентябрь 2024)
- `satia_bali_2025_02` — ретрит Satia Bali (февраль 2025)
- `practices_ongoing` — регулярные практики

### команды

```bash
# экспорт аналитики vahue
PYTHONPATH=. python3 examples/export_project_analytics.py \
  --workspace vahue/analytics/satia \
  --groups-file vahue/analytics/satia/notes/groups.txt \
  --participants-limit 2000
```

### связанные правила

- `65-data-policy.md` — общая политика данных
- `66-gconf-separation.md` — разделение gconf/vahue/s16
- `70-telegram-invariants.md` — Telegram инварианты
