import os
import asyncio
import stat
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from dotenv import load_dotenv
from telethon.tl.types import User
from .limiter import safe_call, get_rate_limiter
from .metrics import (
    increment_rate_limit_requests_total,
    increment_rate_limit_throttled_total,
    increment_flood_wait_events_total,
    observe_tele_call_latency_seconds,
)

load_dotenv()

# Безопасные пути для хранения данных (настраиваемые)
# Можно переопределить через SESSION_DIR, по умолчанию в data/sessions
SESSION_DIR = Path(os.getenv("SESSION_DIR", "data/sessions"))
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# Усиление прав доступа для каталога/файлов сессии
def _harden_session_storage(directory: Path, session_file: Path) -> None:
    try:
        # Каталог только для владельца: 700
        current_mode = directory.stat().st_mode & 0o777
        if current_mode != 0o700:
            directory.chmod(0o700)
    except Exception:
        pass
    try:
        if session_file.exists():
            # Файл только для владельца: 600
            file_mode = session_file.stat().st_mode & 0o777
            if file_mode != 0o600:
                session_file.chmod(0o600)
    except Exception:
        pass

api_id   = int(os.getenv("TG_API_ID", 0))
api_hash = os.getenv("TG_API_HASH", "")
session_name = os.getenv("SESSION_NAME", "s16_session")
session_path = str(SESSION_DIR / session_name)

# Проверка конфигурации
if not api_id or not api_hash:
    raise ValueError("❌ Необходимо указать TG_API_ID и TG_API_HASH в .env файле")

_client = None
_clients_by_path = {}

def get_client():
    global _client
    if _client is None:
        # Усиливаем права хранилища перед созданием клиента
        _harden_session_storage(SESSION_DIR, Path(session_path))
        _client = TelegramClient(session_path, api_id, api_hash)
    return _client

def get_client_for_session(custom_session_file_path: str):
    """Возвращает TelegramClient для указанного файла сессии.

    Не влияет на глобальный клиент; кеширует клиентов по полному пути.
    """
    if not custom_session_file_path:
        return get_client()
    session_file = Path(custom_session_file_path)
    session_dir = session_file.parent
    session_dir.mkdir(parents=True, exist_ok=True)
    # Усиливаем права
    _harden_session_storage(session_dir, session_file)
    resolved = session_file.resolve()
    key = str(resolved)
    client = _clients_by_path.get(key)
    if client is None:
        # Telethon appends .session automatically — strip it to avoid double extension
        session_name = str(resolved.with_suffix("")) if resolved.suffix == ".session" else str(resolved)
        client = TelegramClient(session_name, api_id, api_hash)
        _clients_by_path[key] = client
    return client

async def test_connection():
    """Тестирует подключение к Telegram API с anti-spam защитой"""
    try:
        client = get_client()
        await client.start()
        
        # Используем safe_call для get_me() и метрики
        import time
        start = time.perf_counter()
        try:
            increment_rate_limit_requests_total()
            me = await safe_call(client.get_me, operation_type="api")
        except Exception as e:
            # Простейшая эвристика для FLOOD_WAIT
            if hasattr(e, "seconds"):
                increment_flood_wait_events_total()
            raise
        finally:
            observe_tele_call_latency_seconds(time.perf_counter() - start)
        print(f"✅ Подключение успешно: {me.username} (ID: {me.id})")
        
        # Показываем статистику anti-spam системы
        limiter = get_rate_limiter()
        stats = limiter.get_stats()
        print(f"🛡️  Anti-spam статус: API calls: {stats['api_calls']}, RPS: {stats['current_rps']}")
        
        await client.disconnect()
        # Усиливаем права после возможного создания/обновления файла сессии
        _harden_session_storage(SESSION_DIR, Path(session_path))
        return True
    except SessionPasswordNeededError:
        print("❌ Требуется двухфакторная аутентификация")
        return False
    except PhoneCodeInvalidError:
        print("❌ Неверный код подтверждения")
        return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
