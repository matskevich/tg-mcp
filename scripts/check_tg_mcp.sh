#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="${1:-}"
if [[ -z "${REPO_PATH}" ]]; then
  echo "Usage: $0 /absolute/path/to/tg-mcp"
  exit 1
fi

if [[ "${REPO_PATH}" != /* ]]; then
  echo "Error: use absolute repo path"
  exit 1
fi

if [[ ! -d "${REPO_PATH}" ]]; then
  echo "Error: repo path does not exist: ${REPO_PATH}"
  exit 1
fi

missing=0
PYTHON_BIN="${REPO_PATH}/venv/bin/python3"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

check_path() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    echo "Missing: ${path}"
    missing=1
  fi
}

check_path "${REPO_PATH}/venv/bin/python3"
check_path "${REPO_PATH}/tganalytics/mcp_server_read.py"
check_path "${REPO_PATH}/tganalytics/mcp_server_actions.py"
check_path "${REPO_PATH}/data/sessions"

if [[ ! -f "${REPO_PATH}/.env" ]]; then
  echo "Warning: ${REPO_PATH}/.env not found (ok if secrets are provided externally)"
fi

if [[ ${missing} -eq 1 ]]; then
  echo "tg-mcp check failed"
  exit 2
fi

if compgen -G "${REPO_PATH}/data/sessions/*.session" > /dev/null; then
  if ! auth_report="$(cd "${REPO_PATH}" && PYTHONPATH=tganalytics:. TG_AUTH_BOOTSTRAP=1 "${PYTHON_BIN}" - <<'PY' 2>/dev/null
import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(".env"))

async def main() -> int:
    sessions = sorted(Path("data/sessions").glob("*.session"))
    if not sessions:
        print("Warning: no .session files found in data/sessions")
        return 0

    try:
        from tganalytics.infra.tele_client import get_client_for_session
    except Exception as exc:
        print(f"Warning: auth probe skipped ({exc})")
        return 0

    print("Auth probe:")
    for session_file in sessions:
        session_name = session_file.stem
        client = get_client_for_session(str(session_file))
        try:
            await client.connect()
            authorized = await client.is_user_authorized()
            print(f"  - {session_name}: authorized={'true' if authorized else 'false'}")
        except Exception as exc:
            print(f"  - {session_name}: warning={exc}")
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    return 0


raise SystemExit(asyncio.run(main()))
PY
)"; then
    echo "Warning: auth probe failed (non-blocking)."
  else
    echo "${auth_report}"
  fi
else
  echo "Warning: no session files found under ${REPO_PATH}/data/sessions"
fi

echo "tg-mcp check ok"
