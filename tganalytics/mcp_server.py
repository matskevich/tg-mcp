"""MCP server for tganalytics — read-only Telegram analytics.

Provides 9 tools for Claude Code to query Telegram groups/channels
via existing tganalytics infrastructure (GroupManager, rate limiter,
anti-spam). Supports multiple sessions with live switching.

Transport: stdio (local process only, no network port).
"""

import os
import glob

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP
from tganalytics.infra.tele_client import get_client, get_client_for_session
from tganalytics.domain.groups import GroupManager
from tganalytics.infra.limiter import get_rate_limiter
from tganalytics.infra.metrics import snapshot

mcp = FastMCP("tganalytics")

SESSIONS_DIR = os.environ.get("TG_SESSIONS_DIR", "data/sessions")

# Mutable state — single active session at a time
_client = None
_manager: GroupManager | None = None
_current_session: str | None = None


async def _get_manager() -> GroupManager:
    """Lazy-init: connect to default session on first tool call."""
    global _client, _manager, _current_session
    if _manager is None:
        session_path = os.environ.get("TG_SESSION_PATH", "")
        if session_path:
            _client = get_client_for_session(session_path)
            _current_session = os.path.basename(session_path).replace(".session", "")
        else:
            _client = get_client()
            _current_session = os.environ.get("SESSION_NAME", "default")
        await _client.start()
        _manager = GroupManager(_client)
    return _manager


# ── Session management ───────────────────────────────────────────────


@mcp.tool()
async def tg_list_sessions() -> dict:
    """List available Telegram sessions in data/sessions/."""
    sessions = [
        os.path.basename(f).replace(".session", "")
        for f in glob.glob(os.path.join(SESSIONS_DIR, "*.session"))
    ]
    return {"sessions": sorted(sessions), "current": _current_session}


@mcp.tool()
async def tg_use_session(session_name: str) -> dict:
    """Switch to a different Telegram session (e.g. 'dmatskevich')."""
    global _client, _manager, _current_session
    path = os.path.join(SESSIONS_DIR, f"{session_name}.session")
    if not os.path.exists(path):
        return {"error": f"Session '{session_name}' not found"}
    if _client:
        await _client.disconnect()
    _client = get_client_for_session(path)
    await _client.start()
    _manager = GroupManager(_client)
    _current_session = session_name
    me = await _client.get_me()
    return {"switched_to": session_name, "account": me.username or me.first_name}


# ── Analytics (read-only) ────────────────────────────────────────────


@mcp.tool()
async def tg_get_group_info(group: str) -> dict:
    """Get info about a Telegram group/channel (id, title, participants_count, type)."""
    manager = await _get_manager()
    result = await manager.get_group_info(group)
    return result or {"error": "Group not found"}


@mcp.tool()
async def tg_get_participants(group: str, limit: int = 100) -> dict:
    """Get participants of a Telegram group (id, username, first_name, is_premium, …)."""
    manager = await _get_manager()
    participants = await manager.get_participants(group, limit=limit)
    return {"count": len(participants), "participants": participants}


@mcp.tool()
async def tg_search_participants(group: str, query: str, limit: int = 50) -> dict:
    """Search group participants by name or username."""
    manager = await _get_manager()
    participants = await manager.search_participants(group, query, limit=limit)
    return {"count": len(participants), "participants": participants}


@mcp.tool()
async def tg_get_messages(group: str, limit: int = 100, min_id: int = 0) -> dict:
    """Get messages from a Telegram group (id, date, text, from_id, views, …)."""
    manager = await _get_manager()
    messages = await manager.get_messages(group, limit=limit, min_id=min_id)
    return {"count": len(messages), "messages": messages}


@mcp.tool()
async def tg_get_message_count(group: str) -> dict:
    """Get total number of messages in a Telegram group."""
    manager = await _get_manager()
    count = await manager.get_message_count(group)
    if count is not None:
        return {"group": group, "message_count": count}
    return {"group": group, "error": "Could not retrieve message count"}


@mcp.tool()
async def tg_get_group_creation_date(group: str) -> dict:
    """Get approximate creation date of a Telegram group (via first message)."""
    manager = await _get_manager()
    dt = await manager.get_group_creation_date(group)
    if dt is not None:
        return {"group": group, "creation_date": dt.isoformat()}
    return {"group": group, "error": "Could not determine creation date"}


@mcp.tool()
async def tg_get_my_dialogs(limit: int = 100, dialog_type: str = "all") -> dict:
    """List groups, channels and chats the current account is a member of.

    Args:
        limit: max number of dialogs to return (default 100).
        dialog_type: filter — "all", "group", "channel", "user".
    """
    manager = await _get_manager()
    dialogs = await manager.get_my_dialogs(limit=limit, dialog_type=dialog_type)
    return {"count": len(dialogs), "dialogs": dialogs}


@mcp.tool()
async def tg_resolve_username(username: str) -> dict:
    """Resolve a Telegram @username to user/channel/chat info (id, type, name).

    Args:
        username: Telegram username (with or without @).
    """
    manager = await _get_manager()
    result = await manager.resolve_username(username)
    return result or {"error": f"Could not resolve username '{username}'"}


@mcp.tool()
async def tg_download_media(group: str, message_id: int, output_dir: str = "data/downloads") -> dict:
    """Download a file/media from a Telegram message to a local directory.

    Args:
        group: group identifier (username or ID).
        message_id: ID of the message containing the media.
        output_dir: local directory to save the file (default: data/downloads).
    """
    manager = await _get_manager()
    path = await manager.download_media(group, message_id, output_dir)
    if path:
        return {"success": True, "path": path}
    return {"success": False, "error": "Download failed or message has no media"}


@mcp.tool()
async def tg_get_stats() -> dict:
    """Get anti-spam statistics (API calls, flood waits, quotas, latency histogram)."""
    limiter = get_rate_limiter()
    return {
        "rate_limiter": limiter.get_stats(),
        "metrics": snapshot(),
        "current_session": _current_session,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
