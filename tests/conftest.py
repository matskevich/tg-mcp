"""
Конфигурация pytest для тестов S16-Leads
"""

import sys
from pathlib import Path
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from telethon import TelegramClient
from telethon.tl.types import User, Channel, Chat

# Make local `tg_core` importable in tests without sys.path hacks in app code.
REPO_ROOT = Path(__file__).resolve().parents[1]
TG_CORE_PKG = REPO_ROOT / "packages" / "tg_core"
if str(TG_CORE_PKG) not in sys.path:
    sys.path.insert(0, str(TG_CORE_PKG))

class AsyncIteratorMock:
    """Мок для асинхронного итератора"""
    def __init__(self, items):
        self.items = items
        self.index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item

@pytest.fixture
def mock_telegram_client():
    """Создает мок Telegram клиента"""
    client = AsyncMock(spec=TelegramClient)
    return client

@pytest.fixture
def mock_user():
    """Создает мок пользователя Telegram"""
    user = MagicMock(spec=User)
    user.id = 123456789
    user.username = "test_user"
    user.first_name = "Test"
    user.last_name = "User"
    user.phone = "+1234567890"
    user.bot = False
    user.verified = False
    user.premium = False
    user.status = None
    return user

@pytest.fixture
def mock_channel():
    """Создает мок канала/группы Telegram"""
    channel = MagicMock(spec=Channel)
    channel.id = -100123456789
    channel.title = "Test Group"
    channel.username = "testgroup"
    channel.participants_count = 1000
    return channel

@pytest.fixture
def sample_participants():
    """Возвращает список тестовых участников"""
    return [
        {
            'id': 123456789,
            'username': 'user1',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+1234567890',
            'is_bot': False,
            'is_verified': False,
            'is_premium': False,
            'status': None
        },
        {
            'id': 987654321,
            'username': 'user2',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone': '+0987654321',
            'is_bot': False,
            'is_verified': True,
            'is_premium': True,
            'status': 'online'
        }
    ]

@pytest.fixture
def mock_participants_iterator(mock_user):
    """Создает мок асинхронного итератора участников"""
    return AsyncIteratorMock([mock_user])

@pytest.fixture
def mock_bot_and_user_iterator():
    """Создает мок итератора с ботом и обычным пользователем"""
    # Создаем мок бота
    bot_user = MagicMock(spec=User)
    bot_user.id = 999999999
    bot_user.username = "test_bot"
    bot_user.first_name = "Test"
    bot_user.last_name = "Bot"
    bot_user.phone = None
    bot_user.bot = True
    bot_user.verified = False
    bot_user.premium = False
    bot_user.status = None
    
    # Создаем обычного пользователя
    regular_user = MagicMock(spec=User)
    regular_user.id = 123456789
    regular_user.username = "regular_user"
    regular_user.first_name = "Regular"
    regular_user.last_name = "User"
    regular_user.phone = "+1234567890"
    regular_user.bot = False
    regular_user.verified = False
    regular_user.premium = False
    regular_user.status = None
    
    return AsyncIteratorMock([bot_user, regular_user])

@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для асинхронных тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 