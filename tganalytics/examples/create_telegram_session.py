#!/usr/bin/env python3
"""
🔐 Create / refresh a Telegram (Telethon) session file.

This is an interactive helper: it may prompt for phone number, login code, and 2FA password.

Usage:
  # uses .env TG_API_ID / TG_API_HASH
  PYTHONPATH=. python3 examples/create_telegram_session.py --session-name dmatskevich

  # custom session dir (default: data/sessions)
  PYTHONPATH=. python3 examples/create_telegram_session.py --session-name dmatskevich --session-dir data/sessions
"""

import argparse
import asyncio
import sys
from pathlib import Path

# add packages/ and packages/tg_core to import path (same pattern as other examples)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = PROJECT_ROOT / "packages"
TG_CORE_DIR = PKG_DIR / "tg_core"
for p in (str(PKG_DIR), str(TG_CORE_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from tganalytics.infra.tele_client import get_client_for_session
from tganalytics.infra.limiter import safe_call


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Telegram session file (interactive)")
    parser.add_argument(
        "--session-name",
        required=True,
        help="Session name (file will be <session-dir>/<session-name>.session)",
    )
    parser.add_argument(
        "--session-dir",
        default="data/sessions",
        help="Directory to store session files (default: data/sessions)",
    )
    args = parser.parse_args()

    session_path = (PROJECT_ROOT / args.session_dir / args.session_name).resolve()
    print("🔐 creating telegram session")
    print(f"   session file: {session_path}.session")
    print()

    client = get_client_for_session(str(session_path))
    try:
        await client.start()
        me = await safe_call(client.get_me, operation_type="api")
        print(f"✅ logged in as: @{me.username} (id={me.id})")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())


