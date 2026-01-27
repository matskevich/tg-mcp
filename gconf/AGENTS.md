# gconf — CLAUDE.md

**Если работаешь с проектом gconf — читай `CONTEXT.md` в этой же папке.**

```
gconf/CONTEXT.md  ← полный контекст проекта
```

## Быстрая справка

- **gconf** = образовательный проект по AI (метанавыки, vibe coding, библиотека связок)
- **Не путать с vahue** — это разные проекты

### Структура

| Папка | Что там |
|-------|---------|
| `docs/` | Evergreen методология (фреймворки, планы) |
| `src/` | Код (CLI, tools) |
| `analytics/` | Telegram-статистика (gitignored) |
| `data/` | Приватные данные, blacklist (gitignored) |

### Blacklist

При любых метриках — применять blacklist для исключения организаторов:

```python
from gconf.src.tools.blacklist import Blacklist
bl = Blacklist()
if bl.apply_attendance(user_id, event_key):
    # включить в статистику
```

### Команды

```bash
# список org-чатов
PYTHONPATH=. python3 gconf/src/tools/list_org_chats.py

# участники группы
PYTHONPATH=. python3 gconf/src/cli.py participants <group_id> --limit 100
```

---

**Полный контекст: `gconf/CONTEXT.md`**
