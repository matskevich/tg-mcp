import pytest

import mcp_server_actions as actions


class _FakeManager:
    async def send_message(self, group, message_text):
        return True


class _FakeCtx:
    current_session = "test"

    async def get_manager(self):
        return _FakeManager()


@pytest.mark.asyncio
async def test_send_message_requires_exact_confirmation_text(monkeypatch, tmp_path):
    monkeypatch.setattr(actions, "ACTIONS_ENABLED", True)
    monkeypatch.setattr(actions, "REQUIRE_ALLOWLIST", False)
    monkeypatch.setattr(actions, "REQUIRE_CONFIRMATION_TEXT", True)
    monkeypatch.setattr(actions, "CONFIRMATION_PHRASE", "отправляй")
    monkeypatch.setattr(actions, "REQUIRE_APPROVAL_CODE", False)
    monkeypatch.setattr(actions, "IDEMPOTENCY_ENABLED", False)
    monkeypatch.setattr(actions, "APPROVAL_FILE", tmp_path / "approvals.json")

    result = await actions.tg_send_message(
        group="test_target",
        message_text="hello",
        dry_run=False,
        confirm=True,
        confirmation_text="подтверждаю",
    )

    assert result["success"] is False
    assert "confirmation_text" in result["error"]


@pytest.mark.asyncio
async def test_send_message_requires_one_time_approval_code(monkeypatch, tmp_path):
    monkeypatch.setattr(actions, "ACTIONS_ENABLED", True)
    monkeypatch.setattr(actions, "REQUIRE_ALLOWLIST", False)
    monkeypatch.setattr(actions, "REQUIRE_CONFIRMATION_TEXT", True)
    monkeypatch.setattr(actions, "CONFIRMATION_PHRASE", "отправляй")
    monkeypatch.setattr(actions, "REQUIRE_APPROVAL_CODE", True)
    monkeypatch.setattr(actions, "IDEMPOTENCY_ENABLED", False)
    monkeypatch.setattr(actions, "APPROVAL_TTL_SEC", 1800)
    monkeypatch.setattr(actions, "APPROVAL_FILE", tmp_path / "approvals.json")
    monkeypatch.setattr(actions, "ctx", _FakeCtx())

    preview = await actions.tg_send_message(
        group="test_target",
        message_text="hello",
        dry_run=True,
        confirm=False,
    )
    assert preview["success"] is True
    approval_code = preview.get("approval_code")
    assert approval_code

    blocked = await actions.tg_send_message(
        group="test_target",
        message_text="hello",
        dry_run=False,
        confirm=True,
        confirmation_text="отправляй",
    )
    assert blocked["success"] is False
    assert "approval_code" in blocked["error"]

    sent = await actions.tg_send_message(
        group="test_target",
        message_text="hello",
        dry_run=False,
        confirm=True,
        confirmation_text="отправляй",
        approval_code=approval_code,
    )
    assert sent["success"] is True

    reused = await actions.tg_send_message(
        group="test_target",
        message_text="hello",
        dry_run=False,
        confirm=True,
        confirmation_text="отправляй",
        approval_code=approval_code,
    )
    assert reused["success"] is False
    assert "invalid or expired" in reused["error"]
