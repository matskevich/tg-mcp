#!/usr/bin/env python3
"""
Скрипт для проверки безопасности проекта S16-Leads
"""

import os
import stat
from pathlib import Path
import subprocess
import sys

def check_file_permissions(file_path):
    """Проверяет права доступа к файлу"""
    try:
        st = os.stat(file_path)
        mode = stat.S_IMODE(st.st_mode)
        return mode == 0o600
    except FileNotFoundError:
        return False

def check_git_ignored(file_path):
    """Проверяет, игнорируется ли файл git"""
    try:
        result = subprocess.run(
            ['git', 'check-ignore', file_path],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("⚠️  Git не найден")
        return False

def main():
    print("🔍 Проверка безопасности проекта S16-Leads\n")
    
    # Проверка .env файла
    print("1. Проверка .env файла:")
    if os.path.exists('.env'):
        if check_git_ignored('.env'):
            print("   ✅ .env файл игнорируется git")
        else:
            print("   ❌ .env файл НЕ игнорируется git!")
        if check_file_permissions('.env'):
            print("   ✅ Правильные права доступа (600)")
        else:
            print("   ⚠️  Рекомендуется установить права 600")
    else:
        print("   ⚠️  .env файл не найден")
    
    # Проверка сессионных файлов
    print("\n2. Проверка сессионных файлов:")
    sessions_dir = Path("data/sessions")
    if sessions_dir.exists():
        session_files = list(sessions_dir.glob("*.session"))
        if session_files:
            for session_file in session_files:
                if check_git_ignored(str(session_file)):
                    print(f"   ✅ {session_file.name} игнорируется git")
                else:
                    print(f"   ❌ {session_file.name} НЕ игнорируется git!")
                
                if check_file_permissions(session_file):
                    print(f"   ✅ Правильные права доступа для {session_file.name}")
                else:
                    print(f"   ⚠️  Рекомендуется установить права 600 для {session_file.name}")
        else:
            print("   ℹ️  Сессионные файлы не найдены")
    else:
        print("   ℹ️  Директория sessions не существует")
    
    # Проверка подключения к Telegram
    print("\n3. Проверка подключения к Telegram:")
    try:
        import asyncio
        from tg_core.infra.tele_client import test_connection

        success = asyncio.run(test_connection())
        if success:
            print("   ✅ Подключение к Telegram успешно")
        else:
            print("   ❌ Подключение к Telegram не удалось (см. вывод выше)")
    except Exception as e:
        print(f"   ❌ Ошибка проверки: {e}")
    
    # Проверка зависимостей
    print("\n4. Проверка зависимостей:")
    try:
        import telethon
        print(f"   ✅ Telethon установлен (версия: {telethon.__version__})")
    except ImportError:
        print("   ❌ Telethon не установлен")
    
    try:
        import dotenv
        print("   ✅ python-dotenv установлен")
    except ImportError:
        print("   ❌ python-dotenv не установлен")
    
    print("\n📋 Рекомендации:")
    print("- Регулярно обновляйте зависимости: pip install -r requirements.txt --upgrade")
    print("- Проверяйте права доступа: chmod 600 data/sessions/*.session")
    print("- Не делитесь сессионными файлами")
    print("- Храните API ключи в безопасном месте")

if __name__ == "__main__":
    main() 