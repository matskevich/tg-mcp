# TG Analytics

Telegram Analytics infrastructure for data collection, rate limiting, anti-spam, and analytics.

## What is this?

**TG Analytics** is a Python library providing core infrastructure for working with Telegram:

- **Telegram clients** with session management
- **Rate limiting** and anti-spam protection
- **Data exporters** (participants, messages, groups)
- **Domain models** (GroupManager, participants, metrics)
- **Examples** for common use cases

## Structure

```
tganalytics/
├── tganalytics/            # Core package
│   ├── infra/              # Infrastructure (clients, rate limiting, metrics)
│   ├── domain/             # Domain models (groups, participants)
│   ├── config/             # Configuration
│   └── __init__.py
├── examples/               # Usage examples
└── pyproject.toml
```

## Projects using TG Analytics

This monorepo also contains projects that use TG Analytics:

- **gconf/** — Educational AI project (meta-skills, vibe coding)
- **vahue/** — Retreats and practices project

Each project has its own:
- `CONTEXT.md` — Full project context
- `CLAUDE.md` — Entry point for AI agents
- `analytics/` — Telegram analytics workspace (gitignored)
- `data/` — Private data (gitignored)

## Installation

### Option 1: Editable install (development)

```bash
pip install -e tganalytics/
```

### Option 2: PYTHONPATH (quick start)

```bash
export PYTHONPATH=tganalytics:\$PYTHONPATH
```

## Usage

```python
from tganalytics.infra.tele_client import get_client_for_session
from tganalytics.domain.groups import GroupManager

# Get Telegram client
client = get_client_for_session("my_session")

# Export participants
manager = GroupManager(client)
participants = await manager.get_participants(group_id, limit=100)
```

See `tganalytics/examples/` for more examples.

## Running tests

```bash
PYTHONPATH=tganalytics:. python3 -m pytest tests/ -v
```

## Documentation

- [CLAUDE.md](CLAUDE.md) — Entry point for AI agents
- [gconf/CONTEXT.md](gconf/CONTEXT.md) — gconf project context
- [vahue/CONTEXT.md](vahue/CONTEXT.md) — vahue project context
- `.cursor/rules/` — Cursor AI rules

## Architecture principles

1. **Projects are isolated**: gconf and vahue are separate domains
2. **Telegram via tganalytics**: No direct telethon imports in project code
3. **PII protection**: All exports in gitignored folders
4. **Rate limiting**: Built-in anti-spam and flood protection

## License

MIT
