"""Actions-focused MCP server for tganalytics.

Contains high-risk Telegram operations behind explicit env gates.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Hard default: direct telethon writes are blocked unless context is actions_mcp.
os.environ.setdefault("TG_BLOCK_DIRECT_TELETHON_WRITE", "1")
os.environ.setdefault("TG_ALLOW_DIRECT_TELETHON_WRITE", "0")
os.environ.setdefault("TG_ENFORCE_ACTION_PROCESS", "1")
os.environ.setdefault("TG_DIRECT_TELETHON_WRITE_ALLOWED_CONTEXTS", "actions_mcp")
os.environ.setdefault("TG_WRITE_CONTEXT", "actions_mcp")
os.environ.setdefault("TG_ACTION_PROCESS", "1")

from mcp.server.fastmcp import FastMCP

from mcp_actions_batch import create_add_member_batch_record, summarize_batch
from mcp_actions_policy import (
    detect_unsafe_defaults,
    hash_payload,
    normalize_target,
    parse_allowlist,
    validate_confirmation_text,
)
from mcp_actions_state import load_json_dict, update_json_dict
from mcp_server_common import MCPServerContext
from tganalytics.infra.limiter import get_rate_limiter
from tganalytics.infra.metrics import snapshot

SERVER_NAME = os.environ.get("TG_MCP_SERVER_NAME", "tganalytics-actions")
ALLOW_SESSION_SWITCH = os.environ.get("TG_ALLOW_SESSION_SWITCH", "0") == "1"
ACTIONS_ENABLED = os.environ.get("TG_ACTIONS_ENABLED", "0") == "1"
REQUIRE_ALLOWLIST = os.environ.get("TG_ACTIONS_REQUIRE_ALLOWLIST", "1") == "1"
UNSAFE_OVERRIDE = os.environ.get("TG_ACTIONS_UNSAFE_OVERRIDE", "0") == "1"

try:
    MAX_MESSAGE_LEN = int(os.environ.get("TG_ACTIONS_MAX_MESSAGE_LEN", "2000"))
except ValueError:
    MAX_MESSAGE_LEN = 2000

try:
    MAX_FILE_MB = int(os.environ.get("TG_ACTIONS_MAX_FILE_MB", "20"))
except ValueError:
    MAX_FILE_MB = 20

try:
    MIN_CONFIRMATION_TEXT_LEN = int(os.environ.get("TG_ACTIONS_MIN_CONFIRM_TEXT_LEN", "6"))
except ValueError:
    MIN_CONFIRMATION_TEXT_LEN = 6

try:
    IDEMPOTENCY_WINDOW_SEC = int(os.environ.get("TG_ACTIONS_IDEMPOTENCY_WINDOW_SEC", str(24 * 3600)))
except ValueError:
    IDEMPOTENCY_WINDOW_SEC = 24 * 3600

REQUIRE_CONFIRMATION_TEXT = os.environ.get("TG_ACTIONS_REQUIRE_CONFIRMATION_TEXT", "1") == "1"
CONFIRMATION_PHRASE = os.environ.get("TG_ACTIONS_CONFIRMATION_PHRASE", "отправляй").strip().lower()
REQUIRE_APPROVAL_CODE = os.environ.get("TG_ACTIONS_REQUIRE_APPROVAL_CODE", "1") == "1"
IDEMPOTENCY_ENABLED = os.environ.get("TG_ACTIONS_IDEMPOTENCY_ENABLED", "1") == "1"
IDEMPOTENCY_FILE = Path(
    os.environ.get("TG_ACTIONS_IDEMPOTENCY_FILE", "data/anti_spam/action_idempotency.json")
)

try:
    APPROVAL_TTL_SEC = int(os.environ.get("TG_ACTIONS_APPROVAL_TTL_SEC", "1800"))
except ValueError:
    APPROVAL_TTL_SEC = 1800

APPROVAL_FILE = Path(os.environ.get("TG_ACTIONS_APPROVAL_FILE", "data/anti_spam/action_approvals.json"))

try:
    BATCH_DEFAULT_TTL_HOURS = int(os.environ.get("TG_ACTIONS_BATCH_TTL_HOURS", "168"))
except ValueError:
    BATCH_DEFAULT_TTL_HOURS = 168

try:
    BATCH_APPROVAL_LEASE_SEC = int(os.environ.get("TG_ACTIONS_BATCH_APPROVAL_LEASE_SEC", str(24 * 3600)))
except ValueError:
    BATCH_APPROVAL_LEASE_SEC = 24 * 3600

try:
    BATCH_RUN_LEASE_SEC = int(os.environ.get("TG_ACTIONS_BATCH_RUN_LEASE_SEC", "1800"))
except ValueError:
    BATCH_RUN_LEASE_SEC = 1800

BATCH_FILE = Path(os.environ.get("TG_ACTIONS_BATCH_FILE", "data/anti_spam/action_batches.json"))


def _detect_unsafe_defaults() -> list[str]:
    """Return list of unsafe policy settings."""
    return detect_unsafe_defaults(
        env=os.environ,
        require_allowlist=REQUIRE_ALLOWLIST,
        require_confirmation_text=REQUIRE_CONFIRMATION_TEXT,
        require_approval_code=REQUIRE_APPROVAL_CODE,
        idempotency_enabled=IDEMPOTENCY_ENABLED,
    )


UNSAFE_POLICY_ISSUES = _detect_unsafe_defaults()
SAFE_STARTUP_BLOCK_REASON = None
if UNSAFE_POLICY_ISSUES and not UNSAFE_OVERRIDE:
    ACTIONS_ENABLED = False
    SAFE_STARTUP_BLOCK_REASON = (
        "Unsafe ActionMCP policy detected: "
        + "; ".join(UNSAFE_POLICY_ISSUES)
        + ". Set TG_ACTIONS_UNSAFE_OVERRIDE=1 only if you really need non-safe mode."
    )


def _normalize_target(group: str) -> str:
    return normalize_target(group)


def _parse_allowlist(raw: str) -> set[str]:
    return parse_allowlist(raw)


ALLOWED_TARGETS = _parse_allowlist(os.environ.get("TG_ACTIONS_ALLOWED_GROUPS", ""))

mcp = FastMCP(SERVER_NAME)
ctx = MCPServerContext(allow_session_switch=ALLOW_SESSION_SWITCH)


def _check_target_allowed(group: str) -> tuple[bool, str | None]:
    normalized = _normalize_target(group)

    if REQUIRE_ALLOWLIST and not ALLOWED_TARGETS:
        return (
            False,
            "Actions blocked: TG_ACTIONS_REQUIRE_ALLOWLIST=1 but TG_ACTIONS_ALLOWED_GROUPS is empty.",
        )

    if ALLOWED_TARGETS and normalized not in ALLOWED_TARGETS:
        return (
            False,
            f"Target '{group}' is not in TG_ACTIONS_ALLOWED_GROUPS.",
        )

    return True, None


def _check_action_preconditions(
    group: str,
    dry_run: bool,
    confirm: bool,
    confirmation_text: str = "",
) -> tuple[bool, str | None]:
    if SAFE_STARTUP_BLOCK_REASON:
        return False, SAFE_STARTUP_BLOCK_REASON

    if not ACTIONS_ENABLED:
        return False, "Actions are disabled. Set TG_ACTIONS_ENABLED=1."

    allowed, error = _check_target_allowed(group)
    if not allowed:
        return False, error

    if not dry_run and not confirm:
        return (
            False,
            "Execution blocked: set confirm=true to run destructive action. "
            "Use dry_run=true to preview safely.",
        )

    ok, err = _validate_confirmation_text(confirmation_text, dry_run=dry_run)
    if not ok:
        return False, err

    return True, None


def _suggest_next_step(error: str | None) -> str | None:
    text = str(error or "").lower()
    if not text:
        return None
    if "unsafe actionmcp policy detected" in text:
        return (
            "Restore strict safety env flags, then restart ActionMCP. "
            "Use TG_ACTIONS_UNSAFE_OVERRIDE=1 only for temporary debugging."
        )
    if "actions are disabled" in text:
        return "Set TG_ACTIONS_ENABLED=1 for ActionMCP and restart server."
    if "require_allowlist=1 but tg_actions_allowed_groups is empty" in text:
        return "Set TG_ACTIONS_ALLOWED_GROUPS with explicit targets, then retry dry_run."
    if "is not in tg_actions_allowed_groups" in text:
        return "Add this target to TG_ACTIONS_ALLOWED_GROUPS, then retry dry_run."
    if "confirm=true" in text:
        return "Run same action with dry_run=true first, then rerun with confirm=true."
    if "confirmation_text" in text:
        return f"Use exact confirmation_text='{CONFIRMATION_PHRASE}' in this thread."
    if "approval_code" in text:
        return "Run matching action with dry_run=true to get one-time approval_code, then execute."
    if "duplicate action blocked" in text:
        return "Wait until idempotency window expires or set force_resend=true if resend is intentional."
    return None


def _blocked(error: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": False, "error": error}
    step = _suggest_next_step(error)
    if step:
        payload["next_step"] = step
    payload.update(extra)
    return payload


def _hash_payload(payload: dict[str, Any]) -> str:
    return hash_payload(payload)


def _load_idempotency_state() -> dict[str, float]:
    raw = load_json_dict(IDEMPOTENCY_FILE)
    state: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(key, str):
            try:
                state[key] = float(value)
            except Exception:
                continue
    return state


def _save_idempotency_state(state: dict[str, float]) -> None:
    normalized = {}
    for key, value in state.items():
        if isinstance(key, str):
            try:
                normalized[key] = float(value)
            except Exception:
                continue

    def _mut(current: dict[str, Any]) -> None:
        current.clear()
        current.update(normalized)

    update_json_dict(IDEMPOTENCY_FILE, _mut)


def _check_recent_duplicate(action_hash: str, now_ts: float | None = None) -> tuple[bool, int]:
    if not IDEMPOTENCY_ENABLED:
        return False, 0
    now = now_ts if now_ts is not None else time.time()

    def _mut(state: dict[str, Any]) -> tuple[bool, int]:
        normalized: dict[str, float] = {}
        for key, value in state.items():
            if not isinstance(key, str):
                continue
            try:
                normalized[key] = float(value)
            except Exception:
                continue

        # Trim stale keys while reading.
        fresh = {k: v for k, v in normalized.items() if (now - v) <= IDEMPOTENCY_WINDOW_SEC}
        state.clear()
        state.update(fresh)

        last_ts = fresh.get(action_hash)
        if last_ts is None:
            return False, 0

        retry_after = int(max(0, IDEMPOTENCY_WINDOW_SEC - (now - last_ts)))
        return retry_after > 0, retry_after

    return update_json_dict(IDEMPOTENCY_FILE, _mut)


def _mark_action_executed(action_hash: str, now_ts: float | None = None) -> None:
    if not IDEMPOTENCY_ENABLED:
        return
    now = now_ts if now_ts is not None else time.time()

    def _mut(state: dict[str, Any]) -> None:
        state[action_hash] = float(now)

    update_json_dict(IDEMPOTENCY_FILE, _mut)


def _validate_confirmation_text(confirmation_text: str, dry_run: bool) -> tuple[bool, str | None]:
    return validate_confirmation_text(
        confirmation_text=confirmation_text,
        dry_run=dry_run,
        require_confirmation_text=REQUIRE_CONFIRMATION_TEXT,
        min_confirmation_text_len=MIN_CONFIRMATION_TEXT_LEN,
        confirmation_phrase=CONFIRMATION_PHRASE,
    )


def _load_approvals_state() -> dict[str, dict[str, Any]]:
    raw = load_json_dict(APPROVAL_FILE)
    state: dict[str, dict[str, Any]] = {}
    for code, item in raw.items():
        if not isinstance(code, str) or not isinstance(item, dict):
            continue
        digest = item.get("digest")
        expires_at = item.get("expires_at")
        if not isinstance(digest, str):
            continue
        try:
            exp = float(expires_at)
        except Exception:
            continue
        state[code] = {"digest": digest, "expires_at": exp}
    return state


def _save_approvals_state(state: dict[str, dict[str, Any]]) -> None:
    normalized: dict[str, dict[str, Any]] = {}
    for code, item in state.items():
        if not isinstance(code, str) or not isinstance(item, dict):
            continue
        digest = item.get("digest")
        expires_at = item.get("expires_at")
        if not isinstance(digest, str):
            continue
        try:
            exp = float(expires_at)
        except Exception:
            continue
        normalized[code] = {"digest": digest, "expires_at": exp}

    def _mut(current: dict[str, Any]) -> None:
        current.clear()
        current.update(normalized)

    update_json_dict(APPROVAL_FILE, _mut)


def _trim_approvals(state: dict[str, dict[str, Any]], now_ts: float | None = None) -> dict[str, dict[str, Any]]:
    now = now_ts if now_ts is not None else time.time()
    return {
        code: item
        for code, item in state.items()
        if isinstance(item, dict) and float(item.get("expires_at", 0)) > now
    }


def _issue_approval(payload_hash: str, now_ts: float | None = None) -> dict[str, Any]:
    now = now_ts if now_ts is not None else time.time()
    code = secrets.token_urlsafe(9)
    expires_at = now + APPROVAL_TTL_SEC

    def _mut(state: dict[str, Any]) -> None:
        trimmed = _trim_approvals(state, now_ts=now)
        trimmed[code] = {"digest": payload_hash, "expires_at": expires_at}
        state.clear()
        state.update(trimmed)

    update_json_dict(APPROVAL_FILE, _mut)
    return {
        "approval_code": code,
        "approval_expires_in_sec": APPROVAL_TTL_SEC,
        "approval_expires_at_ts": int(expires_at),
    }


def _consume_approval(payload_hash: str, approval_code: str, now_ts: float | None = None) -> tuple[bool, str | None]:
    now = now_ts if now_ts is not None else time.time()
    code = (approval_code or "").strip()

    def _mut(state: dict[str, Any]) -> tuple[bool, str | None]:
        trimmed = _trim_approvals(state, now_ts=now)
        state.clear()
        state.update(trimmed)

        if not code:
            return (
                False,
                "Execution blocked: approval_code is required. Run the same action with dry_run=true first.",
            )

        item = state.get(code)
        if not item:
            return False, "Execution blocked: approval_code is invalid or expired."
        if item.get("digest") != payload_hash:
            return (
                False,
                "Execution blocked: approval_code does not match this payload. Generate a fresh dry_run preview.",
            )

        state.pop(code, None)
        return True, None

    return update_json_dict(APPROVAL_FILE, _mut)


def _approval_gate(
    *,
    action_hash: str,
    dry_run: bool,
    approval_code: str,
) -> tuple[bool, str | None, dict[str, Any] | None]:
    if not REQUIRE_APPROVAL_CODE:
        return True, None, None
    if dry_run:
        return True, None, _issue_approval(action_hash)
    ok, err = _consume_approval(action_hash, approval_code)
    return ok, err, None


def _load_batches_state() -> dict[str, dict[str, Any]]:
    batches = load_json_dict(BATCH_FILE, root_key="batches")
    return {str(k): v for k, v in batches.items() if isinstance(v, dict)}


def _save_batches_state(state: dict[str, dict[str, Any]]) -> None:
    normalized = {str(k): v for k, v in state.items() if isinstance(v, dict)}

    def _mut(current: dict[str, Any]) -> None:
        current.clear()
        current.update(normalized)

    update_json_dict(BATCH_FILE, _mut, root_key="batches")


def _get_batch(batch_id: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    state = _load_batches_state()
    batch = state.get((batch_id or "").strip())
    return state, batch


def _batch_run_owner() -> str:
    return f"{SERVER_NAME}:{os.getpid()}"


def _acquire_batch_run_lock(batch_id: str, now_ts: int | None = None) -> tuple[bool, str | None]:
    now = int(now_ts if now_ts is not None else time.time())
    owner = _batch_run_owner()
    bid = (batch_id or "").strip()
    blocked_error: str | None = None

    def _mut(state: dict[str, Any]) -> None:
        nonlocal blocked_error
        batch = state.get(bid)
        if not isinstance(batch, dict):
            blocked_error = f"batch '{bid}' not found"
            return

        locked_until = int(batch.get("run_lock_until_ts") or 0)
        locked_by = str(batch.get("run_lock_owner") or "")
        if locked_until > now and locked_by and locked_by != owner:
            blocked_error = (
                f"batch is already running by another worker until {locked_until}; "
                "retry later or after lock lease expires"
            )
            return

        batch["run_lock_owner"] = owner
        batch["run_lock_until_ts"] = now + BATCH_RUN_LEASE_SEC
        state[bid] = batch

    update_json_dict(BATCH_FILE, _mut, root_key="batches")
    if blocked_error:
        return False, blocked_error
    return True, None


def _release_batch_run_lock(batch_id: str, now_ts: int | None = None) -> None:
    now = int(now_ts if now_ts is not None else time.time())
    owner = _batch_run_owner()
    bid = (batch_id or "").strip()

    def _mut(state: dict[str, Any]) -> None:
        batch = state.get(bid)
        if not isinstance(batch, dict):
            return
        if str(batch.get("run_lock_owner") or "") not in ("", owner):
            return
        batch["run_lock_owner"] = None
        batch["run_lock_until_ts"] = now
        state[bid] = batch

    update_json_dict(BATCH_FILE, _mut, root_key="batches")


def _summarize_batch(batch: dict[str, Any]) -> dict[str, Any]:
    return summarize_batch(batch)


def _create_add_member_batch_record(
    user: str,
    groups: list[str],
    note: str,
    ttl_hours: int,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    return create_add_member_batch_record(
        user=user,
        groups=groups,
        note=note,
        ttl_hours=ttl_hours,
        check_target_allowed=_check_target_allowed,
    )


@mcp.tool()
async def tg_list_sessions() -> dict:
    """List available Telegram sessions in data/sessions/."""
    return await ctx.list_sessions()


@mcp.tool()
async def tg_use_session(session_name: str) -> dict:
    """Switch to a different Telegram session if allowed by configuration."""
    return await ctx.use_session(session_name)


@mcp.tool()
async def tg_get_group_info(group: str) -> dict:
    """Get group/channel info to validate the target before action calls."""
    manager = await ctx.get_manager()
    result = await manager.get_group_info(group)
    return result or {"error": "Group not found"}


@mcp.tool()
async def tg_resolve_username(username: str) -> dict:
    """Resolve a Telegram @username to user/channel/chat info."""
    manager = await ctx.get_manager()
    result = await manager.resolve_username(username)
    return result or {"error": f"Could not resolve username '{username}'"}


@mcp.tool()
async def tg_get_my_dialogs(limit: int = 100, dialog_type: str = "all") -> dict:
    """List dialogs to choose safe action targets."""
    manager = await ctx.get_manager()
    dialogs = await manager.get_my_dialogs(limit=limit, dialog_type=dialog_type)
    return {"count": len(dialogs), "dialogs": dialogs}


@mcp.tool()
async def tg_send_message(
    group: str,
    message_text: str,
    dry_run: bool = False,
    confirm: bool = False,
    confirmation_text: str = "",
    approval_code: str = "",
    force_resend: bool = False,
) -> dict:
    """Send message with policy gates (confirm + confirmation_text + idempotency)."""
    can_run, error = _check_action_preconditions(
        group,
        dry_run=dry_run,
        confirm=confirm,
        confirmation_text=confirmation_text,
    )
    if not can_run:
        return _blocked(error or "preconditions failed")

    clean_text = (message_text or "").strip()
    if not clean_text:
        return _blocked("message_text is empty")

    if len(clean_text) > MAX_MESSAGE_LEN:
        return {
            "success": False,
            "error": f"message_text is too long ({len(clean_text)} > {MAX_MESSAGE_LEN})",
        }

    action_hash = _hash_payload(
        {
            "action": "send_message",
            "target": _normalize_target(group),
            "text": clean_text,
        }
    )

    approval_ok, approval_error, approval_meta = _approval_gate(
        action_hash=action_hash,
        dry_run=dry_run,
        approval_code=approval_code,
    )
    if not approval_ok:
        return _blocked(approval_error or "approval gate blocked")

    if dry_run:
        result = {
            "success": True,
            "dry_run": True,
            "target": group,
            "message_len": len(clean_text),
            "action_hash": action_hash,
            "confirmation_text_required": CONFIRMATION_PHRASE if REQUIRE_CONFIRMATION_TEXT else None,
        }
        if approval_meta:
            result.update(approval_meta)
        return result

    if not force_resend:
        duplicate, retry_after_sec = _check_recent_duplicate(action_hash)
        if duplicate:
            return {
                "success": False,
                "duplicate_blocked": True,
                "retry_after_sec": retry_after_sec,
                "action_hash": action_hash,
                "error": "Duplicate action blocked by idempotency window. "
                "Set force_resend=true to override.",
            }

    manager = await ctx.get_manager()
    sent = await manager.send_message(group, clean_text)
    if sent:
        _mark_action_executed(action_hash)
        return {
            "success": True,
            "target": group,
            "message_len": len(clean_text),
            "action_hash": action_hash,
        }

    return {
        "success": False,
        "target": group,
        "action_hash": action_hash,
        "error": "send_message failed (see server logs for details)",
    }


@mcp.tool()
async def tg_send_file(
    group: str,
    file_path: str,
    caption: str = "",
    dry_run: bool = False,
    confirm: bool = False,
    confirmation_text: str = "",
    approval_code: str = "",
    force_resend: bool = False,
) -> dict:
    """Send local file with policy gates (confirm + confirmation_text + idempotency)."""
    can_run, error = _check_action_preconditions(
        group,
        dry_run=dry_run,
        confirm=confirm,
        confirmation_text=confirmation_text,
    )
    if not can_run:
        return _blocked(error or "preconditions failed")

    path = (file_path or "").strip()
    if not path:
        return _blocked("file_path is empty")
    if not os.path.exists(path):
        return _blocked(f"file_path does not exist: {path}")
    if not os.path.isfile(path):
        return _blocked(f"file_path is not a file: {path}")

    file_size_bytes = os.path.getsize(path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    if file_size_mb > MAX_FILE_MB:
        return {
            "success": False,
            "error": f"file is too large ({file_size_mb:.2f} MB > {MAX_FILE_MB} MB)",
        }

    clean_caption = (caption or "").strip()
    if len(clean_caption) > MAX_MESSAGE_LEN:
        return {
            "success": False,
            "error": f"caption is too long ({len(clean_caption)} > {MAX_MESSAGE_LEN})",
        }

    stat = os.stat(path)
    action_hash = _hash_payload(
        {
            "action": "send_file",
            "target": _normalize_target(group),
            "file_path": os.path.abspath(path),
            "file_size": int(stat.st_size),
            "file_mtime_ns": int(stat.st_mtime_ns),
            "caption": clean_caption,
        }
    )

    approval_ok, approval_error, approval_meta = _approval_gate(
        action_hash=action_hash,
        dry_run=dry_run,
        approval_code=approval_code,
    )
    if not approval_ok:
        return _blocked(approval_error or "approval gate blocked")

    if dry_run:
        result = {
            "success": True,
            "dry_run": True,
            "target": group,
            "file_path": path,
            "file_size_mb": round(file_size_mb, 3),
            "caption_len": len(clean_caption),
            "action_hash": action_hash,
            "confirmation_text_required": CONFIRMATION_PHRASE if REQUIRE_CONFIRMATION_TEXT else None,
        }
        if approval_meta:
            result.update(approval_meta)
        return result

    if not force_resend:
        duplicate, retry_after_sec = _check_recent_duplicate(action_hash)
        if duplicate:
            return {
                "success": False,
                "duplicate_blocked": True,
                "retry_after_sec": retry_after_sec,
                "action_hash": action_hash,
                "error": "Duplicate action blocked by idempotency window. "
                "Set force_resend=true to override.",
            }

    manager = await ctx.get_manager()
    sent = await manager.send_file(group, path, caption=clean_caption)
    if sent:
        _mark_action_executed(action_hash)
        return {
            "success": True,
            "target": group,
            "file_path": path,
            "file_size_mb": round(file_size_mb, 3),
            "caption_len": len(clean_caption),
            "action_hash": action_hash,
        }

    return {
        "success": False,
        "target": group,
        "action_hash": action_hash,
        "error": "send_file failed (see server logs for details)",
    }


@mcp.tool()
async def tg_add_member_to_group(
    group: str,
    user: str,
    dry_run: bool = True,
    confirm: bool = False,
    confirmation_text: str = "",
    approval_code: str = "",
    force_resend: bool = False,
) -> dict:
    """Add user to group/channel with confirmation and idempotency gates."""
    can_run, error = _check_action_preconditions(
        group,
        dry_run=dry_run,
        confirm=confirm,
        confirmation_text=confirmation_text,
    )
    if not can_run:
        return _blocked(error or "preconditions failed")

    action_hash = _hash_payload(
        {
            "action": "add_member",
            "target": _normalize_target(group),
            "user": str(user).strip().lower(),
        }
    )

    approval_ok, approval_error, approval_meta = _approval_gate(
        action_hash=action_hash,
        dry_run=dry_run,
        approval_code=approval_code,
    )
    if not approval_ok:
        return _blocked(approval_error or "approval gate blocked")

    if not dry_run and not force_resend:
        duplicate, retry_after_sec = _check_recent_duplicate(action_hash)
        if duplicate:
            return {
                "success": False,
                "duplicate_blocked": True,
                "retry_after_sec": retry_after_sec,
                "action_hash": action_hash,
                "error": "Duplicate action blocked by idempotency window. "
                "Set force_resend=true to override.",
            }

    manager = await ctx.get_manager()
    result = await manager.add_member_to_group(group, user, dry_run=dry_run)
    if not dry_run and result.get("success"):
        _mark_action_executed(action_hash)
    if dry_run and approval_meta:
        result.update(approval_meta)
    result["action_hash"] = action_hash
    result["confirmation_text_required"] = CONFIRMATION_PHRASE if REQUIRE_CONFIRMATION_TEXT else None
    return result


@mcp.tool()
async def tg_remove_member_from_group(
    group: str,
    user: str,
    dry_run: bool = True,
    confirm: bool = False,
    confirmation_text: str = "",
    approval_code: str = "",
    force_resend: bool = False,
) -> dict:
    """Remove user from group/channel with confirmation and idempotency gates."""
    can_run, error = _check_action_preconditions(
        group,
        dry_run=dry_run,
        confirm=confirm,
        confirmation_text=confirmation_text,
    )
    if not can_run:
        return _blocked(error or "preconditions failed")

    action_hash = _hash_payload(
        {
            "action": "remove_member",
            "target": _normalize_target(group),
            "user": str(user).strip().lower(),
        }
    )

    approval_ok, approval_error, approval_meta = _approval_gate(
        action_hash=action_hash,
        dry_run=dry_run,
        approval_code=approval_code,
    )
    if not approval_ok:
        return _blocked(approval_error or "approval gate blocked")

    if not dry_run and not force_resend:
        duplicate, retry_after_sec = _check_recent_duplicate(action_hash)
        if duplicate:
            return {
                "success": False,
                "duplicate_blocked": True,
                "retry_after_sec": retry_after_sec,
                "action_hash": action_hash,
                "error": "Duplicate action blocked by idempotency window. "
                "Set force_resend=true to override.",
            }

    manager = await ctx.get_manager()
    result = await manager.remove_member_from_group(group, user, dry_run=dry_run)
    if not dry_run and result.get("success"):
        _mark_action_executed(action_hash)
    if dry_run and approval_meta:
        result.update(approval_meta)
    result["action_hash"] = action_hash
    result["confirmation_text_required"] = CONFIRMATION_PHRASE if REQUIRE_CONFIRMATION_TEXT else None
    return result


@mcp.tool()
async def tg_migrate_member(
    group: str,
    old_user: str,
    new_user: str,
    dry_run: bool = True,
    confirm: bool = False,
    confirmation_text: str = "",
    approval_code: str = "",
    force_resend: bool = False,
) -> dict:
    """Migrate member (add new, remove old) with confirmation and idempotency gates."""
    can_run, error = _check_action_preconditions(
        group,
        dry_run=dry_run,
        confirm=confirm,
        confirmation_text=confirmation_text,
    )
    if not can_run:
        return _blocked(error or "preconditions failed")

    action_hash = _hash_payload(
        {
            "action": "migrate_member",
            "target": _normalize_target(group),
            "old_user": str(old_user).strip().lower(),
            "new_user": str(new_user).strip().lower(),
        }
    )

    approval_ok, approval_error, approval_meta = _approval_gate(
        action_hash=action_hash,
        dry_run=dry_run,
        approval_code=approval_code,
    )
    if not approval_ok:
        return _blocked(approval_error or "approval gate blocked")

    if not dry_run and not force_resend:
        duplicate, retry_after_sec = _check_recent_duplicate(action_hash)
        if duplicate:
            return {
                "success": False,
                "duplicate_blocked": True,
                "retry_after_sec": retry_after_sec,
                "action_hash": action_hash,
                "error": "Duplicate action blocked by idempotency window. "
                "Set force_resend=true to override.",
            }

    manager = await ctx.get_manager()
    result = await manager.migrate_member(
        group_identifier=group,
        old_user_identifier=old_user,
        new_user_identifier=new_user,
        dry_run=dry_run,
    )
    if not dry_run and result.get("success"):
        _mark_action_executed(action_hash)
    if dry_run and approval_meta:
        result.update(approval_meta)
    result["action_hash"] = action_hash
    result["confirmation_text_required"] = CONFIRMATION_PHRASE if REQUIRE_CONFIRMATION_TEXT else None
    return result


@mcp.tool()
async def tg_create_add_member_batch(
    user: str,
    groups: list[str],
    note: str = "",
    ttl_hours: int = BATCH_DEFAULT_TTL_HOURS,
) -> dict:
    """Create batch for adding one user to many groups with one-time approval."""
    if SAFE_STARTUP_BLOCK_REASON:
        return _blocked(SAFE_STARTUP_BLOCK_REASON)
    if not ACTIONS_ENABLED:
        return _blocked("Actions are disabled. Set TG_ACTIONS_ENABLED=1.")

    if not str(user).strip():
        return _blocked("user is empty")
    if not groups:
        return _blocked("groups list is empty")

    batch, blocked_targets = _create_add_member_batch_record(user=user, groups=groups, note=note, ttl_hours=ttl_hours)
    state = _load_batches_state()
    state[batch["id"]] = batch
    _save_batches_state(state)

    summary = _summarize_batch(batch)
    summary["blocked_targets"] = blocked_targets
    summary["next_step"] = (
        "Call tg_approve_batch(batch_id, confirmation_text), then tg_run_add_member_batch(batch_id)."
    )
    return {"success": True, **summary}


@mcp.tool()
async def tg_create_add_member_batch_from_report(
    report_path: str,
    user: str,
    note: str = "",
    error_contains: str = "join quota exceeded",
    ttl_hours: int = BATCH_DEFAULT_TTL_HOURS,
) -> dict:
    """Create add-member batch from JSON report (e.g. previous migration run)."""
    path = Path((report_path or "").strip())
    if not path.exists():
        return _blocked(f"report_path does not exist: {path}")
    if not path.is_file():
        return _blocked(f"report_path is not a file: {path}")

    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _blocked(f"failed to parse report: {exc}")

    items = report.get("items")
    if not isinstance(items, list):
        return _blocked("report has no valid 'items' array")

    needle = (error_contains or "").strip().lower()
    groups: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result = item.get("result")
        if not isinstance(result, dict):
            continue
        if result.get("success"):
            continue
        err = str(result.get("error", "")).lower()
        if needle and needle not in err:
            continue
        chat_id = item.get("chat_id")
        if chat_id is None:
            continue
        groups.append(str(chat_id))

    if not groups:
        return {
            "success": False,
            "error": f"No failed groups matched error_contains='{error_contains}' in report.",
        }

    note_prefix = f"from_report:{path.name}"
    full_note = f"{note_prefix} {note}".strip()
    return await tg_create_add_member_batch(
        user=user,
        groups=groups,
        note=full_note,
        ttl_hours=ttl_hours,
    )


@mcp.tool()
async def tg_approve_batch(batch_id: str, confirmation_text: str) -> dict:
    """Approve previously created batch once; after that runs don't need per-action approval."""
    state, batch = _get_batch(batch_id)
    if not batch:
        return _blocked(f"batch '{batch_id}' not found")

    now = int(time.time())
    if int(batch.get("expires_at_ts", 0)) <= now:
        return _blocked("batch is expired")

    ok, err = _validate_confirmation_text(confirmation_text, dry_run=False)
    if not ok:
        return _blocked(err or "confirmation_text validation failed")

    batch["approved"] = True
    batch["approved_at_ts"] = now
    batch["approved_until_ts"] = now + BATCH_APPROVAL_LEASE_SEC
    if batch.get("status") == "pending_approval":
        batch["status"] = "approved"
    state[batch["id"]] = batch
    _save_batches_state(state)

    result = {"success": True, **_summarize_batch(batch)}
    result["approval_lease_sec"] = BATCH_APPROVAL_LEASE_SEC
    return result


@mcp.tool()
async def tg_get_batch_status(batch_id: str) -> dict:
    """Get status and counters for action batch."""
    _, batch = _get_batch(batch_id)
    if not batch:
        return _blocked(f"batch '{batch_id}' not found")

    summary = _summarize_batch(batch)
    pending_groups = [
        action.get("group")
        for action in batch.get("actions", [])
        if action.get("status") == "pending"
    ]
    summary["pending_groups_preview"] = pending_groups[:20]
    summary["last_error"] = batch.get("last_error")
    return {"success": True, **summary}


@mcp.tool()
async def tg_run_add_member_batch(batch_id: str, max_actions: int = 100) -> dict:
    """Execute approved add-member batch without per-action confirmations."""
    if SAFE_STARTUP_BLOCK_REASON:
        return _blocked(SAFE_STARTUP_BLOCK_REASON)
    if not ACTIONS_ENABLED:
        return _blocked("Actions are disabled. Set TG_ACTIONS_ENABLED=1.")

    if max_actions <= 0:
        return _blocked("max_actions must be > 0")

    state, batch = _get_batch(batch_id)
    if not batch:
        return _blocked(f"batch '{batch_id}' not found")

    now = int(time.time())
    lock_ok, lock_error = _acquire_batch_run_lock(batch_id, now_ts=now)
    if not lock_ok:
        return _blocked(lock_error or "failed to acquire batch run lock", **_summarize_batch(batch))

    try:
        state, batch = _get_batch(batch_id)
        if not batch:
            return _blocked(f"batch '{batch_id}' not found")

        if int(batch.get("expires_at_ts", 0)) <= now:
            batch["status"] = "expired"
            batch["run_lock_owner"] = None
            batch["run_lock_until_ts"] = now
            state[batch["id"]] = batch
            _save_batches_state(state)
            return _blocked("batch is expired", **_summarize_batch(batch))

        if not bool(batch.get("approved", False)):
            batch["run_lock_owner"] = None
            batch["run_lock_until_ts"] = now
            state[batch["id"]] = batch
            _save_batches_state(state)
            return _blocked("batch is not approved; call tg_approve_batch first", **_summarize_batch(batch))

        approved_until_ts = int(batch.get("approved_until_ts") or 0)
        if approved_until_ts <= now:
            batch["approved"] = False
            batch["status"] = "pending_approval"
            batch["run_lock_owner"] = None
            batch["run_lock_until_ts"] = now
            state[batch["id"]] = batch
            _save_batches_state(state)
            return _blocked("batch approval expired; call tg_approve_batch again", **_summarize_batch(batch))

        if batch.get("status") == "completed":
            batch["run_lock_owner"] = None
            batch["run_lock_until_ts"] = now
            state[batch["id"]] = batch
            _save_batches_state(state)
            return {"success": True, "message": "batch already completed", **_summarize_batch(batch)}

        manager = await ctx.get_manager()
        processed_now = 0
        stopped_reason = None

        batch["status"] = "running"
        batch["last_error"] = None

        for action in batch.get("actions", []):
            if processed_now >= int(max_actions):
                break
            if action.get("status") != "pending":
                continue

            group = str(action.get("group"))
            allowed, allowed_error = _check_target_allowed(group)
            if not allowed:
                action["status"] = "blocked_policy"
                action["last_error"] = allowed_error
                action["last_run_ts"] = now
                processed_now += 1
                continue

            result = await manager.add_member_to_group(group, batch.get("user"), dry_run=False)
            action["attempts"] = int(action.get("attempts", 0)) + 1
            action["last_run_ts"] = now

            if result.get("success"):
                if result.get("already_member"):
                    action["status"] = "already_member"
                else:
                    action["status"] = "success"
                    _mark_action_executed(str(action.get("action_hash", "")))
                action["last_error"] = None
                processed_now += 1
                continue

            err_text = str(result.get("error", "unknown error"))
            err_lower = err_text.lower()
            action["last_error"] = err_text

            if "join quota exceeded" in err_lower:
                batch["status"] = "paused_quota"
                batch["last_error"] = err_text
                stopped_reason = "join_quota_exceeded"
                break

            if "you can't write in this chat" in err_lower:
                action["status"] = "blocked_rights"
            else:
                action["status"] = "failed"
            processed_now += 1

        pending_left = any(a.get("status") == "pending" for a in batch.get("actions", []))
        if batch.get("status") == "running":
            batch["status"] = "approved" if pending_left else "completed"
        if batch.get("status") == "completed":
            batch["completed_at_ts"] = now
        batch["last_run_ts"] = now
        batch["run_lock_owner"] = None
        batch["run_lock_until_ts"] = now

        state[batch["id"]] = batch
        _save_batches_state(state)

        summary = _summarize_batch(batch)
        summary["processed_now"] = processed_now
        summary["stopped_reason"] = stopped_reason
        return {"success": True, **summary}
    finally:
        _release_batch_run_lock(batch_id, now_ts=int(time.time()))


@mcp.tool()
async def tg_get_actions_policy() -> dict[str, Any]:
    """Return active action policy gates and limits."""
    limiter_stats = get_rate_limiter().get_stats()
    return {
        "server_profile": "actions",
        "actions_enabled": ACTIONS_ENABLED,
        "require_allowlist": REQUIRE_ALLOWLIST,
        "allowed_targets": sorted(ALLOWED_TARGETS),
        "max_message_len": MAX_MESSAGE_LEN,
        "max_file_mb": MAX_FILE_MB,
        "idempotency_enabled": IDEMPOTENCY_ENABLED,
        "idempotency_window_sec": IDEMPOTENCY_WINDOW_SEC,
        "require_confirmation_text": REQUIRE_CONFIRMATION_TEXT,
        "confirmation_phrase": CONFIRMATION_PHRASE if REQUIRE_CONFIRMATION_TEXT else None,
        "min_confirmation_text_len": MIN_CONFIRMATION_TEXT_LEN,
        "require_approval_code": REQUIRE_APPROVAL_CODE,
        "approval_ttl_sec": APPROVAL_TTL_SEC if REQUIRE_APPROVAL_CODE else None,
        "batch_file": str(BATCH_FILE),
        "batch_default_ttl_hours": BATCH_DEFAULT_TTL_HOURS,
        "batch_approval_lease_sec": BATCH_APPROVAL_LEASE_SEC,
        "batch_run_lease_sec": BATCH_RUN_LEASE_SEC,
        "unsafe_override": UNSAFE_OVERRIDE,
        "unsafe_policy_issues": UNSAFE_POLICY_ISSUES,
        "safe_startup_block_reason": SAFE_STARTUP_BLOCK_REASON,
        "write_context": os.environ.get("TG_WRITE_CONTEXT"),
        "direct_telethon_write_guard": os.environ.get("TG_BLOCK_DIRECT_TELETHON_WRITE", "1") == "1",
        "enforce_action_process": os.environ.get("TG_ENFORCE_ACTION_PROCESS", "1") == "1",
        "group_msg_usage": limiter_stats.get("group_msg_usage"),
        "circuit_breaker": limiter_stats.get("circuit_breaker"),
        "destructive_actions_require_confirm": True,
        "default_dry_run_for_member_actions": True,
        "allow_session_switch": ALLOW_SESSION_SWITCH,
        "recommended_write_flow": [
            "1) Call write tool with dry_run=true to preview and get approval_code.",
            "2) Ask user for exact confirmation_text phrase in this thread.",
            "3) Execute same payload with confirm=true + confirmation_text + approval_code.",
            "4) Handle duplicate_blocked by waiting or using force_resend=true intentionally.",
        ],
        "recommended_batch_flow": [
            "1) tg_create_add_member_batch(user, groups).",
            "2) tg_approve_batch(batch_id, confirmation_text).",
            "3) Repeat tg_run_add_member_batch(batch_id, max_actions) until completed.",
            "4) If lease expires, re-run tg_approve_batch and continue.",
        ],
    }


@mcp.tool()
async def tg_get_stats() -> dict:
    """Get anti-spam statistics (API calls, flood waits, quotas, latency histogram)."""
    limiter = get_rate_limiter()
    return {
        "rate_limiter": limiter.get_stats(),
        "metrics": snapshot(),
        "current_session": ctx.current_session,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
