#!/usr/bin/env python3
"""
Скрипт для проверки соблюдения анти-спам требований в S16-leads
Проверяет что все Telegram API вызовы используют safe_call обертки
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Паттерны для поиска проблемных вызовов
DANGEROUS_PATTERNS = [
    # Прямые вызовы к client без safe_call
    r'await\s+(?:self\.)?client\.(get_entity|iter_participants|iter_dialogs|send_message|send_file|delete_messages|edit_message|forward_messages|get_participants)',
    r'(?:self\.)?client\.(get_entity|iter_participants|iter_dialogs|send_message|send_file|delete_messages|edit_message|forward_messages|get_participants)',
    # Raw MTProto вызовы через client(...)
    r'await\s+(?:self\.)?client\(',
    
    # Async for loops с client
    r'async\s+for\s+\w+\s+in\s+(?:self\.)?client\.',
    
    # Прямые вызовы telethon функций без обертки
    r'from\s+telethon\.tl\.functions\s+import.*\n.*await\s+client\(',
]

# Допустимые паттерны (исключения)
ALLOWED_PATTERNS = [
    r'await\s+_safe_api_call\(',
    r'await\s+safe_call\(',
    r'client\.start\(\)',
    r'client\.disconnect\(\)',
    r'client\.get_me\(',  # В tele_client.py есть safe_call обертка
    # Wrapper функции внутри safe_call - допустимы
    r'async\s+def\s+\w+.*:\s*$',  # Начало async функции
    r'async\s+for.*in\s+self\.client\..*:\s*$',  # Внутри wrapper функции
    # Комментарии и документация
    r'#.*client\.',
    r'""".*client\..*"""',
    r"'''.*client\..*'''",
]

# Файлы которые нужно проверять
INCLUDE_PATTERNS = [
    '**/*.py'
]

# Файлы/папки которые нужно исключить
EXCLUDE_PATTERNS = [
    'venv/**',
    '.venv/**',
    'env/**',
    '.env/**',
    '**/__pycache__/**',
    'tests/**',  # В тестах могут быть прямые моки
    'scripts/check_anti_spam_compliance.py',  # Этот файл
    '.git/**',
    'node_modules/**',
    '**/*.pyc',
    'build/**',
    'dist/**',
]

class AntiSpamChecker:
    """Проверяет соблюдение анти-спам требований"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations: List[Dict] = []
        
    def check_file(self, file_path: Path) -> List[Dict]:
        """Проверяет один файл на соблюдение анти-спам требований"""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            # Находим области внутри wrapper функций (которые допустимы)
            wrapper_areas = self._find_wrapper_function_areas(content, lines)
                
            # Проверяем на опасные паттерны
            for pattern in DANGEROUS_PATTERNS:
                matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                
                for match in matches:
                    # Находим номер строки
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1].strip()
                    
                    # Проверяем что это не исключение
                    is_allowed = False
                    
                    # 1. Проверяем стандартные исключения
                    for allowed_pattern in ALLOWED_PATTERNS:
                        if re.search(allowed_pattern, line_content, re.IGNORECASE):
                            is_allowed = True
                            break
                    
                    # 2. Проверяем что мы не внутри wrapper функции
                    if not is_allowed:
                        for start_line, end_line in wrapper_areas:
                            if start_line <= line_num <= end_line:
                                is_allowed = True
                                break
                    
                    # 3. Проверяем что строка содержит safe_call или _safe_api_call
                    if not is_allowed:
                        context_lines = lines[max(0, line_num-3):line_num+3]
                        context = ' '.join(context_lines)
                        if 'safe_call' in context or '_safe_api_call' in context:
                            is_allowed = True
                    
                    if not is_allowed:
                        violations.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': line_num,
                            'content': line_content,
                            'pattern': pattern,
                            'match': match.group(),
                            'severity': 'CRITICAL'
                        })
                        
        except Exception as e:
            print(f"⚠️ Ошибка при проверке {file_path}: {e}")
            
        return violations
    
    def _find_wrapper_function_areas(self, content: str, lines: List[str]) -> List[Tuple[int, int]]:
        """Находит области внутри wrapper функций где client.* вызовы допустимы"""
        wrapper_areas = []
        
        # Ищем паттерны wrapper функций
        wrapper_patterns = [
            r'async def \w+.*:\s*$',  # async def function():
            r'def \w+.*:\s*$',        # def function():
        ]
        
        for pattern in wrapper_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            
            for match in matches:
                start_line = content[:match.start()].count('\n') + 1
                
                # Ищем end функции (следующая функция или конец отступа)
                current_indent = self._get_line_indent(lines[start_line - 1])
                end_line = start_line
                
                for i in range(start_line, len(lines)):
                    line = lines[i]
                    if line.strip() == '':
                        continue
                    
                    line_indent = self._get_line_indent(line)
                    
                    # Если отступ меньше или равен начальному - конец функции
                    if line_indent <= current_indent and i > start_line:
                        end_line = i
                        break
                else:
                    end_line = len(lines)
                
                # Проверяем что внутри есть safe_call или это wrapper
                function_content = '\n'.join(lines[start_line-1:end_line])
                if ('safe_call' in function_content or 
                    '_safe_api_call' in function_content or
                    'wrapper' in function_content.lower() or
                    'async for' in function_content):
                    wrapper_areas.append((start_line, end_line))
        
        return wrapper_areas
    
    def _get_line_indent(self, line: str) -> int:
        """Получает уровень отступа строки"""
        return len(line) - len(line.lstrip())
    
    def should_check_file(self, file_path: Path) -> bool:
        """Определяет нужно ли проверять файл"""
        relative_path = str(file_path.relative_to(self.project_root))
        
        # Быстрая проверка на venv - приоритет
        if 'venv' in relative_path or '.venv' in relative_path:
            return False
            
        # Проверяем исключения
        for exclude_pattern in EXCLUDE_PATTERNS:
            # Используем fnmatch для правильной проверки glob паттернов
            import fnmatch
            if fnmatch.fnmatch(relative_path, exclude_pattern):
                return False
                
        # Проверяем включения  
        for include_pattern in INCLUDE_PATTERNS:
            import fnmatch
            if fnmatch.fnmatch(relative_path, include_pattern):
                return True
                
        return False
    
    def check_project(self) -> bool:
        """Проверяет весь проект"""
        print("🔍 Проверка соблюдения анти-спам требований...")
        print("=" * 60)
        
        all_violations = []
        
        # Проходим по всем Python файлам
        for py_file in self.project_root.rglob("*.py"):
            if self.should_check_file(py_file):
                violations = self.check_file(py_file)
                all_violations.extend(violations)
        
        # Выводим результаты
        if all_violations:
            print(f"🚨 НАЙДЕНО {len(all_violations)} НАРУШЕНИЙ АНТИ-СПАМ ТРЕБОВАНИЙ:")
            print()
            
            for violation in all_violations:
                print(f"📁 {violation['file']}:{violation['line']}")
                print(f"   ❌ {violation['content']}")
                print(f"   🔍 Паттерн: {violation['pattern']}")
                print()
            
            print("🔧 РЕКОМЕНДАЦИИ:")
            print("1. Замените прямые client.* вызовы на _safe_api_call() или safe_call()")
            print("2. Для новых API функций используйте шаблон:")
            print("   async def your_function():")
            print("       result = await _safe_api_call(self.client.your_method, args)")
            print("3. В тестах используйте моки, а не прямые вызовы")
            print()
            
            return False
        else:
            print("✅ Все файлы соответствуют анти-спам требованиям!")
            return True

def main():
    """Главная функция"""
    project_root = Path(__file__).parent.parent
    checker = AntiSpamChecker(project_root)
    
    if len(sys.argv) > 1:
        # Проверяем конкретные файлы (для pre-commit hook)
        files_to_check = sys.argv[1:]
        violations_found = False
        
        for file_path in files_to_check:
            file_path = Path(file_path)
            if file_path.exists() and checker.should_check_file(file_path):
                violations = checker.check_file(file_path)
                if violations:
                    violations_found = True
                    print(f"🚨 Нарушения в {file_path}:")
                    for violation in violations:
                        print(f"   Line {violation['line']}: {violation['content']}")
        
        sys.exit(1 if violations_found else 0)
    else:
        # Проверяем весь проект
        success = checker.check_project()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
