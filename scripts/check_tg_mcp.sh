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
check_path() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    echo "Missing: ${path}"
    missing=1
  fi
}

check_path "${REPO_PATH}/.env"
check_path "${REPO_PATH}/venv/bin/python3"
check_path "${REPO_PATH}/tganalytics/mcp_server_read.py"
check_path "${REPO_PATH}/tganalytics/mcp_server_actions.py"
check_path "${REPO_PATH}/data/sessions"

if [[ ${missing} -eq 1 ]]; then
  echo "tg-mcp check failed"
  exit 2
fi

echo "tg-mcp check ok"
