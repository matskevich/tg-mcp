import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from tganalytics.domain.groups import GroupManager


@pytest.fixture
def mock_telegram_client():
    """Мок Telegram клиента"""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_first_message():
    """Мок первого сообщения с датой"""
    message = MagicMock()
    message.date = datetime(2024, 7, 29, 11, 58, 7)
    return message


@pytest.mark.asyncio
async def test_get_group_creation_date_with_id(mock_telegram_client, mock_first_message):
    """Тест получения даты создания группы по ID"""
    
    # Создаем правильный async generator для iter_messages
    async def mock_iter_messages(*args, **kwargs):
        yield mock_first_message
    
    mock_telegram_client.iter_messages = mock_iter_messages
    
    group_manager = GroupManager(mock_telegram_client)
    
    # Тестируем с числовым ID
    result = await group_manager.get_group_creation_date(-1002188344480)
    
    assert result is not None
    assert result.year == 2024
    assert result.month == 7
    assert result.day == 29


@pytest.mark.asyncio
async def test_get_group_creation_date_with_string_id(mock_telegram_client, mock_first_message):
    """Тест получения даты создания группы по строковому ID"""
    
    async def mock_iter_messages(*args, **kwargs):
        yield mock_first_message
    
    mock_telegram_client.iter_messages = mock_iter_messages
    
    group_manager = GroupManager(mock_telegram_client)
    
    # Тестируем со строковым ID
    result = await group_manager.get_group_creation_date("-1002188344480")
    
    assert result is not None
    assert result.year == 2024


@pytest.mark.asyncio
async def test_get_group_creation_date_with_username(mock_telegram_client, mock_first_message):
    """Тест получения даты создания группы по username"""
    
    async def mock_iter_messages(*args, **kwargs):
        yield mock_first_message
    
    mock_telegram_client.iter_messages = mock_iter_messages
    
    group_manager = GroupManager(mock_telegram_client)
    
    # Тестируем с username без @
    result = await group_manager.get_group_creation_date("testgroup")
    
    assert result is not None


@pytest.mark.asyncio
async def test_get_group_creation_date_no_messages(mock_telegram_client):
    """Тест случая когда в группе нет сообщений"""
    
    async def mock_iter_messages(*args, **kwargs):
        # Пустой async generator
        if False:
            yield  # недостижимый код для создания async generator
    
    mock_telegram_client.iter_messages = mock_iter_messages
    
    group_manager = GroupManager(mock_telegram_client)
    
    result = await group_manager.get_group_creation_date(-1002188344480)
    
    assert result is None


@pytest.mark.asyncio
async def test_get_group_creation_date_error(mock_telegram_client):
    """Тест обработки ошибок при получении даты создания"""
    
    # Настраиваем мок для выброса исключения
    async def mock_iter_messages_error(*args, **kwargs):
        raise Exception("Connection error")
    
    mock_telegram_client.iter_messages = mock_iter_messages_error
    
    group_manager = GroupManager(mock_telegram_client)
    
    result = await group_manager.get_group_creation_date(-1002188344480)
    
    assert result is None