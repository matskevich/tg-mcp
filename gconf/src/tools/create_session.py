import asyncio
from pathlib import Path
from tganalytics.infra.tele_client import get_client_for_session

GCONF_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_PATH = GCONF_ROOT / "data" / "sessions" / "gconf_support.session"

async def main(session_path: str = str(DEFAULT_SESSION_PATH)):
    client = get_client_for_session(session_path)
    await client.start()
    me = await client.get_me()
    print(f"✅ session created/updated at {session_path} for @{me.username} ({me.id})")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())





