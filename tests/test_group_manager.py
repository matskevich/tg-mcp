"""
Тесты для GroupManager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from telethon.errors import ChatAdminRequiredError, FloodWaitError
from tganalytics.domain.groups import GroupManager
from telethon.tl.types import User

@pytest.mark.asyncio
async def test_get_group_info_success(mock_telegram_client, mock_channel):
    """Тест успешного получения информации о группе"""
    # Настройка мока
    mock_telegram_client.get_entity.return_value = mock_channel
    
    # Создание менеджера
    group_manager = GroupManager(mock_telegram_client)
    
    # Выполнение теста
    result = await group_manager.get_group_info("testgroup")
    
    # Проверки
    assert result is not None
    assert result['id'] == mock_channel.id
    assert result['title'] == mock_channel.title
    assert result['username'] == mock_channel.username
    assert result['participants_count'] == mock_channel.participants_count
    assert result['type'] == 'channel'
    
    # Проверка вызова
    mock_telegram_client.get_entity.assert_called_once_with('@testgroup')

@pytest.mark.asyncio
async def test_get_group_info_without_at_prefix(mock_telegram_client, mock_channel):
    """Тест получения информации о группе без @ префикса"""
    mock_telegram_client.get_entity.return_value = mock_channel
    
    group_manager = GroupManager(mock_telegram_client)
    result = await group_manager.get_group_info("testgroup")
    
    assert result is not None
    mock_telegram_client.get_entity.assert_called_once_with('@testgroup')

@pytest.mark.asyncio
async def test_get_group_info_not_found(mock_telegram_client):
    """Тест обработки случая, когда группа не найдена"""
    mock_telegram_client.get_entity.side_effect = Exception("Group not found")
    
    group_manager = GroupManager(mock_telegram_client)
    result = await group_manager.get_group_info("nonexistent")
    
    assert result is None

@pytest.mark.asyncio
async def test_get_participants_success(mock_telegram_client, mock_channel, mock_participants_iterator):
    """Тест успешного получения участников группы"""
    # Настройка моков
    mock_telegram_client.get_entity.return_value = mock_channel
    mock_telegram_client.iter_participants.return_value = mock_participants_iterator
    
    group_manager = GroupManager(mock_telegram_client)
    participants = await group_manager.get_participants("testgroup", limit=10)
    
    assert len(participants) == 1
    assert participants[0]['id'] == 123456789
    assert participants[0]['username'] == "test_user"
    assert participants[0]['first_name'] == "Test"
    assert participants[0]['is_bot'] == False

@pytest.mark.asyncio
async def test_get_participants_exclude_bots(mock_telegram_client, mock_channel, mock_bot_and_user_iterator):
    """Тест исключения ботов из списка участников"""
    # Настройка моков
    mock_telegram_client.get_entity.return_value = mock_channel
    mock_telegram_client.iter_participants.return_value = mock_bot_and_user_iterator
    
    group_manager = GroupManager(mock_telegram_client)
    participants = await group_manager.get_participants("testgroup", limit=10)
    
    # Должен быть только обычный пользователь, бот исключен
    assert len(participants) == 1
    assert participants[0]['username'] == "regular_user"
    assert participants[0]['is_bot'] == False

@pytest.mark.asyncio
async def test_get_participants_admin_required_error(mock_telegram_client, mock_channel):
    """Тест обработки ошибки отсутствия прав администратора"""
    mock_telegram_client.get_entity.return_value = mock_channel
    mock_telegram_client.iter_participants.side_effect = ChatAdminRequiredError("No admin rights")
    
    group_manager = GroupManager(mock_telegram_client)
    participants = await group_manager.get_participants("testgroup")
    
    assert participants == []

@pytest.mark.asyncio
async def test_get_participants_flood_wait_error(mock_telegram_client, mock_channel):
    """Тест обработки ошибки превышения лимита запросов"""
    mock_telegram_client.get_entity.return_value = mock_channel
    mock_telegram_client.iter_participants.side_effect = FloodWaitError(60)
    
    group_manager = GroupManager(mock_telegram_client)
    participants = await group_manager.get_participants("testgroup")
    
    assert participants == []

@pytest.mark.asyncio
async def test_search_participants_success(mock_telegram_client, mock_participants_iterator):
    """Тест успешного поиска участников"""
    mock_telegram_client.iter_participants.return_value = mock_participants_iterator
    
    group_manager = GroupManager(mock_telegram_client)
    participants = await group_manager.search_participants("testgroup", "test", limit=10)
    
    assert len(participants) == 1
    assert participants[0]['username'] == "test_user"
    
    # Проверяем, что поиск вызван с правильными параметрами (с добавленным @)
    mock_telegram_client.iter_participants.assert_called_once_with(
        "@testgroup", search="test", limit=10
    )

@pytest.mark.asyncio
async def test_search_participants_empty_result(mock_telegram_client):
    """Тест поиска участников с пустым результатом"""
    from tests.conftest import AsyncIteratorMock
    mock_telegram_client.iter_participants.return_value = AsyncIteratorMock([])
    
    group_manager = GroupManager(mock_telegram_client)
    participants = await group_manager.search_participants("testgroup", "nonexistent")
    
    assert participants == []

@pytest.mark.asyncio
async def test_export_participants_to_csv_success(mock_telegram_client, mock_channel, sample_participants, tmp_path):
    """Тест успешного экспорта участников в CSV"""
    # Создаем моки пользователей из sample_participants
    from tests.conftest import AsyncIteratorMock
    
    mock_users = []
    for participant in sample_participants:
        user = MagicMock(spec=User)
        user.id = participant['id']
        user.username = participant['username']
        user.first_name = participant['first_name']
        user.last_name = participant['last_name']
        user.phone = participant['phone']
        user.bot = participant['is_bot']
        user.verified = participant['is_verified']
        user.premium = participant['is_premium']
        user.status = participant['status']
        mock_users.append(user)
    
    # Настройка моков
    mock_telegram_client.get_entity.return_value = mock_channel
    mock_telegram_client.iter_participants.return_value = AsyncIteratorMock(mock_users)
    
    group_manager = GroupManager(mock_telegram_client)
    
    # Создаем временный файл
    csv_file = tmp_path / "test_participants.csv"
    
    # Выполняем экспорт
    result = await group_manager.export_participants_to_csv("testgroup", str(csv_file), limit=10)
    
    assert result == True
    assert csv_file.exists()
    
    # Проверяем содержимое файла
    content = csv_file.read_text(encoding='utf-8')
    assert "id,username,first_name,last_name,phone,is_verified,is_premium,status" in content
    assert "user1" in content
    assert "user2" in content

@pytest.mark.asyncio
async def test_export_participants_to_csv_no_participants(mock_telegram_client, mock_channel, tmp_path):
    """Тест экспорта при отсутствии участников"""
    from tests.conftest import AsyncIteratorMock
    
    mock_telegram_client.get_entity.return_value = mock_channel
    mock_telegram_client.iter_participants.return_value = AsyncIteratorMock([])
    
    group_manager = GroupManager(mock_telegram_client)
    csv_file = tmp_path / "empty_participants.csv"
    
    result = await group_manager.export_participants_to_csv("testgroup", str(csv_file))
    
    assert result == False
    assert not csv_file.exists() 