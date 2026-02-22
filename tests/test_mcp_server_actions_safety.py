import os

os.environ.setdefault("TG_API_ID", "1")
os.environ.setdefault("TG_API_HASH", "testhash")

import mcp_server_actions as actions


def test_validate_confirmation_text_required():
    actions.REQUIRE_CONFIRMATION_TEXT = True
    actions.MIN_CONFIRMATION_TEXT_LEN = 6

    ok, error = actions._validate_confirmation_text("", dry_run=False)
    assert ok is False
    assert "confirmation_text" in str(error)


def test_validate_confirmation_text_not_required_in_dry_run():
    actions.REQUIRE_CONFIRMATION_TEXT = True
    actions.MIN_CONFIRMATION_TEXT_LEN = 6

    ok, error = actions._validate_confirmation_text("", dry_run=True)
    assert ok is True
    assert error is None


def test_idempotency_duplicate_window(tmp_path):
    actions.IDEMPOTENCY_ENABLED = True
    actions.IDEMPOTENCY_WINDOW_SEC = 3600
    actions.IDEMPOTENCY_FILE = tmp_path / "action_idempotency.json"

    action_hash = "abc123"

    duplicate, retry_after = actions._check_recent_duplicate(action_hash, now_ts=1000.0)
    assert duplicate is False
    assert retry_after == 0

    actions._mark_action_executed(action_hash, now_ts=1000.0)

    duplicate, retry_after = actions._check_recent_duplicate(action_hash, now_ts=1300.0)
    assert duplicate is True
    assert retry_after > 0

    duplicate, retry_after = actions._check_recent_duplicate(action_hash, now_ts=5000.0)
    assert duplicate is False
    assert retry_after == 0


def test_hash_payload_is_stable_for_key_order():
    a = actions._hash_payload({"action": "send", "target": "x", "text": "hello"})
    b = actions._hash_payload({"text": "hello", "target": "x", "action": "send"})
    assert a == b


def test_preconditions_blocked_by_safe_startup_guard(monkeypatch):
    monkeypatch.setattr(actions, "SAFE_STARTUP_BLOCK_REASON", "unsafe config")
    ok, err = actions._check_action_preconditions("group1", dry_run=True, confirm=False)
    assert ok is False
    assert "unsafe" in str(err)


def test_blocked_response_adds_next_step_for_approval_code():
    result = actions._blocked(
        "Execution blocked: approval_code is required. Run the same action with dry_run=true first."
    )
    assert result["success"] is False
    assert "approval_code" in result["error"]
    assert "dry_run=true" in str(result.get("next_step", ""))
