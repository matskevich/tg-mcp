#!/usr/bin/env python3
"""CLI для работы с Telegram через gconf-сессию"""

import asyncio
import argparse
import json
from pathlib import Path
from tganalytics.infra.tele_client import get_client_for_session
from tganalytics.domain.groups import GroupManager
from tganalytics.infra.limiter import get_rate_limiter

GCONF_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSION_PATH = GCONF_ROOT / "data" / "sessions" / "gconf_support.session"


async def run_cli() -> None:
    parser = argparse.ArgumentParser(
        description="GConf: Работа с Telegram через выделенную сессию"
    )
    parser.add_argument(
        "command",
        choices=["info", "participants", "search", "export", "creation-date"],
        help="Команда для выполнения",
    )
    parser.add_argument(
        "group",
        help="Username группы (без @) или ID группы",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Максимальное количество участников (по умолчанию: 100)",
    )
    parser.add_argument(
        "--query",
        help="Поисковый запрос (для команды search)",
    )
    parser.add_argument(
        "--output",
        help="Файл для экспорта (для команды export)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Формат вывода (по умолчанию: json)",
    )
    parser.add_argument(
        "--session",
        default=str(DEFAULT_SESSION_PATH),
        help="Путь к файлу сессии (по умолчанию gconf/data/sessions/gconf_support.session)",
    )

    args = parser.parse_args()

    session_path = args.session or str(DEFAULT_SESSION_PATH)

    client = None

    try:
        client = get_client_for_session(session_path)
        await client.start()
        group_manager = GroupManager(client)

        if args.command == "info":
            await handle_info(group_manager, args.group)
        elif args.command == "participants":
            await handle_participants(group_manager, args.group, args.limit, args.format)
        elif args.command == "search":
            if not args.query:
                print("❌ Для команды search необходимо указать --query")
                return
            await handle_search(
                group_manager,
                args.group,
                args.query,
                args.limit,
                args.format,
            )
        elif args.command == "export":
            if not args.output:
                print("❌ Для команды export необходимо указать --output")
                return
            await handle_export(group_manager, args.group, args.output, args.limit)
        elif args.command == "creation-date":
            await handle_creation_date(group_manager, args.group)

        stats = get_rate_limiter().get_stats()
        print(
            "📊 Статистика анти-спам: "
            f"API вызовов: {stats['api_calls']}, FLOOD_WAIT: {stats['flood_waits']}"
        )

    except KeyboardInterrupt:
        print("\n⚠️ Операция прервана пользователем")
    except Exception as exc:
        print(f"❌ Ошибка: {exc}")
    finally:
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass


async def handle_info(group_manager: GroupManager, group: str) -> None:
    """Обработка команды info"""
    print(f"📋 Получение информации о группе: {group}")

    info = await group_manager.get_group_info(group)
    if info:
        print(f"✅ Найдена группа: {info['title']}")
        print(f"   ID: {info['id']}")
        print(f"   Username: @{info['username']}" if info["username"] else "   Username: Нет")
        print(f"   Тип: {info['type']}")
        print(f"   Участников: {info['participants_count']}")
    else:
        print(f"❌ Группа {group} не найдена")


async def handle_participants(
    group_manager: GroupManager, group: str, limit: int, format: str
) -> None:
    """Обработка команды participants"""
    print(f"👥 Получение участников группы: {group} (лимит: {limit})")

    participants = await group_manager.get_participants(group, limit)

    if participants:
        print(f"✅ Получено {len(participants)} участников")

        if format == "json":
            print(json.dumps(participants, ensure_ascii=False, indent=2))
        else:
            for i, participant in enumerate(participants, 1):
                username = participant["username"] or "Нет username"
                name = f"{participant['first_name'] or ''} {participant['last_name'] or ''}".strip()
                print(f"{i:3d}. {username} - {name}")
    else:
        print("❌ Не удалось получить участников")


async def handle_search(
    group_manager: GroupManager,
    group: str,
    query: str,
    limit: int,
    format: str,
) -> None:
    """Обработка команды search"""
    print(f"🔍 Поиск участников в группе {group} по запросу: {query}")

    participants = await group_manager.search_participants(group, query, limit)

    if participants:
        print(f"✅ Найдено {len(participants)} участников")

        if format == "json":
            print(json.dumps(participants, ensure_ascii=False, indent=2))
        else:
            for i, participant in enumerate(participants, 1):
                username = participant["username"] or "Нет username"
                name = f"{participant['first_name'] or ''} {participant['last_name'] or ''}".strip()
                print(f"{i:3d}. {username} - {name}")
    else:
        print("❌ Участники не найдены")


async def handle_export(
    group_manager: GroupManager, group: str, output: str, limit: int
) -> None:
    """Обработка команды export"""
    print(f"📤 Экспорт участников группы {group} в файл: {output}")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".csv":
        success = await group_manager.export_participants_to_csv(group, output, limit)
    else:
        participants = await group_manager.get_participants(group, limit)
        if participants:
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(participants, f, ensure_ascii=False, indent=2)
            print(f"✅ Экспортировано {len(participants)} участников в {output}")
            success = True
        else:
            success = False

    if not success:
        print("❌ Ошибка при экспорте")


async def handle_creation_date(group_manager: GroupManager, group: str) -> None:
    """Обработка команды creation-date"""
    print(f"📅 Получение даты создания группы {group}...")

    creation_date = await group_manager.get_group_creation_date(group)

    if creation_date:
        formatted_date = creation_date.strftime("%Y-%m-%d %H:%M:%S UTC")
        formatted_date_short = creation_date.strftime("%Y-%m-%d")

        print(f"✅ Группа создана: {formatted_date}")
        print(f"📊 Краткий формат: {formatted_date_short}")
    else:
        print("❌ Не удалось получить дату создания группы")


def main() -> None:
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
