"""Shared state/helpers for tg-mcp MCP servers."""

from __future__ import annotations

import glob
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from tganalytics.domain.groups import GroupManager
from tganalytics.infra.tele_client import get_client, get_client_for_session


class MCPServerContext:
    """Shared runtime state for MCP servers.

    Keeps one active Telegram client/session per server process.
    """

    def __init__(self, sessions_dir: str | None = None, allow_session_switch: bool = True):
        self.sessions_dir = sessions_dir or os.environ.get("TG_SESSIONS_DIR", "data/sessions")
        self.allow_session_switch = allow_session_switch

        self._client = None
        self._manager: GroupManager | None = None
        self._current_session: str | None = None

    @property
    def current_session(self) -> str | None:
        return self._current_session

    @property
    def client(self) -> Any:
        return self._client

    async def _connect_client(self, client, session_name: str) -> GroupManager:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise RuntimeError(
                f"Session '{session_name}' is not authorized. "
                "Run create_telegram_session.py to re-authenticate."
            )
        self._client = client
        self._current_session = session_name
        self._manager = GroupManager(client)
        return self._manager

    async def get_manager(self) -> GroupManager:
        """Lazy-init manager and connect on the first call."""
        if self._manager is None:
            session_path = os.environ.get("TG_SESSION_PATH", "").strip()
            if session_path:
                session_name = os.path.basename(session_path).replace(".session", "")
                client = get_client_for_session(session_path)
            else:
                session_name = os.environ.get("SESSION_NAME", "default")
                client = get_client()

            await self._connect_client(client, session_name)

        return self._manager

    async def list_sessions(self) -> dict[str, Any]:
        sessions = [
            os.path.basename(path).replace(".session", "")
            for path in glob.glob(os.path.join(self.sessions_dir, "*.session"))
        ]
        return {"sessions": sorted(sessions), "current": self._current_session}

    async def use_session(self, session_name: str) -> dict[str, Any]:
        if not self.allow_session_switch:
            return {
                "error": "Session switching is disabled. "
                "Set TG_ALLOW_SESSION_SWITCH=1 to enable tg_use_session."
            }

        path = os.path.join(self.sessions_dir, f"{session_name}.session")
        if not os.path.exists(path):
            return {"error": f"Session '{session_name}' not found"}

        if self._client is not None:
            await self._client.disconnect()

        try:
            client = get_client_for_session(path)
            await self._connect_client(client, session_name)
            me = await self._client.get_me()
            return {"switched_to": session_name, "account": me.username or me.first_name}
        except RuntimeError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"Failed to switch session: {exc}"}
