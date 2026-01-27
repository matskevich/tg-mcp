#!/usr/bin/env python3
"""
Пример использования функций для работы с группами Telegram
"""

import asyncio
import json
from tganalytics.infra.tele_client import get_client
from tganalytics.domain.groups import GroupManager

async def test_group_functions():
    """Тестирует основные функции работы с группами"""
    
    # Тестовая группа (замените на реальную)
    test_group = "python"  # Группа @python
    
    try:
        print("🚀 Тестирование функций работы с группами\n")
        
        # Получаем клиент
        client = get_client()
        await client.start()
        
        # Создаем менеджер групп
        group_manager = GroupManager(client)
        
        # 1. Получение информации о группе
        print("1️⃣ Получение информации о группе:")
        group_info = await group_manager.get_group_info(test_group)
        if group_info:
            print(f"   ✅ Группа: {group_info['title']}")
            print(f"   📊 Участников: {group_info['participants_count']}")
            print(f"   🔗 Username: @{group_info['username']}")
        else:
            print(f"   ❌ Группа {test_group} не найдена")
            return
        
        print()
        
        # 2. Получение участников (ограниченное количество)
        print("2️⃣ Получение участников группы:")
        participants = await group_manager.get_participants(test_group, limit=10)
        if participants:
            print(f"   ✅ Получено {len(participants)} участников:")
            for i, participant in enumerate(participants[:5], 1):  # Показываем только первые 5
                username = participant['username'] or 'Нет username'
                name = f"{participant['first_name'] or ''} {participant['last_name'] or ''}".strip()
                print(f"   {i}. {username} - {name}")
            if len(participants) > 5:
                print(f"   ... и еще {len(participants) - 5} участников")
        else:
            print("   ❌ Не удалось получить участников")
        
        print()
        
        # 3. Поиск участников
        print("3️⃣ Поиск участников:")
        search_results = await group_manager.search_participants(test_group, "admin", limit=5)
        if search_results:
            print(f"   ✅ Найдено {len(search_results)} участников с 'admin':")
            for i, participant in enumerate(search_results, 1):
                username = participant['username'] or 'Нет username'
                name = f"{participant['first_name'] or ''} {participant['last_name'] or ''}".strip()
                print(f"   {i}. {username} - {name}")
        else:
            print("   ℹ️ Участники с 'admin' не найдены")
        
        print()
        
        # 4. Экспорт в JSON
        print("4️⃣ Экспорт участников в JSON:")
        export_file = "data/export/participants_sample.json"
        participants_for_export = await group_manager.get_participants(test_group, limit=20)
        if participants_for_export:
            # Создаем директорию
            from pathlib import Path
            Path(export_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(participants_for_export, f, ensure_ascii=False, indent=2)
            print(f"   ✅ Экспортировано {len(participants_for_export)} участников в {export_file}")
        else:
            print("   ❌ Нет данных для экспорта")
        
        await client.disconnect()
        print("\n✅ Тестирование завершено успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")

if __name__ == "__main__":
    asyncio.run(test_group_functions()) 