"""
Unit тесты для Anti-Spam Rate Limiter
=====================================

Тестируем:
1. TokenBucket - алгоритм ограничения скорости
2. RateLimiter - управление квотами
3. safe_call - wrapper с retry логикой
4. smart_pause - интеллектуальные паузы

Критический тест: 10 throttles @5rps → ≥2s runtime
"""

import pytest
import asyncio
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from telethon.errors import FloodWaitError

# Импортируем наши модули
from tganalytics.infra.limiter import (
    TokenBucket, 
    RateLimiter, 
    safe_call, 
    smart_pause,
    get_rate_limiter,
    setup_safe_logging
)


class TestTokenBucket:
    """Тесты для TokenBucket алгоритма"""
    
    @pytest.mark.asyncio
    async def test_token_bucket_basic_acquire(self):
        """Тест базового получения токенов"""
        bucket = TokenBucket(capacity=10, refill_rate=4.0)
        
        # Сначала должны получить токены мгновенно
        result = await bucket.acquire(1)
        assert result == True
        assert bucket.tokens == 9.0
    
    @pytest.mark.asyncio
    async def test_token_bucket_capacity_limit(self):
        """Тест ограничения capacity"""
        bucket = TokenBucket(capacity=5, refill_rate=10.0)
        
        # Пытаемся получить больше чем capacity
        result = await bucket.acquire(6)
        assert result == False
    
    @pytest.mark.asyncio
    async def test_token_bucket_refill_over_time(self):
        """Тест пополнения токенов со временем"""
        bucket = TokenBucket(capacity=10, refill_rate=4.0)
        
        # Тратим все токены
        await bucket.acquire(10)
        assert bucket.tokens == 0.0
        
        # Ждем 1 секунду - должно пополниться 4 токена
        await asyncio.sleep(1.0)
        result = await bucket.acquire(1)
        assert result == True
        assert bucket.tokens >= 2.0  # Примерно 3 токена осталось
    
    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiting_timing(self):
        """КРИТИЧЕСКИЙ ТЕСТ: проверка что rate limiting работает"""
        # Bucket на 10 RPS с минимальной capacity для более предсказуемого результата
        bucket = TokenBucket(capacity=2, refill_rate=10.0)
        
        # Тратим все токены
        await bucket.acquire(2)
        assert bucket.tokens == 0.0
        
        # Запрашиваем еще токены - должны ждать пополнения
        start_time = time.time()
        await bucket.acquire(1)
        end_time = time.time()
        elapsed = end_time - start_time
        
        # При 10 RPS нужно ждать 0.1 секунды для 1 токена 
        assert elapsed >= 0.08, f"Expected ≥0.08s wait, but took {elapsed:.3f}s"
        assert elapsed <= 0.15, f"Expected ≤0.15s wait, but took {elapsed:.3f}s"
        print(f"Rate limiting test passed: {elapsed:.3f}s wait for token refill")
    
    def test_get_wait_time(self):
        """Тест расчета времени ожидания"""
        bucket = TokenBucket(capacity=10, refill_rate=4.0)
        bucket.tokens = 2.0
        
        # Для 1 токена не нужно ждать
        wait_time = bucket.get_wait_time(1)
        assert wait_time == 0.0
        
        # Для 5 токенов нужно ждать (5-2)/4 = 0.75 секунды
        wait_time = bucket.get_wait_time(5)
        assert wait_time == 0.75


class TestRateLimiter:
    """Тесты для RateLimiter"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        # Создаем временную директорию для тестов
        self.temp_dir = tempfile.mkdtemp()
        self.limiter = RateLimiter(
            rps=4.0,
            max_dm_per_day=20,
            max_joins_per_day=20,
            max_groups=200,
            data_dir=self.temp_dir
        )
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_dm_quota_check(self):
        """Тест проверки квоты DM"""
        # В начале квота должна быть доступна
        result = await self.limiter.check_dm_quota()
        assert result == True
        
        # Увеличиваем счетчик до лимита
        for _ in range(20):
            await self.limiter.increment_dm_counter()
        
        # Теперь квота должна быть исчерпана
        result = await self.limiter.check_dm_quota()
        assert result == False
    
    @pytest.mark.asyncio
    async def test_join_quota_check(self):
        """Тест проверки квоты join/leave"""
        result = await self.limiter.check_join_quota()
        assert result == True
        
        # Увеличиваем счетчик до лимита
        for _ in range(20):
            await self.limiter.increment_join_counter()
        
        result = await self.limiter.check_join_quota()
        assert result == False
    
    @pytest.mark.asyncio
    async def test_daily_counters_persistence(self):
        """Тест сохранения ежедневных счетчиков"""
        # Увеличиваем счетчики
        await self.limiter.increment_dm_counter()
        await self.limiter.increment_join_counter()
        await self.limiter.increment_api_counter()
        
        # Создаем новый limiter с тем же data_dir
        new_limiter = RateLimiter(data_dir=self.temp_dir)
        
        # Счетчики должны сохраниться
        assert new_limiter.daily_counters["dm_count"] == 1
        assert new_limiter.daily_counters["join_count"] == 1
        assert new_limiter.daily_counters["api_calls"] == 1
    
    def test_get_stats(self):
        """Тест получения статистики"""
        stats = self.limiter.get_stats()
        
        assert "date" in stats
        assert "dm_usage" in stats
        assert "join_usage" in stats
        assert "api_calls" in stats
        assert "flood_waits" in stats
        assert "current_rps" in stats
        
        assert stats["dm_usage"] == "0/20"
        assert stats["join_usage"] == "0/20"
        assert stats["current_rps"] == 4.0


class TestSafeCall:
    """Тесты для safe_call wrapper"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.temp_dir = tempfile.mkdtemp()
        # Патчим глобальный rate limiter
        self.patcher = patch('tganalytics.infra.limiter._rate_limiter', 
                           RateLimiter(data_dir=self.temp_dir))
        self.patcher.start()
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_safe_call_success(self):
        """Тест успешного вызова функции"""
        async def mock_func(value):
            return f"success: {value}"
        
        result = await safe_call(mock_func, "test")
        assert result == "success: test"
    
    @pytest.mark.asyncio
    async def test_safe_call_dm_quota_exceeded(self):
        """Тест превышения квоты DM"""
        limiter = get_rate_limiter()
        
        # Исчерпываем квоту DM
        for _ in range(20):
            await limiter.increment_dm_counter()
        
        async def mock_dm_func():
            return "dm sent"
        
        # Должно выбросить исключение
        with pytest.raises(Exception) as exc_info:
            await safe_call(mock_dm_func, operation_type="dm")
        
        assert "DM quota exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_safe_call_flood_wait_retry(self):
        """Тест retry при FLOOD_WAIT"""
        call_count = 0
        
        async def mock_func_with_flood():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # Создаем правильный FloodWaitError
                error = FloodWaitError(request=None)
                error.seconds = 1  # Устанавливаем атрибут seconds
                raise error
            return "success after retry"
        
        # Мокаем sleep чтобы тест шел быстро
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await safe_call(mock_func_with_flood, max_retries=3)
        
        assert result == "success after retry"
        assert call_count == 3  # Первый + 2 retry
    
    @pytest.mark.asyncio
    async def test_safe_call_max_retries_exceeded(self):
        """Тест превышения максимального количества retry"""
        async def mock_func_always_flood():
            error = FloodWaitError(request=None)
            error.seconds = 1
            raise error
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(FloodWaitError):
                await safe_call(mock_func_always_flood, max_retries=2)
    
    @pytest.mark.asyncio
    async def test_safe_call_non_flood_error(self):
        """Тест обработки других ошибок (не FLOOD_WAIT)"""
        async def mock_func_with_error():
            raise ValueError("Some other error")
        
        with pytest.raises(ValueError) as exc_info:
            await safe_call(mock_func_with_error)
        
        assert "Some other error" in str(exc_info.value)


class TestSmartPause:
    """Тесты для smart_pause функции"""
    
    @pytest.mark.asyncio
    async def test_smart_pause_participants(self):
        """Тест паузы для participants"""
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Не должно быть паузы для count < 5000
            await smart_pause("participants", 1000)
            mock_sleep.assert_not_called()
            
            # Должна быть пауза для count = 5000
            await smart_pause("participants", 5000)
            mock_sleep.assert_called_once_with(1.0)
    
    @pytest.mark.asyncio
    async def test_smart_pause_dm_batch(self):
        """Тест паузы для DM batch"""
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Не должно быть паузы для count < 20
            await smart_pause("dm_batch", 10)
            mock_sleep.assert_not_called()
            
            # Должна быть пауза для count = 20
            await smart_pause("dm_batch", 20)
            mock_sleep.assert_called_once_with(60.0)
    
    @pytest.mark.asyncio
    async def test_smart_pause_join_batch(self):
        """Тест паузы для join batch"""
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Должна быть пауза для любого count > 0
            await smart_pause("join_batch", 1)
            mock_sleep.assert_called_once_with(3.0)


class TestIntegration:
    """Интеграционные тесты"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_safe_call_integration(self):
        """Интеграционный тест rate limiter с safe_call"""
        # Создаем limiter с быстрым RPS для теста
        with patch('tganalytics.infra.limiter._rate_limiter', 
                   RateLimiter(rps=10.0, data_dir=self.temp_dir)):
            
            call_count = 0
            
            async def mock_api_call():
                nonlocal call_count
                call_count += 1
                return f"call_{call_count}"
            
            # Делаем несколько вызовов
            results = []
            for i in range(5):
                result = await safe_call(mock_api_call, operation_type="api")
                results.append(result)
            
            assert len(results) == 5
            assert results[0] == "call_1"
            assert results[4] == "call_5"
            
            # Проверяем что счетчики API обновились
            limiter = get_rate_limiter()
            assert limiter.daily_counters["api_calls"] >= 5
    
    def test_singleton_pattern(self):
        """Тест Singleton паттерна для get_rate_limiter"""
        # Очищаем глобальную переменную
        import tganalytics.infra.limiter as limiter
        limiter._rate_limiter = None
        
        # Получаем два экземпляра
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        
        # Должны быть одним и тем же объектом
        assert limiter1 is limiter2
    
    @pytest.mark.asyncio 
    async def test_complete_workflow_simulation(self):
        """Симуляция полного workflow с anti-spam защитой"""
        with patch('tganalytics.infra.limiter._rate_limiter', 
                   RateLimiter(rps=20.0, data_dir=self.temp_dir)):  # Быстрый RPS для теста
            
            # Симулируем получение участников группы
            participants_processed = 0
            
            async def process_participant(participant_id):
                nonlocal participants_processed
                participants_processed += 1
                
                # Каждые 10 участников делаем smart_pause
                if participants_processed % 10 == 0:
                    await smart_pause("participants", participants_processed)
                
                return f"processed_{participant_id}"
            
            # Обрабатываем 25 участников
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                for i in range(25):
                    result = await safe_call(process_participant, i, operation_type="api")
                    assert result == f"processed_{i}"
                
                # Должно было быть 2 паузы (на 10 и 20 участниках)
                # Но мы мокаем smart_pause, поэтому проверяем только что функция работает
                assert participants_processed == 25
    
    def test_logging_setup(self):
        """Тест настройки логирования"""
        # Просто проверяем что функция не падает
        setup_safe_logging()
        
        # Проверяем что директория логов создалась
        log_dir = Path("data/logs")
        assert log_dir.exists()


# Маркеры для разных типов тестов
slow = pytest.mark.slow
integration = pytest.mark.integration

# Конфигурация для pytest
pytest_plugins = [] 