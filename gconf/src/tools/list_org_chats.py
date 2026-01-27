#!/usr/bin/env python3
import asyncio
import argparse
from pathlib import Path
from typing import List, Optional

from tganalytics.infra.limiter import safe_call, get_rate_limiter
from tganalytics.infra.tele_client import get_client_for_session
from tganalytics.domain.groups import GroupManager

GCONF_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_PATH = GCONF_ROOT / "data" / "sessions" / "gconf_support.session"


async def fetch_dialogs(client):
    dialogs = []
    async for dialog in client.iter_dialogs():
        dialogs.append(dialog)
    return dialogs


def title_contains_org(title: str) -> bool:
    if not title:
        return False
    lowered = title.lower()
    return "(org)" in lowered


async def list_org_chats(session_path: Optional[str], show_legacy: bool = False, exact_count: bool = False) -> List[dict]:
    client = get_client_for_session(session_path or str(DEFAULT_SESSION_PATH))

    # fail fast if session file is missing to avoid interactive prompts
    session_file = Path(session_path) if session_path else DEFAULT_SESSION_PATH
    if not session_file.exists():
        print(
            f"❌ session file not found: {session_file}. "
            "create it first using gconf/src/tools/create_session.py"
        )
        return []

    await client.start()

    dialogs = await safe_call(fetch_dialogs, client, operation_type="api")

    results: List[dict] = []
    for d in dialogs:
        try:
            title = d.title or ""
            if not title_contains_org(title):
                continue
            if not (d.is_group or d.is_channel):
                continue

            entity = d.entity
            username = getattr(entity, "username", None)
            if d.is_channel:
                if getattr(entity, "megagroup", False):
                    chat_type = "supergroup"
                else:
                    chat_type = "channel"
            elif d.is_group:
                chat_type = "group"
            else:
                chat_type = "other"
            legacy = False
            try:
                if getattr(entity, "migrated_to", None):
                    legacy = True
            except Exception:
                pass
            results.append({
                "id": getattr(entity, "id", d.id),
                "type": chat_type,
                "title": title,
                "username": username,
                "link": f"https://t.me/{username}" if username else None,
                "legacy": legacy,
            })
        except Exception:
            # skip problematic dialogs without failing the whole run
            continue

    limiter = get_rate_limiter()
    stats = limiter.get_stats()

    # enrich with members, messages count, first/last message dates
    manager = GroupManager(client)
    for item in results:
        gid = item["id"]
        # participants count
        info = None
        try:
            info = await manager.get_group_info(gid)
            item["members"] = info.get("participants_count") if info else None
        except Exception:
            item["members"] = None
        # messages count (fast count via tg_core helper)
        try:
            item["messages"] = await manager.get_message_count(gid)
        except Exception:
            item["messages"] = None
        # first message date and build deeplinks
        first_id = None
        try:
            async def get_first_msg():
                ent = await client.get_entity(gid)
                async for msg in client.iter_messages(ent, reverse=True, limit=1):
                    return msg.id, msg.date
                return None, None
            first_id, first_dt = await safe_call(get_first_msg, operation_type="api")
            item["first_date"] = first_dt.isoformat() if first_dt else None
        except Exception:
            item["first_date"] = None
        # last message date (and id for approximate count fallback)
        last_id = None
        try:
            async def get_last_msg():
                ent = await client.get_entity(gid)
                async for msg in client.iter_messages(ent, limit=1):
                    return msg.id, msg.date
                return None, None
            last_id, last_dt = await safe_call(get_last_msg, operation_type="api")
            item["last_date"] = last_dt.isoformat() if last_dt else None
        except Exception:
            item["last_date"] = None
        # optional exact count if API didn't return count (can be slow)
        if exact_count and item.get("messages") is None:
            try:
                async def count_all():
                    ent = await client.get_entity(gid)
                    c = 0
                    async for _ in client.iter_messages(ent):
                        c += 1
                    return c
                item["messages"] = await safe_call(count_all, operation_type="api")
            except Exception:
                pass
        try:
            if item.get("username"):
                item["deeplink"] = f"https://t.me/{item['username']}"
            elif first_id:
                # for private/supergroups without username, t.me/c/SHORT_ID/MSG_ID works inside the app
                # SHORT_ID is the internal channel id without -100 prefix; our gid is already that form from dialogs
                item["deeplink"] = f"https://t.me/c/{gid}/{first_id}"
            else:
                item["deeplink"] = f"tg://openmessage?chat_id=-100{gid}"
        except Exception:
            item["deeplink"] = None

    # deduplicate legacy groups when a supergroup with the same title exists
    title_has_supergroup = {r["title"] for r in results if r["type"] == "supergroup"}
    for r in results:
        if r["type"] == "group" and r["title"] in title_has_supergroup:
            r["legacy"] = True

    await client.disconnect()

    # print summary
    print("ID".ljust(15) + " | " + "TYPE".ljust(10) + " | " + "MEMB".rjust(5) + " | " + "MSGS".rjust(6) + " | " + "FIRST".ljust(19) + " | " + "LAST".ljust(19) + " | " + "LINK".ljust(45) + " | TITLE")
    print("-" * 230)
    display_items = results if show_legacy else [r for r in results if not r.get("legacy")]
    for item in display_items:
        id_str = str(item["id"])[:15]
        type_str = item["type"][:10]
        memb = item.get("members")
        memb_str = (str(memb) if memb is not None else "?").rjust(5)
        msgs = item.get("messages")
        msgs_str = (str(msgs) if msgs is not None else "?").rjust(6)
        first = item.get("first_date") or "?"
        first_str = first[:19]
        last = item.get("last_date") or "?"
        last_str = last[:19]
        link = item.get("deeplink") or item.get("link") or "-"
        link_str = link[:45]
        title_str = item["title"]
        print(f"{id_str.ljust(15)} | {type_str.ljust(10)} | {memb_str} | {msgs_str} | {first_str.ljust(19)} | {last_str.ljust(19)} | {link_str.ljust(45)} | {title_str}")

    print(f"\n✅ matched {(len(results))} chats containing '(org)' in title")
    print(f"🛡️  anti-spam: api_calls={stats['api_calls']}, flood_waits={stats['flood_waits']}")

    return results


async def main():
    parser = argparse.ArgumentParser(description="list chats with titles containing '(org)' (gconf scope)")
    parser.add_argument(
        "--session",
        default=str(DEFAULT_SESSION_PATH),
        help="path to .session file to use (default: gconf/data/sessions/gconf_support.session)",
    )
    parser.add_argument(
        "--show-legacy",
        action="store_true",
        help="include legacy migrated groups in the output",
    )
    parser.add_argument(
        "--exact-count",
        action="store_true",
        help="compute exact message counts for groups without API-provided counts (slower)",
    )
    args = parser.parse_args()

    await list_org_chats(args.session, show_legacy=args.show_legacy, exact_count=args.exact_count)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        raise SystemExit(130)


