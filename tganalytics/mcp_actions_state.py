"""State file helpers for Action MCP with optional cross-process locks."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

try:
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None

T = TypeVar("T")


def load_json_dict(path: Path, *, root_key: str | None = None) -> dict[str, Any]:
    """Load dict-like JSON payload from path, returning empty dict on errors."""
    if not path.exists():
        return {}
    with _file_lock(path, shared=True):
        raw = _read_json_dict(path)
        if root_key is None:
            return raw
        nested = raw.get(root_key, {})
        return nested if isinstance(nested, dict) else {}


def update_json_dict(
    path: Path,
    mutator: Callable[[dict[str, Any]], T],
    *,
    root_key: str | None = None,
) -> T:
    """Atomically load-mutate-save dict payload under file lock."""
    with _file_lock(path, shared=False):
        raw = _read_json_dict(path)
        if root_key is None:
            state = raw
        else:
            nested = raw.get(root_key, {})
            state = nested if isinstance(nested, dict) else {}

        result = mutator(state)

        if root_key is None:
            payload = state
        else:
            raw[root_key] = state
            payload = raw

        _atomic_write_json(path, payload)
        return result


@contextmanager
def _file_lock(path: Path, *, shared: bool) -> Iterator[None]:
    """Best-effort process lock using a sibling .lock file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if fcntl is not None:
            mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
            fcntl.flock(fd, mode)
        yield
    finally:
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(fd)


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
