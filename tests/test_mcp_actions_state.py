import json

from mcp_actions_state import load_json_dict, update_json_dict


def test_update_json_dict_roundtrip(tmp_path):
    path = tmp_path / "state.json"

    def _set_value(state):
        state["foo"] = "bar"
        return "ok"

    result = update_json_dict(path, _set_value)
    assert result == "ok"
    assert load_json_dict(path) == {"foo": "bar"}


def test_update_json_dict_root_key_preserves_other_keys(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps({"meta": {"version": 1}, "batches": {"old": {"id": "old"}}}, ensure_ascii=False),
        encoding="utf-8",
    )

    def _add_batch(state):
        state["new"] = {"id": "new"}

    update_json_dict(path, _add_batch, root_key="batches")
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert raw["meta"] == {"version": 1}
    assert "old" in raw["batches"]
    assert raw["batches"]["new"]["id"] == "new"
