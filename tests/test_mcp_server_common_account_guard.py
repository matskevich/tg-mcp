import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("TG_API_ID", "1")
os.environ.setdefault("TG_API_HASH", "testhash")

import mcp_server_common as common


class DummyClient:
    def __init__(self, username: str, authorized: bool = True):
        self._username = username
        self._authorized = authorized
        self.connected = False
        self.disconnected = False

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.disconnected = True

    async def is_user_authorized(self):
        return self._authorized

    async def get_me(self):
        return SimpleNamespace(id=12345, username=self._username, first_name="Test")


@pytest.mark.asyncio
async def test_connect_client_fails_fast_on_expected_username_mismatch(monkeypatch):
    monkeypatch.setenv("TG_EXPECTED_USERNAME", "@dmatskevich")
    ctx = common.MCPServerContext(allow_session_switch=False)
    client = DummyClient(username="other_user")

    with pytest.raises(RuntimeError, match="Session mismatch"):
        await ctx._connect_client(client, "test_session")

    assert client.disconnected is True


@pytest.mark.asyncio
async def test_connect_client_allows_expected_username_case_insensitive(monkeypatch):
    monkeypatch.setenv("TG_EXPECTED_USERNAME", "dmatskevich")
    ctx = common.MCPServerContext(allow_session_switch=False)
    client = DummyClient(username="DmAtSkEvIcH")

    manager = await ctx._connect_client(client, "test_session")

    assert manager is not None
    assert ctx.current_session == "test_session"


@pytest.mark.asyncio
async def test_auth_status_reports_mismatch_as_unauthorized(monkeypatch):
    monkeypatch.setenv("TG_EXPECTED_USERNAME", "dmatskevich")
    monkeypatch.delenv("TG_SESSION_PATH", raising=False)

    ctx = common.MCPServerContext(allow_session_switch=False)
    ctx._client = DummyClient(username="another_user")

    payload = await ctx.auth_status()

    assert payload["authorized"] is False
    assert "Session mismatch" in payload.get("error", "")
