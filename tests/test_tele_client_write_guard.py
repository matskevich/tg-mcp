import os

os.environ.setdefault("TG_API_ID", "1")
os.environ.setdefault("TG_API_HASH", "testhash")

from tganalytics.infra import tele_client


def _dummy_request(module_name: str, class_name: str):
    cls = type(class_name, (), {})
    cls.__module__ = module_name
    return cls()


def test_write_request_detection_for_invite():
    req = _dummy_request("telethon.tl.functions.channels", "InviteToChannelRequest")
    assert tele_client._is_telethon_write_request(req) is True


def test_read_request_detection_for_get():
    req = _dummy_request("telethon.tl.functions.channels", "GetFullChannelRequest")
    assert tele_client._is_telethon_write_request(req) is False


def test_batch_write_detection():
    read_req = _dummy_request("telethon.tl.functions.messages", "GetCommonChatsRequest")
    write_req = _dummy_request("telethon.tl.functions.messages", "DeleteChatUserRequest")
    assert tele_client._contains_telethon_write_request([read_req, write_req]) is True


def test_enforce_action_process_blocks_non_action_context(monkeypatch):
    monkeypatch.setattr(tele_client, "WRITE_GUARD_ENABLED", True)
    monkeypatch.setattr(tele_client, "ALLOW_DIRECT_WRITE", False)
    monkeypatch.setattr(tele_client, "ENFORCE_ACTION_PROCESS", True)
    monkeypatch.setattr(tele_client, "WRITE_CONTEXT", "actions_mcp")
    monkeypatch.setattr(tele_client, "WRITE_ALLOWED_CONTEXTS", {"actions_mcp"})
    monkeypatch.setattr(tele_client, "_is_actions_process", lambda: False)

    assert tele_client._is_direct_write_allowed() is False


def test_enforce_action_process_allows_real_action_process(monkeypatch):
    monkeypatch.setattr(tele_client, "WRITE_GUARD_ENABLED", True)
    monkeypatch.setattr(tele_client, "ALLOW_DIRECT_WRITE", False)
    monkeypatch.setattr(tele_client, "ENFORCE_ACTION_PROCESS", True)
    monkeypatch.setattr(tele_client, "WRITE_CONTEXT", "actions_mcp")
    monkeypatch.setattr(tele_client, "WRITE_ALLOWED_CONTEXTS", {"actions_mcp"})
    monkeypatch.setattr(tele_client, "_is_actions_process", lambda: True)

    assert tele_client._is_direct_write_allowed() is True
