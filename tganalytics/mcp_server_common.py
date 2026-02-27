"""Shared state/helpers for tg-mcp MCP servers."""

from __future__ import annotations

import glob
import os
from typing import Any
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from tganalytics.domain.groups import GroupManager
from tganalytics.infra.tele_client import get_client, get_client_for_session


def _expected_username() -> str:
    raw = os.environ.get("TG_EXPECTED_USERNAME", "").strip().lstrip("@")
    return raw.lower()


def _build_session_mismatch_error(expected_username: str, actual_username: str | None, account_id: int | None) -> str:
    expected = f"@{expected_username}"
    actual_clean = (actual_username or "").strip()
    actual = f"@{actual_clean}" if actual_clean else "<no_username>"
    return (
        f"Session mismatch: expected account {expected}, got {actual} (id={account_id}). "
        "Set TG_SESSION_PATH to the correct session and restart MCP."
    )


def _validate_expected_account(me: Any) -> str | None:
    expected = _expected_username()
    if not expected:
        return None

    actual_username = (getattr(me, "username", None) or "").strip().lower()
    actual_id = getattr(me, "id", None)
    if actual_username != expected:
        return _build_session_mismatch_error(expected, getattr(me, "username", None), actual_id)
    return None


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
                "Run create_telegram_session.py (or scripts/create_session_qr.py) to re-authenticate. "
                "Telegram login code usually arrives in-app (SentCodeTypeApp), not SMS."
            )

        me = await client.get_me()
        mismatch_error = _validate_expected_account(me)
        if mismatch_error:
            await client.disconnect()
            raise RuntimeError(mismatch_error)

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

    async def auth_status(self) -> dict[str, Any]:
        """Return authorization status for current/default Telegram session."""
        session_path = os.environ.get("TG_SESSION_PATH", "").strip()
        if session_path:
            resolved_path = str(Path(session_path).expanduser().resolve())
            session_name = Path(session_path).name.replace(".session", "")
            client = self._client or get_client_for_session(session_path)
            is_transient = self._client is None
        else:
            resolved_path = ""
            session_name = os.environ.get("SESSION_NAME", "default")
            client = self._client or get_client()
            is_transient = self._client is None

        try:
            await client.connect()
            authorized = await client.is_user_authorized()
            payload: dict[str, Any] = {
                "authorized": bool(authorized),
                "session_name": session_name,
                "session_path": resolved_path or None,
            }
            if authorized:
                me = await client.get_me()
                payload["account"] = {
                    "id": getattr(me, "id", None),
                    "username": getattr(me, "username", None),
                    "first_name": getattr(me, "first_name", None),
                }
                mismatch_error = _validate_expected_account(me)
                if mismatch_error:
                    payload["authorized"] = False
                    payload["error"] = mismatch_error
            return payload
        except Exception as exc:
            return {
                "authorized": False,
                "session_name": session_name,
                "session_path": resolved_path or None,
                "error": str(exc),
            }
        finally:
            if is_transient:
                try:
                    await client.disconnect()
                except Exception:
                    pass
