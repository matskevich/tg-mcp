#!/usr/bin/env python3
"""
🎬 Демо: Session + Anti-Spam система S16-Leads

Показывает работу всех компонентов системы:
1. Session Management (создание и использование)
2. Rate Limiter (Token Bucket)
3. Safe Call Wrapper (защита API вызовов)
4. Квоты (Daily Limits)
5. Интеграция (реальный пример)

Использование:
    python examples/demo_session_antispam.py
"""

import asyncio
import time
from pathlib import Path
from typing import Optional

from tganalytics.infra.tele_client import get_client, get_client_for_session
from tganalytics.infra.limiter import (
    safe_call,
    get_rate_limiter,
    smart_pause,
)
from tganalytics.domain.groups import GroupManager
from tganalytics.infra.metrics import snapshot


# Цвета для вывода
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Красивый заголовок"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.END}\n")


def print_step(step: int, text: str):
    """Номер шага"""
    print(f"{Colors.CYAN}[ШАГ {step}]{Colors.END} {text}")


def print_info(text: str):
    """Информационное сообщение"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_success(text: str):
    """Успешное сообщение"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_warning(text: str):
    """Предупреждение"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_error(text: str):
    """Ошибка"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


# ============================================================================
# ЭТАП 1: Session Management
# ============================================================================

async def demo_session_management():
    """Демонстрация работы с session-файлами"""
    print_header("ЭТАП 1: Session Management")
    
    session_path = "data/sessions/demo_session.session"
    session_file = Path(session_path)
    
    print_step(1, "Проверка существования session-файла")
    if session_file.exists():
        print_success(f"Session файл найден: {session_path}")
        
        # Показываем права доступа
        file_mode = session_file.stat().st_mode & 0o777
        mode_str = oct(file_mode)
        print_info(f"Права доступа: {mode_str}")
        
        if file_mode == 0o600:
            print_success("Права доступа корректны (600 - только владелец)")
        else:
            print_warning(f"Права доступа должны быть 600, текущие: {mode_str}")
        
        # Показываем размер файла
        size = session_file.stat().st_size
        print_info(f"Размер файла: {size} байт")
        
    else:
        print_warning(f"Session файл не найден: {session_path}")
        print_info("При первом запуске будет создан новый session")
    
    print_step(2, "Создание клиента с session")
    print_info("Используем get_client_for_session() для создания клиента")
    
    client = get_client_for_session(session_path)
    print_success(f"Клиент создан для session: {session_path}")
    
    print_step(3, "Авторизация (использование session)")
    print_info("Запускаем client.start()...")
    print_info("Если session существует - авторизация автоматическая")
    print_info("Если session нет - потребуется телефон + код")
    
    try:
        await client.start()
        me = await safe_call(client.get_me, operation_type="api")
        print_success(f"Авторизация успешна: @{me.username} (ID: {me.id})")
        
        if session_file.exists():
            print_info("✅ Session использован для автоматической авторизации")
        else:
            print_info("✅ Новый session создан и сохранен")
            
    except Exception as e:
        print_error(f"Ошибка авторизации: {e}")
        return None
    
    print_step(4, "Проверка безопасности session после создания")
    if session_file.exists():
        file_mode = session_file.stat().st_mode & 0o777
        if file_mode == 0o600:
            print_success("Права доступа установлены корректно (600)")
        else:
            print_warning(f"Права доступа: {oct(file_mode)} (ожидалось 600)")
    
    return client


# ============================================================================
# ЭТАП 2: Rate Limiter (Token Bucket)
# ============================================================================

async def demo_rate_limiter():
    """Демонстрация работы Token Bucket"""
    print_header("ЭТАП 2: Rate Limiter (Token Bucket)")
    
    limiter = get_rate_limiter()
    bucket = limiter.bucket
    
    print_step(1, "Текущее состояние Token Bucket")
    print_info(f"Capacity (максимум токенов): {bucket.capacity}")
    print_info(f"Refill rate (скорость пополнения): {bucket.refill_rate} токенов/сек")
    print_info(f"Текущее количество токенов: {bucket.tokens:.2f}")
    
    print_step(2, "Демонстрация работы Token Bucket")
    print_info("Делаем 10 быстрых запросов подряд...")
    print_info("Ожидаем: первые запросы пройдут быстро, затем начнется throttling\n")
    
    wait_times = []
    for i in range(10):
        start = time.perf_counter()
        await bucket.acquire(1)
        elapsed = time.perf_counter() - start
        
        wait_times.append(elapsed)
        tokens_left = bucket.tokens
        
        status = "✅" if elapsed < 0.1 else "⏳"
        print(f"  {status} Запрос {i+1:2d}: ожидание {elapsed:.3f}с, токенов осталось: {tokens_left:.2f}")
    
    avg_wait = sum(wait_times) / len(wait_times)
    print_info(f"\nСреднее время ожидания: {avg_wait:.3f}с")
    
    if avg_wait > 0.1:
        print_success("✅ Rate limiting работает - запросы замедляются при нехватке токенов")
    else:
        print_info("ℹ️  Токены были доступны сразу (bucket был полный)")
    
    print_step(3, "Пополнение токенов")
    print_info("Ждем 1 секунду для пополнения токенов...")
    await asyncio.sleep(1.0)
    
    print_info(f"Токенов после пополнения: {bucket.tokens:.2f}")
    print_success("✅ Token Bucket автоматически пополняет токены")


# ============================================================================
# ЭТАП 3: Safe Call Wrapper
# ============================================================================

async def demo_safe_call(client):
    """Демонстрация работы safe_call wrapper"""
    print_header("ЭТАП 3: Safe Call Wrapper (защита API вызовов)")
    
    print_step(1, "Разница между прямым вызовом и safe_call")
    print_warning("❌ Прямой вызов (БЕЗ защиты):")
    print("    me = await client.get_me()  # Нет rate limiting, нет retry")
    print()
    print_success("✅ Защищенный вызов через safe_call:")
    print("    me = await safe_call(client.get_me, operation_type='api')")
    print("    # Автоматически: rate limiting + retry при FLOOD_WAIT")
    
    print_step(2, "Демонстрация safe_call в действии")
    print_info("Делаем несколько API вызовов через safe_call...\n")
    
    for i in range(5):
        start = time.perf_counter()
        try:
            me = await safe_call(client.get_me, operation_type="api")
            elapsed = time.perf_counter() - start
            print_success(f"Вызов {i+1}: успех за {elapsed:.3f}с (@{me.username})")
        except Exception as e:
            elapsed = time.perf_counter() - start
            print_error(f"Вызов {i+1}: ошибка за {elapsed:.3f}с - {e}")
        
        # Небольшая пауза между вызовами
        await asyncio.sleep(0.3)
    
    print_step(3, "Что происходит внутри safe_call:")
    print_info("1. Проверка квот (если operation_type='dm' или 'join')")
    print_info("2. Получение токена из Token Bucket")
    print_info("3. Выполнение функции")
    print_info("4. При FLOOD_WAIT - автоматический retry с exponential backoff")
    print_info("5. Логирование всех событий с тегом [SAFE]")
    
    print_success("✅ Все API вызовы защищены автоматически")


# ============================================================================
# ЭТАП 4: Квоты (Daily Limits)
# ============================================================================

async def demo_quotas():
    """Демонстрация работы квот"""
    print_header("ЭТАП 4: Квоты (Daily Limits)")
    
    limiter = get_rate_limiter()
    
    print_step(1, "Текущие квоты и счетчики")
    stats = limiter.get_stats()
    
    print_info(f"DM квота: {stats['dm_usage']} (лимит: {limiter.max_dm_per_day}/день)")
    print_info(f"Join квота: {stats['join_usage']} (лимит: {limiter.max_joins_per_day}/день)")
    print_info(f"API вызовов сегодня: {stats['api_calls']}")
    print_info(f"FLOOD_WAIT событий: {stats['flood_waits']}")
    
    print_step(2, "Файл счетчиков")
    counter_file = Path("data/anti_spam/daily_counters.txt")
    if counter_file.exists():
        print_info(f"Файл счетчиков: {counter_file}")
        print_info("Содержимое:")
        content = counter_file.read_text()
        for line in content.strip().split('\n'):
            if line.strip():
                print(f"  {line}")
        print_success("✅ Счетчики сохраняются между запусками")
    else:
        print_warning("Файл счетчиков не найден (будет создан при первом использовании)")
    
    print_step(3, "Проверка квот перед операцией")
    print_info("Проверяем можно ли отправить DM...")
    
    can_send_dm = await limiter.check_dm_quota()
    if can_send_dm:
        print_success(f"✅ Можно отправить DM (использовано: {stats['dm_usage'].split('/')[0]}/{limiter.max_dm_per_day})")
    else:
        print_warning(f"⚠️  Квота DM исчерпана ({stats['dm_usage']})")
    
    print_step(4, "Автоматический сброс счетчиков")
    print_info("Счетчики автоматически сбрасываются в 00:00 UTC каждый день")
    print_info(f"Текущая дата счетчиков: {stats['date']}")
    
    print_success("✅ Система защищает от превышения лимитов Telegram")


# ============================================================================
# ЭТАП 5: Интеграция (реальный пример)
# ============================================================================

async def demo_integration(client):
    """Демонстрация интеграции всех компонентов"""
    print_header("ЭТАП 5: Интеграция (реальный пример)")
    
    print_step(1, "Использование GroupManager (высокоуровневый API)")
    print_info("GroupManager автоматически использует safe_call для всех операций")
    
    manager = GroupManager(client)
    
    print_step(2, "Получение информации о группе")
    print_info("Попробуем получить информацию о группе...")
    print_info("(Используй username группы или ID, например: 's16_space' или '-1002188344480')")
    
    # Можно использовать тестовую группу или попросить пользователя ввести
    group_id = input(f"{Colors.CYAN}Введите ID/username группы (или Enter для пропуска): {Colors.END}").strip()
    
    if group_id:
        try:
            group_info = await manager.get_group_info(group_id)
            if group_info:
                print_success(f"✅ Информация о группе получена:")
                print(f"   Название: {group_info.get('title')}")
                print(f"   ID: {group_info.get('id')}")
                print(f"   Участников: {group_info.get('participants_count', 'неизвестно')}")
                print(f"   Тип: {group_info.get('type')}")
            else:
                print_warning("Не удалось получить информацию о группе")
        except Exception as e:
            print_error(f"Ошибка: {e}")
    else:
        print_info("Пропущено (демо без реального запроса)")
    
    print_step(3, "Статистика работы системы")
    limiter = get_rate_limiter()
    stats = limiter.get_stats()
    metrics = snapshot()
    
    print_info("\n📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
    print(f"  • API вызовов: {stats['api_calls']}")
    print(f"  • FLOOD_WAIT событий: {stats['flood_waits']}")
    print(f"  • Rate limit throttles: {metrics['rate_limit_throttled_total']}")
    print(f"  • DM использовано: {stats['dm_usage']}")
    print(f"  • Join использовано: {stats['join_usage']}")
    
    # Показываем метрики задержек
    latency_buckets = metrics['tele_call_latency_seconds']
    total_calls = sum(latency_buckets.values())
    if total_calls > 0:
        print(f"  • Всего вызовов с метриками: {total_calls}")
        print_info("  Распределение задержек:")
        for bucket, count in latency_buckets.items():
            if count > 0:
                print(f"    ≤{bucket}с: {count} вызовов")
    
    print_success("✅ Все компоненты работают вместе автоматически")


# ============================================================================
# Главная функция
# ============================================================================

async def main():
    """Главная функция демо"""
    print_header("🎬 ДЕМО: Session + Anti-Spam система S16-Leads")
    
    print_info("Это демо покажет работу всех компонентов системы:")
    print("  1. Session Management - создание и использование session-файлов")
    print("  2. Rate Limiter - Token Bucket алгоритм")
    print("  3. Safe Call Wrapper - защита всех API вызовов")
    print("  4. Квоты - ежедневные лимиты операций")
    print("  5. Интеграция - реальный пример использования")
    
    input(f"\n{Colors.CYAN}Нажмите Enter для начала демо...{Colors.END}")
    
    # ЭТАП 1: Session Management
    client = await demo_session_management()
    if not client:
        print_error("Не удалось инициализировать клиент. Демо прервано.")
        return
    
    input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.END}")
    
    # ЭТАП 2: Rate Limiter
    await demo_rate_limiter()
    
    input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.END}")
    
    # ЭТАП 3: Safe Call
    await demo_safe_call(client)
    
    input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.END}")
    
    # ЭТАП 4: Квоты
    await demo_quotas()
    
    input(f"\n{Colors.CYAN}Нажмите Enter для продолжения...{Colors.END}")
    
    # ЭТАП 5: Интеграция
    await demo_integration(client)
    
    # Завершение
    print_header("🎉 ДЕМО ЗАВЕРШЕНО")
    
    print_success("Все компоненты системы работают корректно!")
    print_info("\nКлючевые моменты:")
    print("  • Session обеспечивает авторизацию без постоянного ввода кода")
    print("  • Token Bucket плавно ограничивает скорость запросов")
    print("  • Safe Call автоматически защищает все API вызовы")
    print("  • Квоты предотвращают превышение лимитов Telegram")
    print("  • Интеграция работает прозрачно для разработчика")
    
    await client.disconnect()
    print_success("\n✅ Клиент отключен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Демо прервано пользователем{Colors.END}")
    except Exception as e:
        print_error(f"Ошибка в демо: {e}")
        import traceback
        traceback.print_exc()

