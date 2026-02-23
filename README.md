# tg-mcp

MCP server + Python library for Telegram API with built-in rate limiting, anti-spam protection, and session management.

## What is this?

**tg-mcp** provides:
- **Two MCP servers** — `Read` and `Actions` profiles with different risk levels
- **Rate limiting** — Token bucket (4 RPS), daily quotas (20 DM/day, 20 joins/day)
- **Multi-process protection** — optional shared RPS limiter across projects/processes
- **Anti-spam** — FLOOD_WAIT retry with exponential backoff
- **Circuit breaker** — auto cooldown after long FLOOD_WAIT events
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

## Agent Onboarding

Start here if this repository will be used by other AI agents/operators:

- [Agent Playbook](docs/AGENT_PLAYBOOK.md) - execution flows, error handling, batch workflow
- [Action Policy Toggles](docs/ACTION_POLICY_TOGGLES.md) - what can be toggled and safe change procedure
- [Anti-spam and Security Model](docs/ANTISPAM_SECURITY.md) - deeper technical details

## Installation Profiles

Use one repository, choose profile by risk level:

- `read` profile: installs only `tgmcp-read` (recommended default for new users)
- `full` profile: installs `tgmcp-read` + `tgmcp-actions`

Generate config:

```bash
# prereq check
bash scripts/check_tg_mcp.sh /absolute/path/to/tg-mcp

# read-only config (safe default)
python3 scripts/render_mcp_config.py \
  --repo /absolute/path/to/tg-mcp \
  --profile read

# full config (read + actions)
python3 scripts/render_mcp_config.py \
  --repo /absolute/path/to/tg-mcp \
  --profile full \
  --read-session-name my_read \
  --actions-session-name my_actions
```

## MCP Servers

Add to your project's `.mcp.json`:
```json
{
  "mcpServers": {
    "tgmcp-read": {
      "command": "path/to/tg-mcp/venv/bin/python3",
      "args": ["path/to/tg-mcp/tganalytics/mcp_server_read.py"],
      "env": {
        "PYTHONPATH": "path/to/tg-mcp/tganalytics:path/to/tg-mcp",
        "TG_SESSIONS_DIR": "path/to/tg-mcp/data/sessions",
        "TG_SESSION_PATH": "path/to/tg-mcp/data/sessions/my_read.session",
        "TG_ALLOW_SESSION_SWITCH": "0",
        "TG_BLOCK_DIRECT_TELETHON_WRITE": "1",
        "TG_ALLOW_DIRECT_TELETHON_WRITE": "0",
        "TG_ENFORCE_ACTION_PROCESS": "1",
        "TG_DIRECT_TELETHON_WRITE_ALLOWED_CONTEXTS": "actions_mcp",
        "TG_WRITE_CONTEXT": "read_mcp",
        "TG_ACTION_PROCESS": "0",
        "TG_SESSION_LOCK_MODE": "shared",
        "TG_GLOBAL_RPS_MODE": "shared"
      }
    },
    "tgmcp-actions": {
      "command": "path/to/tg-mcp/venv/bin/python3",
      "args": ["path/to/tg-mcp/tganalytics/mcp_server_actions.py"],
      "env": {
        "PYTHONPATH": "path/to/tg-mcp/tganalytics:path/to/tg-mcp",
        "TG_SESSIONS_DIR": "path/to/tg-mcp/data/sessions",
        "TG_SESSION_PATH": "path/to/tg-mcp/data/sessions/my_actions.session",
        "TG_ALLOW_SESSION_SWITCH": "0",
        "TG_ACTIONS_ENABLED": "1",
        "TG_ACTIONS_REQUIRE_ALLOWLIST": "1",
        "TG_ACTIONS_ALLOWED_GROUPS": "my_safe_group,-1001234567890",
        "TG_ACTIONS_MAX_MESSAGE_LEN": "2000",
        "TG_ACTIONS_MAX_FILE_MB": "20",
        "TG_ACTIONS_REQUIRE_CONFIRMATION_TEXT": "1",
        "TG_ACTIONS_CONFIRMATION_PHRASE": "отправляй",
        "TG_ACTIONS_MIN_CONFIRM_TEXT_LEN": "6",
        "TG_ACTIONS_REQUIRE_APPROVAL_CODE": "1",
        "TG_ACTIONS_APPROVAL_TTL_SEC": "1800",
        "TG_ACTIONS_APPROVAL_MIN_AGE_SEC": "30",
        "TG_ACTIONS_APPROVAL_FILE": "data/anti_spam/action_approvals.json",
        "TG_ACTIONS_IDEMPOTENCY_ENABLED": "1",
        "TG_ACTIONS_IDEMPOTENCY_WINDOW_SEC": "86400",
        "TG_ACTIONS_BATCH_FILE": "data/anti_spam/action_batches.json",
        "TG_ACTIONS_BATCH_TTL_HOURS": "168",
        "TG_ACTIONS_BATCH_APPROVAL_LEASE_SEC": "86400",
        "TG_ACTIONS_BATCH_RUN_LEASE_SEC": "1800",
        "TG_ACTIONS_UNSAFE_OVERRIDE": "0",
        "TG_BLOCK_DIRECT_TELETHON_WRITE": "1",
        "TG_ALLOW_DIRECT_TELETHON_WRITE": "0",
        "TG_ENFORCE_ACTION_PROCESS": "1",
        "TG_DIRECT_TELETHON_WRITE_ALLOWED_CONTEXTS": "actions_mcp",
        "TG_WRITE_CONTEXT": "actions_mcp",
        "TG_ACTION_PROCESS": "1",
        "TG_SESSION_LOCK_MODE": "shared",
        "TG_GLOBAL_RPS_MODE": "shared",
        "TG_FLOOD_CIRCUIT_THRESHOLD_SEC": "300",
        "TG_FLOOD_CIRCUIT_COOLDOWN_SEC": "900",
        "MAX_GROUP_MSGS_PER_DAY": "30"
      }
    }
  }
}
```

`mcp_server.py` is kept as backward-compatible alias to `mcp_server_read.py`.

### Read Tools

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
| `tg_get_my_dialogs` | List account dialogs |
| `tg_resolve_username` | Resolve username to entity |
| `tg_get_user_by_id` | Get user by numeric ID |
| `tg_download_media` | Download media from message |
| `tg_get_stats` | Anti-spam system stats |

### Actions Tools

| Tool | Description |
|------|-------------|
| `tg_list_sessions` | List available Telegram sessions |
| `tg_use_session` | Switch active session (if enabled) |
| `tg_get_group_info` | Validate target group |
| `tg_get_my_dialogs` | Browse possible targets |
| `tg_resolve_username` | Resolve target username |
| `tg_send_message` | Send message with anti-spam + policy gates (`confirm=true` + exact `confirmation_text` + one-time `approval_code`) |
| `tg_send_file` | Send local file with anti-spam + policy gates (`confirm=true` + exact `confirmation_text` + one-time `approval_code`) |
| `tg_add_member_to_group` | Add user to group/channel (`dry_run` by default; same confirm + approval gates on execution) |
| `tg_remove_member_from_group` | Remove user from group/channel (`dry_run` by default; same confirm + approval gates on execution) |
| `tg_migrate_member` | Add new user + remove old user in one safe flow (same confirm + approval gates on execution) |
| `tg_create_add_member_batch` | Build one add-member batch for many groups (single approval for whole task) |
| `tg_create_add_member_batch_from_report` | Build batch from failed groups in JSON report |
| `tg_approve_batch` | One-time approve a batch |
| `tg_get_batch_status` | Check batch progress and pending groups |
| `tg_run_add_member_batch` | Run approved batch in chunks (no per-group approvals) |
| `tg_get_actions_policy` | Show active action restrictions |
| `tg_get_stats` | Anti-spam system stats |

### Session Concurrency

- Default mode is `TG_SESSION_LOCK_MODE=shared`: multiple MCP servers/projects can use one `.session`.
- Optional strict mode: `TG_SESSION_LOCK_MODE=exclusive` blocks concurrent use of the same session.
- For production safety, prefer separate sessions for Read and Actions even if shared mode is allowed.
- `TG_GLOBAL_RPS_MODE=shared` applies one shared RPS budget across all processes using the same `data/anti_spam`.
- `TG_FLOOD_CIRCUIT_THRESHOLD_SEC` + `TG_FLOOD_CIRCUIT_COOLDOWN_SEC` pause all calls after critical FLOOD_WAIT.
- Non-dry-run write actions require `confirm=true` and exact `confirmation_text` (`TG_ACTIONS_CONFIRMATION_PHRASE`).
- Non-dry-run write actions also require one-time `approval_code` from the matching `dry_run` preview (`TG_ACTIONS_REQUIRE_APPROVAL_CODE=1`).
- `approval_code` has minimum age (`TG_ACTIONS_APPROVAL_MIN_AGE_SEC`, default 30s): immediate execute right after dry_run is blocked.
- Action MCP blocks duplicate sends/actions by payload hash for 24h (`TG_ACTIONS_IDEMPOTENCY_*`), unless `force_resend=true`.
- Action state files (`approval/idempotency/batch`) now use file locks + atomic write, so parallel ActionMCP processes do not corrupt JSON state.
- Batch execution uses a per-batch run lease lock (`TG_ACTIONS_BATCH_RUN_LEASE_SEC`) to avoid duplicate processing of the same batch by two workers.
- For long tasks, batch mode supports scoped approval: `tg_create_add_member_batch` -> `tg_approve_batch` -> repeat `tg_run_add_member_batch` until complete.
- Batch run permission is time-limited (`TG_ACTIONS_BATCH_APPROVAL_LEASE_SEC`, default 24h). After lease expiry, re-approve the same batch.
- ActionMCP is fail-closed by default: weakening core safe flags auto-disables actions unless `TG_ACTIONS_UNSAFE_OVERRIDE=1`.
- Direct `TelegramClient.send_*` writes and raw MTProto write requests (`client(Request)`) are blocked by default.
- Use `tgmcp-actions` tools for any write operation.
- In strict mode (`TG_ENFORCE_ACTION_PROCESS=1`), write is allowed only when process entrypoint is `mcp_server_actions.py`.
- For hard session isolation, run MCP under a dedicated OS user and keep `data/sessions` owned by that user only.

## Structure

```
tganalytics/
├── tganalytics/        # Core package
│   ├── infra/          # Clients, rate limiting, metrics
│   ├── domain/         # GroupManager, participants
│   └── config/         # Configuration
├── mcp_server.py       # Backward-compatible read alias
├── mcp_server_read.py  # Read-focused MCP server
├── mcp_server_actions.py # Actions-focused MCP server
├── mcp_server_common.py # Shared state/session helpers
├── mcp_actions_policy.py # Policy helpers (allowlist/hash/confirmation/safe defaults)
├── mcp_actions_state.py  # Locked JSON state helpers (approval/idempotency/batch)
├── mcp_actions_batch.py  # Batch record + summary helpers
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
