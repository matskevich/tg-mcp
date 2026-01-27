#!/usr/bin/env python3
"""
Универсальная функция для отправки сообщений в группы Telegram

Использование:
    python examples/send_group_message.py "shipyard cohort 1" "текст сообщения"
    
Или из кода:
    from tganalytics.domain.groups import GroupManager
    manager = GroupManager(client)
    await manager.send_message("shipyard cohort 1", "Привет!")
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к пакетам
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = PROJECT_ROOT / "packages"
TG_CORE_DIR = PKG_DIR / "tg_core"
for p in (str(PKG_DIR), str(TG_CORE_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from tganalytics.infra.tele_client import get_client
from tganalytics.domain.groups import GroupManager


async def main():
    if len(sys.argv) < 3:
        print("Использование: python send_group_message.py <группа> <текст сообщения>")
        print('Пример: python send_group_message.py "shipyard cohort 1" "Привет из скрипта!"')
        sys.exit(1)
    
    group = sys.argv[1]
    message = sys.argv[2]
    
    print(f"🔍 Поиск группы: {group}")
    
    client = get_client()
    await client.start()
    
    try:
        manager = GroupManager(client)
        
        print(f"📤 Отправка сообщения через GroupManager.send_message (антиспам защита)...")
        success = await manager.send_message(group, message)
        
        if success:
            print(f"✅ Сообщение успешно отправлено в группу '{group}'")
            print("🛡️  Защита: rate limiting (4 RPS) + FLOOD_WAIT retry применены")
        else:
            print(f"❌ Не удалось отправить сообщение")
            sys.exit(1)
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())





