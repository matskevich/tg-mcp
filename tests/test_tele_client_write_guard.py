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


def test_send_code_is_blocked_without_auth_bootstrap(monkeypatch):
    req = _dummy_request("telethon.tl.functions.auth", "SendCodeRequest")
    monkeypatch.setattr(tele_client, "AUTH_BOOTSTRAP_ENABLED", False)
    assert tele_client._is_telethon_write_request(req) is True


def test_send_code_is_allowed_with_auth_bootstrap(monkeypatch):
    req = _dummy_request("telethon.tl.functions.auth", "SendCodeRequest")
    monkeypatch.setattr(tele_client, "AUTH_BOOTSTRAP_ENABLED", True)
    assert tele_client._is_telethon_write_request(req) is False


def test_load_api_credentials_from_keychain(monkeypatch):
    monkeypatch.setenv("TG_SECRET_PROVIDER", "keychain")
    monkeypatch.delenv("TG_API_ID", raising=False)
    monkeypatch.delenv("TG_API_HASH", raising=False)
    monkeypatch.setenv("TG_KEYCHAIN_SERVICE", "tg-mcp-test")
    monkeypatch.setenv("TG_KEYCHAIN_ACCOUNT_API_ID", "TG_API_ID")
    monkeypatch.setenv("TG_KEYCHAIN_ACCOUNT_API_HASH", "TG_API_HASH")

    def fake_run(cmd, capture_output, text, check):
        account = cmd[cmd.index("-a") + 1]
        value = "12345\n" if account == "TG_API_ID" else "hash_from_keychain\n"
        return type("Proc", (), {"returncode": 0, "stdout": value})()

    monkeypatch.setattr(tele_client.subprocess, "run", fake_run)
    raw_api_id, raw_api_hash = tele_client._load_api_credentials()
    assert raw_api_id == "12345"
    assert raw_api_hash == "hash_from_keychain"


def test_load_api_credentials_from_command_provider(monkeypatch):
    monkeypatch.setenv("TG_SECRET_PROVIDER", "command")
    monkeypatch.delenv("TG_API_ID", raising=False)
    monkeypatch.delenv("TG_API_HASH", raising=False)
    monkeypatch.setenv("TG_SECRET_CMD_API_ID", "secret_id_cmd")
    monkeypatch.setenv("TG_SECRET_CMD_API_HASH", "secret_hash_cmd")

    def fake_run(cmd, capture_output, text, check):
        if cmd[0] == "secret_id_cmd":
            value = "777\n"
        else:
            value = "hash_from_cmd\n"
        return type("Proc", (), {"returncode": 0, "stdout": value})()

    monkeypatch.setattr(tele_client.subprocess, "run", fake_run)
    raw_api_id, raw_api_hash = tele_client._load_api_credentials()
    assert raw_api_id == "777"
    assert raw_api_hash == "hash_from_cmd"


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
