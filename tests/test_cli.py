"""
Тесты для CLI интерфейса
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from apps.s16leads.cli import main, handle_info, handle_participants, handle_search, handle_export

@pytest.mark.asyncio
async def test_cli_info_command(mock_telegram_client, mock_channel):
    """Тест команды info в CLI"""
    with patch('apps.s16leads.cli.get_client') as mock_get_client:
        mock_get_client.return_value = mock_telegram_client
        
        # Мокаем GroupManager
        with patch('apps.s16leads.cli.GroupManager') as mock_group_manager_class:
            mock_group_manager = AsyncMock()
            mock_group_manager_class.return_value = mock_group_manager
            mock_group_manager.get_group_info.return_value = {
                'id': -100123456789,
                'title': 'Test Group',
                'username': 'testgroup',
                'participants_count': 1000,
                'type': 'channel'
            }
            
            # Тестируем функцию
            await handle_info(mock_group_manager, "testgroup")
            
            # Проверяем вызов
            mock_group_manager.get_group_info.assert_called_once_with("testgroup")

@pytest.mark.asyncio
async def test_cli_participants_command_json(mock_telegram_client, sample_participants):
    """Тест команды participants с JSON форматом"""
    with patch('apps.s16leads.cli.get_client') as mock_get_client:
        mock_get_client.return_value = mock_telegram_client
        
        with patch('apps.s16leads.cli.GroupManager') as mock_group_manager_class:
            mock_group_manager = AsyncMock()
            mock_group_manager_class.return_value = mock_group_manager
            mock_group_manager.get_participants.return_value = sample_participants
            
            # Тестируем функцию
            await handle_participants(mock_group_manager, "testgroup", 10, "json")
            
            # Проверяем вызов
            mock_group_manager.get_participants.assert_called_once_with("testgroup", 10)

@pytest.mark.asyncio
async def test_cli_participants_command_text(mock_telegram_client, sample_participants):
    """Тест команды participants с текстовым форматом"""
    with patch('apps.s16leads.cli.get_client') as mock_get_client:
        mock_get_client.return_value = mock_telegram_client
        
        with patch('apps.s16leads.cli.GroupManager') as mock_group_manager_class:
            mock_group_manager = AsyncMock()
            mock_group_manager_class.return_value = mock_group_manager
            mock_group_manager.get_participants.return_value = sample_participants
            
            # Тестируем функцию
            await handle_participants(mock_group_manager, "testgroup", 10, "text")
            
            # Проверяем вызов
            mock_group_manager.get_participants.assert_called_once_with("testgroup", 10)

@pytest.mark.asyncio
async def test_cli_search_command(mock_telegram_client, sample_participants):
    """Тест команды search"""
    with patch('apps.s16leads.cli.get_client') as mock_get_client:
        mock_get_client.return_value = mock_telegram_client
        
        with patch('apps.s16leads.cli.GroupManager') as mock_group_manager_class:
            mock_group_manager = AsyncMock()
            mock_group_manager_class.return_value = mock_group_manager
            mock_group_manager.search_participants.return_value = sample_participants
            
            # Тестируем функцию
            await handle_search(mock_group_manager, "testgroup", "test", 10, "json")
            
            # Проверяем вызов
            mock_group_manager.search_participants.assert_called_once_with("testgroup", "test", 10)

@pytest.mark.asyncio
async def test_cli_export_command_json(mock_telegram_client, sample_participants, tmp_path):
    """Тест команды export с JSON форматом"""
    with patch('apps.s16leads.cli.get_client') as mock_get_client:
        mock_get_client.return_value = mock_telegram_client
        
        with patch('apps.s16leads.cli.GroupManager') as mock_group_manager_class:
            mock_group_manager = AsyncMock()
            mock_group_manager_class.return_value = mock_group_manager
            mock_group_manager.get_participants.return_value = sample_participants
            
            # Создаем временный файл
            export_file = tmp_path / "test_export.json"
            
            # Тестируем функцию
            await handle_export(mock_group_manager, "testgroup", str(export_file), 10)
            
            # Проверяем вызов
            mock_group_manager.get_participants.assert_called_once_with("testgroup", 10)
            
            # Проверяем, что файл создан
            assert export_file.exists()

@pytest.mark.asyncio
async def test_cli_export_command_csv(mock_telegram_client, sample_participants, tmp_path):
    """Тест команды export с CSV форматом"""
    with patch('apps.s16leads.cli.get_client') as mock_get_client:
        mock_get_client.return_value = mock_telegram_client
        
        with patch('apps.s16leads.cli.GroupManager') as mock_group_manager_class:
            mock_group_manager = AsyncMock()
            mock_group_manager_class.return_value = mock_group_manager
            mock_group_manager.export_participants_to_csv.return_value = True
            
            # Создаем временный файл
            export_file = tmp_path / "test_export.csv"
            
            # Тестируем функцию
            await handle_export(mock_group_manager, "testgroup", str(export_file), 10)
            
            # Проверяем вызов
            mock_group_manager.export_participants_to_csv.assert_called_once_with("testgroup", str(export_file), 10)

@pytest.mark.asyncio
async def test_cli_main_function():
    """Тест основной функции main"""
    with patch('apps.s16leads.cli.argparse.ArgumentParser') as mock_parser_class:
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        
        # Мокаем аргументы
        mock_args = MagicMock()
        mock_args.command = 'info'
        mock_args.group = 'testgroup'
        mock_args.limit = 100
        mock_args.query = None
        mock_args.output = None
        mock_args.format = 'json'
        mock_parser.parse_args.return_value = mock_args
        
        with patch('apps.s16leads.cli.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            with patch('apps.s16leads.cli.GroupManager') as mock_group_manager_class:
                mock_group_manager = AsyncMock()
                mock_group_manager_class.return_value = mock_group_manager
                
                # Тестируем функцию
                await main()
                
                # Проверяем вызовы
                mock_client.start.assert_called_once()
                mock_client.disconnect.assert_called_once()
                mock_group_manager_class.assert_called_once_with(mock_client)

@pytest.mark.asyncio
async def test_cli_main_function_with_search():
    """Тест основной функции main с командой search"""
    with patch('apps.s16leads.cli.argparse.ArgumentParser') as mock_parser_class:
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        
        # Мокаем аргументы для search
        mock_args = MagicMock()
        mock_args.command = 'search'
        mock_args.group = 'testgroup'
        mock_args.limit = 50
        mock_args.query = 'test'
        mock_args.output = None
        mock_args.format = 'json'
        mock_parser.parse_args.return_value = mock_args
        
        with patch('apps.s16leads.cli.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            with patch('apps.s16leads.cli.GroupManager') as mock_group_manager_class:
                mock_group_manager = AsyncMock()
                mock_group_manager_class.return_value = mock_group_manager
                # Возвращаем реальные данные вместо моков для JSON сериализации
                mock_group_manager.search_participants.return_value = [
                    {
                        'id': 123456789,
                        'username': 'test_user',
                        'first_name': 'Test',
                        'last_name': 'User',
                        'phone': '+1234567890',
                        'is_bot': False,
                        'is_verified': False,
                        'is_premium': False,
                        'status': None
                    }
                ]
                
                # Тестируем функцию
                await main()
                
                # Проверяем вызовы
                mock_client.start.assert_called_once()
                mock_client.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_cli_main_function_with_export():
    """Тест основной функции main с командой export"""
    with patch('apps.s16leads.cli.argparse.ArgumentParser') as mock_parser_class:
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        
        # Мокаем аргументы для export
        mock_args = MagicMock()
        mock_args.command = 'export'
        mock_args.group = 'testgroup'
        mock_args.limit = 100
        mock_args.query = None
        mock_args.output = 'test_export.json'
        mock_args.format = 'json'
        mock_parser.parse_args.return_value = mock_args
        
        with patch('apps.s16leads.cli.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            with patch('apps.s16leads.cli.GroupManager') as mock_group_manager_class:
                mock_group_manager = AsyncMock()
                mock_group_manager_class.return_value = mock_group_manager
                # Возвращаем реальные данные вместо моков для JSON сериализации
                mock_group_manager.get_participants.return_value = [
                    {
                        'id': 123456789,
                        'username': 'test_user',
                        'first_name': 'Test',
                        'last_name': 'User',
                        'phone': '+1234567890',
                        'is_bot': False,
                        'is_verified': False,
                        'is_premium': False,
                        'status': None
                    }
                ]
                
                # Тестируем функцию
                await main()
                
                # Проверяем вызовы
                mock_client.start.assert_called_once()
                mock_client.disconnect.assert_called_once() 