# 🏗️ Architectural Patterns для Telegram API в S16-leads

## 🛡️ **АНТИ-СПАМ ПЕРВЫЙ ЗАКОН**

> **"Каждый Telegram API вызов ДОЛЖЕН быть защищен анти-спам оберткой"**

Нет исключений. Нет "быстрых хаков". Нет "это только для тестов".

---

## 📋 **ОБЯЗАТЕЛЬНЫЕ ПАТТЕРНЫ**

### **1. 🔄 Safe API Call Pattern**

```python
# ✅ ПРАВИЛЬНО: Используйте _safe_api_call в group_manager.py
async def get_group_info(self, group_id: str):
    try:
        entity = await _safe_api_call(self.client.get_entity, group_id)
        return self._process_entity(entity)
    except Exception as e:
        logger.error(f"Error getting group info: {e}")
        return None

# ✅ ПРАВИЛЬНО: Используйте safe_call в других модулях  
from tganalytics.infra.limiter import safe_call

async def get_user_info(client, user_id):
    return await safe_call(
        client.get_entity, 
        user_id, 
        operation_type="api"
    )
```

### **2. 🔄 Bulk Operations Pattern**

```python
# ✅ ПРАВИЛЬНО: Batch processing с анти-спам защитой
async def get_participants_safe(self, group_id: str, limit: int = 1000):
    # Wrapper функция для batch операции
    async def get_participants_batch():
        users = []
        async for user in self.client.iter_participants(group_id, limit=limit):
            users.append(user)
            
            # Smart pause каждые 1000 пользователей
            if len(users) % 1000 == 0:
                await smart_pause("participants", len(users))
        return users
    
    # Вызов через safe_call
    return await _safe_api_call(get_participants_batch)
```

### **3. 🔄 Iterator Pattern**

```python
# ❌ НЕ ТАК: Прямой async for
async for dialog in client.iter_dialogs():
    process(dialog)

# ✅ ПРАВИЛЬНО: Wrapper + safe_call
async def get_dialogs_safe():
    dialogs = []
    async for dialog in client.iter_dialogs():
        dialogs.append(dialog)
    return dialogs

dialogs = await _safe_api_call(get_dialogs_safe)
for dialog in dialogs:
    process(dialog)
```

---

## 🏗️ **АРХИТЕКТУРНЫЕ СЛОИ**

### **Layer 1: Infrastructure (src/infra/)**

```python
# tele_client.py - Базовый клиент с анти-спам защитой
class TelegramClient:
    async def start(self):
        await self.client.start()
        # Проверка через safe_call
        me = await safe_call(self.client.get_me, operation_type="api")

# limiter.py - Анти-спам система
def safe_call(func, *args, operation_type="api", **kwargs):
    # Rate limiting + retry logic + FLOOD_WAIT handling
```

### **Layer 2: Core Business Logic (src/core/)**

```python
# group_manager.py - Бизнес логика групп
class GroupManager:
    def __init__(self, client: TelegramClient):
        self.client = client
    
    async def get_group_info(self, group_id):
        # Использует _safe_api_call для внутренних нужд
        return await _safe_api_call(self.client.get_entity, group_id)

# s16_config.py - Конфигурация без API вызовов
class S16Config:
    def get_space_group_id(self) -> int:
        return self.space_group_id
```

### **Layer 3: Application (examples/, src/cli.py)**

```python
# s16_crosscheck.py - Приложения используют Core слой
from tganalytics.domain.groups import GroupManager

async def crosscheck():
    manager = GroupManager(client)
    # Все API вызовы через GroupManager (уже защищены)
    participants = await manager.get_participants(group_id)
```

---

## 🔧 **TEMPLATES ДЛЯ НОВЫХ ФУНКЦИЙ**

### **Template 1: Simple API Call**

```python
async def new_telegram_function(self, param: str) -> Optional[Dict]:
    """
    Новая функция для работы с Telegram API
    
    Args:
        param: Описание параметра
        
    Returns:
        Результат или None при ошибке
    """
    try:
        # ОБЯЗАТЕЛЬНО: Используйте _safe_api_call
        result = await _safe_api_call(self.client.your_method, param)
        
        # Обработка результата
        if result:
            return self._process_result(result)
            
    except Exception as e:
        logger.error(f"Error in new_telegram_function: {e}")
        
    return None
```

### **Template 2: Bulk Operation**

```python
async def bulk_telegram_operation(self, items: List[str]) -> List[Dict]:
    """
    Bulk операция с анти-спам защитой
    
    Args:
        items: Список элементов для обработки
        
    Returns:
        Список результатов
    """
    results = []
    
    # Wrapper для bulk операции
    async def process_bulk():
        processed = []
        for i, item in enumerate(items):
            # Обработка одного элемента
            async for result in self.client.iter_something(item):
                processed.append(result)
                
                # Smart pause каждые 100 элементов
                if (i + 1) % 100 == 0:
                    await smart_pause("bulk_operation", i + 1)
                    
        return processed
    
    # ОБЯЗАТЕЛЬНО: Через safe_call
    return await _safe_api_call(process_bulk)
```

### **Template 3: New Manager Class**

```python
from tganalytics.infra.limiter import safe_call, smart_pause
from tganalytics.infra.tele_client import TelegramClient

class NewManager:
    """Менеджер для новой функциональности Telegram"""
    
    def __init__(self, client: TelegramClient):
        self.client = client
    
    async def new_method(self, param: str) -> Optional[Any]:
        """Новый метод с анти-спам защитой"""
        try:
            # Используйте safe_call для новых классов
            result = await safe_call(
                self.client.new_api_method, 
                param,
                operation_type="api"
            )
            return result
            
        except Exception as e:
            logger.error(f"Error in new_method: {e}")
            return None
```

---

## 🧪 **TESTING PATTERNS**

### **Test Template**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from tganalytics.domain.your_manager import YourManager

@pytest.mark.asyncio
async def test_your_function_success():
    """Тест успешного выполнения функции"""
    # Mock client
    mock_client = AsyncMock()
    mock_client.your_method.return_value = MagicMock()
    
    # Создание менеджера
    manager = YourManager(mock_client)
    
    # Выполнение теста  
    result = await manager.your_function("test_param")
    
    # Проверки
    assert result is not None
    mock_client.your_method.assert_called_once_with("test_param")
```

**❗ ВАЖНО:** В тестах НЕ нужно тестировать safe_call - он тестируется отдельно.

---

## 📊 **MONITORING & OBSERVABILITY**

### **Logging Pattern**

```python
import logging
logger = logging.getLogger(__name__)

async def monitored_function(self, param: str):
    """Функция с правильным логированием"""
    logger.info(f"Starting operation with param: {param}")
    
    try:
        result = await _safe_api_call(self.client.method, param)
        logger.info(f"Operation successful, result count: {len(result)}")
        return result
        
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
```

### **Statistics Pattern**

```python
async def stats_aware_function(self):
    """Функция с мониторингом статистики"""
    # Получаем статистику до операции
    limiter = get_rate_limiter()
    stats_before = limiter.get_stats()
    
    # Выполняем операцию
    result = await _safe_api_call(self.client.method)
    
    # Логируем статистику после
    stats_after = limiter.get_stats()
    logger.info(f"API calls: {stats_after['api_calls']} (+{stats_after['api_calls'] - stats_before['api_calls']})")
    
    return result
```

---

## ⚠️ **АНТИ-ПАТТЕРНЫ (НЕ ДЕЛАЙТЕ ТАК)**

### **❌ Прямые API вызовы**

```python
# ❌ НЕ ТАК
await client.get_entity(user_id)
async for user in client.iter_participants(group):
    process(user)

# ✅ ПРАВИЛЬНО  
await _safe_api_call(client.get_entity, user_id)
# или
await safe_call(client.get_entity, user_id, operation_type="api")
```

### **❌ Игнорирование ошибок**

```python
# ❌ НЕ ТАК
try:
    result = await client.get_entity(user_id)
except:
    pass  # Игнорируем все ошибки

# ✅ ПРАВИЛЬНО
try:
    result = await _safe_api_call(client.get_entity, user_id)
except FloodWaitError as e:
    logger.warning(f"FLOOD_WAIT {e.seconds}s, handled by safe_call")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return None
```

### **❌ Hardcoded delays**

```python
# ❌ НЕ ТАК
await asyncio.sleep(5)  # Произвольная задержка

# ✅ ПРАВИЛЬНО
await smart_pause("operation_type", count)  # Интеллектуальная пауза
```

---

## 🎯 **CHECKLIST ДЛЯ НОВЫХ ФУНКЦИЙ**

### **Before Writing Code:**

- [ ] Определил слой архитектуры (infra/core/app)
- [ ] Выбрал правильный pattern (simple/bulk/iterator)
- [ ] Понял где использовать `_safe_api_call` vs `safe_call`

### **While Writing Code:**

- [ ] Все Telegram API вызовы через обертки
- [ ] Добавил proper exception handling
- [ ] Использую smart_pause для больших операций
- [ ] Добавил логирование

### **Before Committing:**

- [ ] Запустил `make anti-spam-check`
- [ ] Запустил `make dev-check`
- [ ] Написал тесты с моками
- [ ] Обновил документацию если нужно

### **Before PR:**

- [ ] Запустил `make check-all`
- [ ] Проверил что CI проходит
- [ ] Заполнил code review checklist

---

## 🔗 **ПОЛЕЗНЫЕ ССЫЛКИ**

- 📋 [Code Review Checklist](CODE_REVIEW_CHECKLIST.md)
- 🛡️ [Anti-spam Audit Report](ANTI_SPAM_AUDIT_REPORT.md) 
- 🔧 [Makefile Commands](../Makefile) - `make help-security`
- ⚙️ [Pre-commit Setup](../.pre-commit-config.yaml)

---

**🎯 Remember:** Лучше потратить 5 минут на правильную анти-спам обертку, чем 5 часов на разбор блокировки аккаунта!