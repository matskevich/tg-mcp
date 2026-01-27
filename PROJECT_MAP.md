# PROJECT MAP: TGflow (бывший S16-Leads)

**Date:** 2025-12-16  
**Purpose:** Быстрая навигация по структуре проекта

---

## 🎯 СУТЬ ПРОЕКТА

**TGflow** — инфраструктура для работы с Telegram через Telethon.

**Не про:** конкретный бизнес-кейс или лиды.  
**Про:** переиспользуемые инструменты для извлечения данных из Telegram и синхронизации с проектами.

---

## 📁 СТРУКТУРА ПРОЕКТА

```
tgflow/
│
├── packages/tg_core/              # 🎯 ЯДРО — переиспользуемая инфраструктура
│   ├── tg_core/infra/
│   │   ├── tele_client.py        # Управление Telegram сессиями
│   │   ├── limiter.py            # Rate limiting (4 RPS), антиспам
│   │   ├── metrics.py            # Метрики использования API
│   │   └── logging.py            # Структурированное логирование
│   │
│   ├── tg_core/domain/
│   │   └── groups.py             # GroupManager: участники, поиск, экспорт
│   │
│   └── tg_core/config/
│       └── loader.py              # Загрузка конфигурации
│
├── apps/                          # 📱 ПРИЛОЖЕНИЯ — используют ядро
│   ├── s16leads/                 # Legacy: S16-специфичная логика
│   ├── gconf/                     # GConf: аналитика и отчёты
│   ├── kuprianov/                 # Проект Kuprianov
│   ├── vahue/                     # Проект Vahue
│   └── wildtantra/                # Проект WildTantra
│
├── examples/                       # 💡 Примеры использования
│   ├── export_group_messages.py
│   ├── list_my_chats.py
│   └── test_group_functions.py
│
├── scripts/                        # 🔧 Утилиты
│   ├── setup_anti_spam_system.py
│   ├── security_check.py
│   └── prepare_for_transfer.py
│
├── tests/                          # ✅ Тесты
│   ├── test_group_manager.py
│   ├── test_limiter.py
│   └── core/
│
├── docs/                           # 📚 Документация
│   ├── ARCHITECTURE_SIMPLE.md
│   ├── telegram_observability_stack.md
│   ├── ANTI_SPAM_*.md
│   └── ...
│
├── data/                           # 💾 Данные (не коммитится)
│   ├── sessions/                  # Telegram сессии
│   ├── export/                    # Экспортированные данные
│   └── gconf/                     # GConf данные
│
└── .cursor/rules/                  # 🎨 Правила для AI-ассистентов
    ├── 60-arch-current.md         # Архитектура
    ├── 65-data-policy.md          # Политика данных
    └── 70-telegram-invariants.md  # Инварианты Telegram
```

---

## 🔑 КЛЮЧЕВЫЕ КОМПОНЕНТЫ

### `tg_core` — Ядро

**Назначение:** Переиспользуемая инфраструктура для работы с Telegram.

**Что внутри:**
- **Безопасный доступ к API:** управление сессиями, аутентификация
- **Антиспам-защита:** rate limiting (4 RPS), защита от FLOOD_WAIT
- **Доменные модели:** группы, участники, сообщения
- **Метрики и логирование:** отслеживание использования API

**Правила:**
- Все обращения к Telegram — только через `tg_core`
- Никаких прямых вызовов Telethon в `apps/*`
- `tg_core` не импортирует `apps/*`

### `apps/*` — Приложения

**Назначение:** Специфичная логика для разных проектов.

**Принципы:**
- Используют только публичный API `tg_core`
- Не импортируют друг друга
- Можно вынести в отдельный репозиторий

---

## 🛠️ КАК ИСПОЛЬЗОВАТЬ

### Базовое использование:

```python
from tg_core.infra.tele_client import get_client
from tg_core.domain.groups import GroupManager

# Получить клиент
client = get_client()
await client.start()

# Использовать GroupManager
manager = GroupManager(client)
participants = await manager.get_participants(group_id, limit=100)
```

### Через CLI:

```bash
# Использовать приложение
python3 gconf/src/cli.py participants <group_id> --limit 100
```

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ

- ✅ Ядро `tg_core` реализовано и работает
- ✅ Антиспам-система активна (4 RPS)
- ✅ Несколько приложений используют ядро
- ✅ Документация есть
- ⚠️ Название проекта не отражает суть (S16-Leads → TGflow)

---

## 🔄 ПЛАН ПЕРЕИМЕНОВАНИЯ

См. `PROJECT_MAP_AND_RENAME_PLAN.md` для детального плана.

**Кратко:**
1. Переименовать проект: S16-Leads → TGflow
2. Обновить документацию
3. Переименовать репозиторий на GitHub
4. Обновить все упоминания в коде

---

**Created:** 2025-12-16




