# scope: project
# priority: 67

## gconf project rules

gconf — образовательный проект по AI (метанавыки, vibe coding, библиотека связок). **Не путать с vahue или s16-leads.**

### структура

- `gconf/docs/` — evergreen методология (фреймворки, планы, vision)
- `gconf/src/` — код (CLI, tools, pipelines)
- `gconf/app/` — конфиги и samples
- `gconf/analytics/` — рабочее пространство для Telegram-статистики (gitignored)
- `gconf/data/` — приватные артефакты (sessions, blacklist) (gitignored)
- `gconf/export/` — выходные отчёты (gitignored)

### контекст

**Читай `gconf/CONTEXT.md`** — там полное описание проекта, структуры, blacklist, workflow.

### правила

1. **разделение данных**
   - evergreen docs → `gconf/docs/`
   - analytics/статистика → `gconf/analytics/`
   - не смешивать

2. **blacklist обязателен**
   - при любых метриках участия применять `gconf/src/tools/blacklist.py`
   - организаторы/волонтёры не должны попадать в статистику
   - файлы blacklist: `gconf/data/blacklist.*.csv`

3. **telegram через tganalytics**
   - никаких прямых telethon импортов в `gconf/*`
   - использовать `from tganalytics.infra.tele_client import get_client_for_session`
   - использовать `from tganalytics.domain.groups import GroupManager`

4. **формат выходов**
   - данные: TSV (tab-separated)
   - summary: Markdown
   - naming: `YYMMDD__source__what__scope_vN.ext`

5. **pii policy**
   - не коммитить: `gconf/analytics/raw/`, `gconf/analytics/processed/`, `gconf/data/`
   - все выгрузки gitignored
   - в MD-summary избегать PII где возможно

6. **worklog**
   - вести `gconf/analytics/notes/WORKLOG.md`
   - записывать: что экспортировали, какие решения приняли, какие файлы создали

### когорты gconf

типичные когорты (уточнить при сборе):
- `meta_skills_N` — поток метанавыков
- `vibe_coding_N` — поток vibe coding
- `open_event` — открытые эфиры
- `library_access` — доступ к библиотеке

### команды

```bash
# создать сессию
python3 gconf/src/tools/create_session.py

# список org-чатов
python3 gconf/src/tools/list_org_chats.py

# экспорт участников
python3 gconf/src/cli.py participants <group_id> --limit 100
```

### связанные правила

- `65-data-policy.md` — общая политика данных
- `66-gconf-separation.md` — разделение gconf/s16
- `70-telegram-invariants.md` — Telegram инварианты
