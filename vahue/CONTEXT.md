# vahue — контекст проекта

**Цель этого файла** — дать AI-агентам (Cursor, Cline, Claude) полную картину проекта vahue: что это, как устроено, какие правила.

---

## Что такое vahue

**vahue** — это проект по организации ретритов и практик (телесные/созерцательные практики, групповая работа). Не путать с gconf или s16-leads — это **отдельный домен** со своей аудиторией, метриками и данными.

### Продуктовая модель (кратко)

- **Ретриты**: многодневные интенсивы (Бали, Индия, etc)
- **Практики**: регулярные встречи (онлайн/офлайн)
- **Комьюнити**: Telegram-группы участников и выпускников
- Каждый ретрит — отдельная когорта с участниками и ценой

---

## Структура папки vahue/

```
vahue/
├── CONTEXT.md          # этот файл — контекст для AI
├── CLAUDE.md           # точка входа для AI-агентов
├── __init__.py         # package marker
├── docs/               # методология, описания практик (если нужно)
├── src/                # код (если будет vahue-specific логика)
├── analytics/          # рабочее пространство для Telegram-аналитики
│   ├── satia/          # кампания satia (Бали, февраль 2025)
│   │   ├── README.md
│   │   ├── FILES.md
│   │   ├── raw/        # сырые выгрузки (gitignored)
│   │   ├── processed/  # нормализованные данные (gitignored)
│   │   ├── notes/      # рабочие заметки, группы
│   │   └── scripts/    # скрипты обработки
│   └── (другие кампании...)
└── data/               # приватные runtime-артефакты (gitignored)
    └── sessions/       # vahue-specific session files (если нужны)
```

---

## Разделение: docs vs analytics

| Слой | Путь | Что там | Коммитим? |
|------|------|---------|-----------|
| **Docs** | `vahue/docs/` | Методология, описания, планы | Да |
| **Analytics workspace** | `vahue/analytics/` | Telegram-статистика, CRM, кампании | Нет (gitignored) |
| **Code** | `vahue/src/` | CLI, tools, pipelines | Да |
| **Private data** | `vahue/data/` | Sessions, приватные списки | Нет (gitignored) |

---

## Telegram-статистика: workflow

Стандартный flow для каждой кампании (на примере satia):

1. **Список групп** → `vahue/analytics/satia/notes/groups.txt`
2. **Экспорт участников** → `vahue/analytics/satia/raw/`
   - Используем общий экспортер: `examples/export_project_analytics.py`
3. **Нормализация** → `vahue/analytics/satia/processed/`
   - membership (участники групп + retreat_name + price_usd)
   - zoom (участники звонков)
   - bot signups (подписки на бота)
4. **Агрегация по людям** → CRM-файл с колонками:
   - `telegram_id`, `username`, `full_name`
   - `groups_count`, `spent_total_usd`, `deepness_level`
   - `retreats` (список ретритов)
5. **Матчинг источников** → cross-join CRM × Zoom × Bot
6. **Outreach** → DM-кампании, инвайты, ответы
7. **Summary** → MD-отчёт

### Naming convention

`YYMMDD__source__what__scope.ext`

Примеры:
- `260107_membership_satia_v1.tsv`
- `260107_people_crm_vahue_v1.tsv`
- `260107_satya_outreach_dms_v4.tsv`
- `260107_satya_invites_summary_v2.md`

---

## Кампании vahue

### satia (актуальная)
- **Папка**: `vahue/analytics/satia/`
- **Ретрит**: Satia Bali, февраль 2025
- **Источники данных**:
  - Zoom-звонок satya (регистранты/участники)
  - Telegram-бот chatplace (подписки)
  - Telegram-группы vahue (участники прошлых ретритов)
  - DM-диалоги (outreach-кампания)
- **Документация**: `vahue/analytics/satia/README.md`, `FILES.md`

---

## Cohorts vahue (примерная структура)

| retreat_name | Описание | price_usd | deepness_level |
|--------------|----------|-----------|----------------|
| `bali_2024_01` | Бали, январь 2024 | 3000 | 3 |
| `india_2024_09` | Индия, сентябрь 2024 | 2500 | 3 |
| `satia_bali_2025_02` | Satia Bali, февраль 2025 | 3500 | 3 |
| `practices_ongoing` | Регулярные практики | 0 | 1 |

(Уточнить реальные когорты при сборе данных)

---

## Команды

```bash
# Экспорт аналитики vahue в workspace
PYTHONPATH=. python3 examples/export_project_analytics.py \
  --workspace vahue/analytics/satia \
  --groups-file vahue/analytics/satia/notes/groups.txt \
  --participants-limit 2000 \
  --messages-limit 5000

# Создать Telegram-сессию (если нужна отдельная)
PYTHONPATH=. python3 examples/create_telegram_session.py --session-name vahue_bot
```

---

## Правила для AI-агента

1. **Не смешивать vahue и gconf** — это разные проекты
2. **PII не коммитить** — все выгрузки в gitignored папках (`vahue/analytics/*/raw/`, `vahue/analytics/*/processed/`)
3. **Telegram через tganalytics** — никаких прямых telethon импортов
4. **Формат выходов**: TSV для данных, MD для summary
5. **WORKLOG вести** — записывать что сделали и какие решения приняли (в `vahue/analytics/*/notes/`)
6. **Naming convention** — использовать `YYMMDD__source__what__scope.ext`

---

## Связанные файлы

- `.cursor/rules/68-vahue-project.md` — cursor rule для vahue
- `.cursor/rules/65-data-policy.md` — политика данных
- `.cursor/rules/60-arch-current.md` — общая архитектура
- `vahue/analytics/satia/README.md` — workflow satia-кампании
- `vahue/analytics/satia/FILES.md` — граф зависимостей файлов
