"""
Anti-Spam Rate Limiter для защиты от блокировок Telegram
==========================================

Основные компоненты:
- TokenBucket: Алгоритм ограничения скорости запросов
- RateLimiter: Основной класс управления лимитами
- safe_call: Wrapper для безопасных API вызовов с retry
- smart_pause: Интеллектуальные паузы для больших операций

Принцип: "Не считай минуты — считай RPC-токены"
Цель: 4 запроса/сек с автоматической обработкой FLOOD_WAIT
"""

import asyncio
import time
import logging
from typing import Any, Callable, Dict, Optional, Union
from datetime import datetime, timedelta
from telethon.errors import FloodWaitError
import os
from pathlib import Path

# Настройка логирования с тегом SAFE
logger = logging.getLogger(__name__)

from .metrics import increment_rate_limit_throttled_total  # added for observability

class TokenBucket:
    """
    Token Bucket алгоритм для rate limiting
    
    Принцип работы:
    - Ведро имеет максимальную capacity (емкость)
    - Токены добавляются с постоянной скоростью refill_rate
    - При запросе тратится 1 токен
    - Если токенов нет - ждем их пополнения
    """
    
    def __init__(self, capacity: int = 10, refill_rate: float = 4.0):
        """
        Args:
            capacity: Максимальное количество токенов в ведре
            refill_rate: Скорость пополнения токенов в секунду (default: 4 RPS)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)  # Начинаем с полным ведром
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens_needed: int = 1) -> bool:
        """
        Получить токены из ведра
        
        Args:
            tokens_needed: Количество нужных токенов
            
        Returns:
            True если токены получены, False если недостаточно capacity
        """
        async with self._lock:
            now = time.time()
            
            # Пополняем токены на основе времени
            time_passed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                return True
            else:
                # Вычисляем время ожидания
                tokens_to_wait = tokens_needed - self.tokens
                wait_time = tokens_to_wait / self.refill_rate
                
                # observability: record throttling event
                try:
                    increment_rate_limit_throttled_total()
                except Exception:
                    pass
                
                logger.info(f"[SAFE] Rate limit: waiting {wait_time:.2f}s for {tokens_needed} tokens")
                await asyncio.sleep(wait_time)
                
                # После ожидания пытаемся снова
                self.tokens = min(self.capacity, self.tokens + wait_time * self.refill_rate)
                if self.tokens >= tokens_needed:
                    self.tokens -= tokens_needed
                    return True
                else:
                    return False
    
    def get_wait_time(self, tokens_needed: int = 1) -> float:
        """Получить время ожидания для токенов без их получения"""
        if self.tokens >= tokens_needed:
            return 0.0
        
        tokens_to_wait = tokens_needed - self.tokens
        return tokens_to_wait / self.refill_rate


class RateLimiter:
    """
    Основной класс управления rate limiting для Telegram API
    
    Возможности:
    - Глобальный rate limiting (4 RPS)
    - Квоты по операциям (DM, join/leave)
    - Счетчики использования
    - Персистентное хранение статистики
    """
    
    def __init__(self, 
                 rps: float = 4.0,
                 max_dm_per_day: int = 20,
                 max_joins_per_day: int = 20,
                 max_groups: int = 200,
                 data_dir: str = "data/anti_spam"):
        """
        Args:
            rps: Запросов в секунду
            max_dm_per_day: Максимум DM в сутки
            max_joins_per_day: Максимум join/leave в сутки
            max_groups: Максимум групп для аккаунта
            data_dir: Директория для хранения счетчиков
        """
        self.rps = rps
        self.max_dm_per_day = max_dm_per_day
        self.max_joins_per_day = max_joins_per_day
        self.max_groups = max_groups
        self.data_dir = Path(data_dir)
        
        # Создаем директорию если не существует
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Token bucket для общего rate limiting
        self.bucket = TokenBucket(capacity=int(rps * 2), refill_rate=rps)
        
        # Счетчики операций
        self.daily_counters = self._load_daily_counters()
        
        logger.info(f"[SAFE] RateLimiter initialized: {rps} RPS, {max_dm_per_day} DM/day, {max_joins_per_day} joins/day")
    
    def _load_daily_counters(self) -> Dict[str, Any]:
        """Загружаем ежедневные счетчики из файла"""
        counter_file = self.data_dir / "daily_counters.txt"
        today = datetime.now().strftime("%Y-%m-%d")
        
        default_counters = {
            "date": today,
            "dm_count": 0,
            "join_count": 0,
            "api_calls": 0,
            "flood_waits": 0
        }
        
        if not counter_file.exists():
            self._save_daily_counters(default_counters)
            return default_counters
        
        try:
            with open(counter_file, 'r') as f:
                lines = f.readlines()
                if not lines:
                    return default_counters
                
                counters = {}
                for line in lines:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key == "date":
                            counters[key] = value
                        else:
                            counters[key] = int(value)
                
                # Если новый день - сбрасываем счетчики
                if counters.get("date") != today:
                    logger.info(f"[SAFE] New day detected, resetting daily counters")
                    return default_counters
                
                return counters
        except Exception as e:
            logger.warning(f"[SAFE] Failed to load counters: {e}, using defaults")
            return default_counters
    
    def _save_daily_counters(self, counters: Dict[str, Any]):
        """Сохраняем ежедневные счетчики в файл"""
        counter_file = self.data_dir / "daily_counters.txt"
        try:
            with open(counter_file, 'w') as f:
                for key, value in counters.items():
                    f.write(f"{key}={value}\n")
        except Exception as e:
            logger.error(f"[SAFE] Failed to save counters: {e}")
    
    async def check_dm_quota(self) -> bool:
        """Проверяем квоту на DM сообщения"""
        return self.daily_counters.get("dm_count", 0) < self.max_dm_per_day
    
    async def check_join_quota(self) -> bool:
        """Проверяем квоту на join/leave операции"""
        return self.daily_counters.get("join_count", 0) < self.max_joins_per_day
    
    async def increment_dm_counter(self):
        """Увеличиваем счетчик DM"""
        self.daily_counters["dm_count"] = self.daily_counters.get("dm_count", 0) + 1
        self._save_daily_counters(self.daily_counters)
        logger.info(f"[SAFE] DM counter: {self.daily_counters['dm_count']}/{self.max_dm_per_day}")
    
    async def increment_join_counter(self):
        """Увеличиваем счетчик join/leave"""
        self.daily_counters["join_count"] = self.daily_counters.get("join_count", 0) + 1
        self._save_daily_counters(self.daily_counters)
        logger.info(f"[SAFE] Join counter: {self.daily_counters['join_count']}/{self.max_joins_per_day}")
    
    async def increment_api_counter(self):
        """Увеличиваем счетчик API вызовов"""
        self.daily_counters["api_calls"] = self.daily_counters.get("api_calls", 0) + 1
        # Сохраняем счетчик сразу для тестов, в продакшене можно оптимизировать
        self._save_daily_counters(self.daily_counters)
        if self.daily_counters["api_calls"] % 100 == 0:  # Логируем каждые 100 вызовов
            logger.info(f"[SAFE] API calls today: {self.daily_counters['api_calls']}")
    
    async def increment_flood_counter(self, wait_time: int):
        """Увеличиваем счетчик FLOOD_WAIT"""
        self.daily_counters["flood_waits"] = self.daily_counters.get("flood_waits", 0) + 1
        self._save_daily_counters(self.daily_counters)
        logger.warning(f"[SAFE] FLOOD_WAIT #{self.daily_counters['flood_waits']} for {wait_time}s")
        
        # Алерт при критических значениях
        if wait_time > 600:  # Более 10 минут
            logger.error(f"[SAFE] CRITICAL: FLOOD_WAIT {wait_time}s - possible account risk!")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить текущую статистику"""
        return {
            "date": self.daily_counters.get("date"),
            "dm_usage": f"{self.daily_counters.get('dm_count', 0)}/{self.max_dm_per_day}",
            "join_usage": f"{self.daily_counters.get('join_count', 0)}/{self.max_joins_per_day}",
            "api_calls": self.daily_counters.get("api_calls", 0),
            "flood_waits": self.daily_counters.get("flood_waits", 0),
            "current_rps": self.rps
        }


# Глобальный экземпляр rate limiter
_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    """Получить глобальный экземпляр rate limiter (Singleton pattern)"""
    global _rate_limiter
    if _rate_limiter is None:
        # Загружаем параметры из .env
        rps = float(os.getenv("RATE_RPS", "4.0"))
        max_dm = int(os.getenv("MAX_DM_PER_DAY", "20"))
        max_joins = int(os.getenv("MAX_JOINS_PER_DAY", "20"))
        max_groups = int(os.getenv("MAX_GROUPS", "200"))
        
        _rate_limiter = RateLimiter(
            rps=rps,
            max_dm_per_day=max_dm,
            max_joins_per_day=max_joins,
            max_groups=max_groups
        )
    return _rate_limiter


async def safe_call(func: Callable, *args, max_retries: int = 3, operation_type: str = "api", **kwargs) -> Any:
    """
    Безопасный wrapper для Telegram API вызовов с rate limiting и retry
    
    Args:
        func: Функция для вызова
        *args: Аргументы функции
        max_retries: Максимальное количество повторов
        operation_type: Тип операции ("api", "dm", "join") для квот
        **kwargs: Keyword аргументы функции
    
    Returns:
        Результат вызова функции
        
    Raises:
        FloodWaitError: Если превышены все попытки retry
        Exception: Другие ошибки от функции
    """
    limiter = get_rate_limiter()
    
    # Проверяем квоты перед выполнением
    if operation_type == "dm":
        if not await limiter.check_dm_quota():
            raise Exception(f"[SAFE] DM quota exceeded: {limiter.daily_counters.get('dm_count', 0)}/{limiter.max_dm_per_day}")
    elif operation_type == "join":
        if not await limiter.check_join_quota():
            raise Exception(f"[SAFE] Join quota exceeded: {limiter.daily_counters.get('join_count', 0)}/{limiter.max_joins_per_day}")
    
    retry_count = 0
    base_wait = 1.0  # Базовое время ожидания для exponential backoff
    
    while retry_count <= max_retries:
        try:
            # Rate limiting перед каждым вызовом
            await limiter.bucket.acquire(1)
            await limiter.increment_api_counter()
            
            # Выполняем функцию
            logger.debug(f"[SAFE] Calling {func.__name__} (attempt {retry_count + 1}/{max_retries + 1})")
            result = await func(*args, **kwargs)
            
            # Увеличиваем соответствующие счетчики при успехе
            if operation_type == "dm":
                await limiter.increment_dm_counter()
            elif operation_type == "join":
                await limiter.increment_join_counter()
            
            return result
            
        except FloodWaitError as e:
            retry_count += 1
            wait_time = e.seconds
            
            await limiter.increment_flood_counter(wait_time)
            
            if retry_count > max_retries:
                logger.error(f"[SAFE] Max retries exceeded for {func.__name__} after FLOOD_WAIT")
                raise e
            
            # Exponential backoff + wait time from Telegram
            total_wait = wait_time + (base_wait * (2 ** (retry_count - 1)))
            logger.warning(f"[SAFE] FLOOD_WAIT {wait_time}s + backoff {total_wait - wait_time:.1f}s, retry {retry_count}/{max_retries}")
            
            await asyncio.sleep(total_wait)
            
        except Exception as e:
            # Для других ошибок не делаем retry
            logger.error(f"[SAFE] Error in {func.__name__}: {e}")
            raise e
    
    # Не должно сюда дойти
    raise Exception(f"[SAFE] Unexpected end of retry loop for {func.__name__}")


async def smart_pause(operation_type: str, count: int = 1):
    """
    Интеллектуальные паузы для больших операций
    
    Args:
        operation_type: Тип операции ("participants", "dm_batch", "join_batch")
        count: Количество обработанных элементов
    """
    if operation_type == "participants":
        # Каждые 5000 участников - пауза 1 секунда
        if count > 0 and count % 5000 == 0:
            logger.info(f"[SAFE] Smart pause: {count} participants processed, sleeping 1s")
            await asyncio.sleep(1.0)
    
    elif operation_type == "dm_batch":
        # После каждых 20 DM - пауза 60 секунд
        if count > 0 and count % 20 == 0:
            logger.info(f"[SAFE] Smart pause: {count} DMs sent, sleeping 60s")
            await asyncio.sleep(60.0)
    
    elif operation_type == "join_batch":
        # После каждого join/leave - пауза 3 секунды
        if count > 0:
            logger.info(f"[SAFE] Smart pause: join/leave operation, sleeping 3s")
            await asyncio.sleep(3.0)


def setup_safe_logging():
    """Настройка логирования с тегом SAFE для мониторинга"""
    
    # Создаем директорию для логов
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Настраиваем форматирование
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler для SAFE логов
    safe_log_file = log_dir / f"safe_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(safe_log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Добавляем handler к нашему логгеру
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    
    logger.info("[SAFE] Logging initialized")


# Инициализация при импорте
setup_safe_logging() 