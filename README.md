# tg-mcp

MCP server + Python library for Telegram API with built-in rate limiting, anti-spam protection, and session management.

## What is this?

**tg-mcp** provides:
- **MCP server** — 9 tools for accessing Telegram API from Claude Code
- **Rate limiting** — Token bucket (4 RPS), daily quotas (20 DM/day, 20 joins/day)
- **Anti-spam** — FLOOD_WAIT retry with exponential backoff
- **Session security** — chmod 700/600 hardening for session files
- **Data exporters** — participants, messages, groups, dialogs

## Quick Start

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.sample .env
# Edit .env with your TG_API_ID, TG_API_HASH

# Run tests
PYTHONPATH=tganalytics:. python3 -m pytest tests/ -q
```

## MCP Server

Add to your project's `.mcp.json`:
```json
{
  "mcpServers": {
    "telegram": {
      "command": "path/to/tg-mcp/venv/bin/python3",
      "args": ["path/to/tg-mcp/tganalytics/mcp_server.py"],
      "env": {
        "PYTHONPATH": "path/to/tg-mcp/tganalytics:path/to/tg-mcp",
        "TG_SESSIONS_DIR": "path/to/tg-mcp/data/sessions"
      }
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `tg_list_sessions` | List available Telegram sessions |
| `tg_use_session` | Switch active session |
| `tg_get_group_info` | Get group/channel info |
| `tg_get_participants` | Export group members |
| `tg_search_participants` | Search members by query |
| `tg_get_messages` | Export messages |
| `tg_get_message_count` | Get message count |
| `tg_get_group_creation_date` | Get group creation date |
| `tg_get_stats` | Anti-spam system stats |

## Structure

```
tganalytics/
├── tganalytics/        # Core package
│   ├── infra/          # Clients, rate limiting, metrics
│   ├── domain/         # GroupManager, participants
│   └── config/         # Configuration
├── mcp_server.py       # MCP server entry point
└── examples/           # Usage examples
```

## Architecture

All Telegram API calls go through a 5-layer protection chain:

```
_safe_api_call → safe_call → TokenBucket → Telegram API
                    ↓            ↓              ↓
              DM/join quotas   4 RPS    FLOOD_WAIT retry + backoff
```

See [docs/ANTISPAM_SECURITY.md](docs/ANTISPAM_SECURITY.md) for details.

## License

MIT
