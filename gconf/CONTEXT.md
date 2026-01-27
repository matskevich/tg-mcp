# gconf — контекст проекта

**Цель этого файла** — дать AI-агентам (Cursor, Cline, Claude) полную картину проекта gconf: что это, как устроено, какие правила.

---

## Что такое gconf

**gconf** — это образовательный проект/комьюнити по AI (конференции, потоки, практики). Не путать с s16-leads или vahue — это **отдельный домен** со своей аудиторией, метриками и данными.

### Продуктовая модель (кратко)

- **Метанавыки (0→GPT)**: человек учится работать с AI как с партнёром, а не слугой
- **Vibe Coding**: сборка прототипов вместе с GPT (не "курс по коду")
- **Библиотека связок**: 1000+ готовых AI-связок для разных задач
- Подробнее: `gconf/docs/product-overview.md`, `gconf/docs/framework.md`

### Ключевые концепции

- **Фреймворк**: РАЗГОН → ПЛАНИРОВАНИЕ → ПРОМПТ=ТЗ → EXECUTION → FEEDBACK
- **Метанавыки**: любопытство, relational approach, AI-first, микро-эксперименты
- **Антипаттерны**: "сделай магию", прыжок в исполнение, бесконечный разгон

---

## Структура папки gconf/

```
gconf/
├── CONTEXT.md          # этот файл — контекст для AI
├── __init__.py         # package marker
├── app/                # конфиги и samples (без PII)
│   ├── config.py
│   ├── config.sample.yaml
│   └── blacklist.sample.csv
├── docs/               # evergreen методология/планы (НЕ аналитика)
│   ├── product-overview.md
│   ├── framework.md
│   ├── gconf-q1-2026-plan.md
│   ├── skills.md
│   ├── patterns-antipatterns.md
│   └── ...
├── src/                # код (CLI, tools, pipelines)
│   ├── cli.py
│   └── tools/
│       ├── blacklist.py
│       ├── create_session.py
│       ├── list_org_chats.py
│       └── client_profile.py
├── analytics/          # рабочее пространство для Telegram-статистики
│   ├── README.md
│   ├── raw/            # сырые выгрузки (gitignored)
│   ├── processed/      # нормализованные данные (gitignored)
│   ├── notes/          # рабочие заметки, WORKLOG, группы
│   └── scripts/        # скрипты обработки
├── data/               # приватные runtime-артефакты (gitignored)
│   ├── sessions/       # Telegram .session файлы
│   ├── blacklist.global.csv
│   ├── blacklist.per_event.csv
│   └── events_keymap.json
└── export/             # выходные отчёты (gitignored, без PII)
```

---

## Разделение: docs vs analytics

| Слой | Путь | Что там | Коммитим? |
|------|------|---------|-----------|
| **Evergreen docs** | `gconf/docs/` | Методология, фреймворки, планы, vision | Да |
| **Analytics workspace** | `gconf/analytics/` | Telegram-статистика, когорты, membership | Нет (gitignored) |
| **Code** | `gconf/src/` | CLI, tools, pipelines | Да |
| **Config samples** | `gconf/app/` | Примеры конфигов, blacklist.sample | Да |
| **Private data** | `gconf/data/` | Реальные blacklist, sessions | Нет (gitignored) |

---

## Blacklist — исключения из статистики

Blacklist нужен чтобы **исключить организаторов/волонтёров** из метрик участия.

### Файлы (в `gconf/data/`)

- `blacklist.global.csv` — глобальные исключения (организаторы)
  - колонки: `id,reason,policy`
  - policy `exclude_all` — исключить отовсюду
- `blacklist.per_event.csv` — исключения по конкретным ивентам
  - колонки: `id,event_key,policy,reason`
  - policies: `invited_free`, `volunteer`, `protagonist`, `exclude_all`
- `events_keymap.json` — маппинг event_key ↔ human-readable label

### Код

`gconf/src/tools/blacklist.py` — класс `Blacklist`:
- `apply_attendance(user_id, event_key)` → bool (включать в метрики?)
- `exclude_from_paid(user_id, event_key)` → bool (исключать из платных?)

---

## Telegram-статистика: workflow

По аналогии с `vahue/satia/`:

1. **Список групп** → `gconf/analytics/notes/groups.txt`
2. **Экспорт участников** → `gconf/analytics/raw/` (через `gconf/src/tools/`)
3. **Нормализация** → `gconf/analytics/processed/`
4. **Агрегация по людям** → TSV с колонками:
   - `telegram_id`, `username`, `full_name`
   - `spent_total_usd`, `events_count`, `deepness_sum`, `deepness_max`
   - `cohorts`, `events` (список ивентов)
5. **Summary** → MD-отчёт

### Naming convention

`YYMMDD__source__what__scope.ext`

Примеры:
- `260126_membership_gconf_v1.tsv`
- `260126_people_crm_gconf_v1.tsv`
- `260126_cohorts_summary_v1.md`

---

## Когорты gconf (примерная структура)

| cohort_key | Описание | price_usd | deepness |
|------------|----------|-----------|----------|
| `meta_skills_N` | Поток метанавыков #N | 500 | 2 |
| `vibe_coding_N` | Поток vibe coding #N | 1000 | 3 |
| `open_event` | Открытые эфиры/вебинары | 0 | 1 |
| `library_access` | Доступ к библиотеке связок | 100 | 1 |

(Уточнить реальные когорты при сборе данных)

---

## Команды CLI

```bash
# Создать/обновить сессию
python3 gconf/src/tools/create_session.py

# Получить список org-чатов
python3 gconf/src/tools/list_org_chats.py

# CLI по группе
python3 gconf/src/cli.py info <group_id>
python3 gconf/src/cli.py participants <group_id> --limit 100
python3 gconf/src/cli.py export <group_id> --output gconf/analytics/raw/export.json
```

---

## Правила для AI-агента

1. **Не смешивать gconf и vahue** — это разные проекты
2. **PII не коммитить** — все выгрузки в gitignored папках
3. **Blacklist обязателен** — применять при любых метриках участия
4. **Telegram через tganalytics** — никаких прямых telethon импортов
5. **Формат выходов**: TSV для данных, MD для summary
6. **WORKLOG вести** — записывать что сделали и какие решения приняли

---

## Связанные файлы

- `.cursor/rules/67-gconf-project.md` — cursor rule для gconf
- `.cursor/rules/65-data-policy.md` — политика данных
- `.cursor/rules/66-gconf-separation.md` — разделение gconf/s16
- `gconf/docs/*` — методология и планы
