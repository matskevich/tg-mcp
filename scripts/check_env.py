#!/usr/bin/env python3
"""
Скрипт проверки .env файла на полноту
====================================

Проверяет что все ключи из env.sample присутствуют в .env
и показывает какие ключи имеют значения по умолчанию
"""

import os
import sys


def check_env():
    """Проверить .env файл на полноту"""
    
    env_sample = {}
    env_current = {}
    
    # Читаем .env.sample
    try:
        with open('.env.sample', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key = line.split('=')[0].strip()
                    env_sample[key] = line
    except FileNotFoundError:
        print('❌ .env.sample not found!')
        sys.exit(1)
    
    # Читаем текущий .env
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key = line.split('=')[0].strip()
                    value = line.split('=', 1)[1].strip() if '=' in line else ''
                    env_current[key] = value
    except FileNotFoundError:
        print('❌ .env not found!')
        sys.exit(1)
    
    # Проверяем полноту
    missing_keys = []
    empty_keys = []
    default_values = ['', 'your_api_id_here', 'your_api_hash_here', '+1234567890']
    secret_provider = env_current.get('TG_SECRET_PROVIDER', 'env').strip().lower()
    use_keychain = secret_provider == 'keychain' or env_current.get('TG_USE_KEYCHAIN', '0') == '1'
    use_command = secret_provider == 'command'

    optional_by_provider = set()
    if not use_keychain:
        optional_by_provider.update({
            'TG_KEYCHAIN_SERVICE',
            'TG_KEYCHAIN_ACCOUNT_API_ID',
            'TG_KEYCHAIN_ACCOUNT_API_HASH',
        })
    if not use_command:
        optional_by_provider.update({
            'TG_SECRET_CMD_API_ID',
            'TG_SECRET_CMD_API_HASH',
        })
    
    for key in env_sample:
        if key not in env_current:
            missing_keys.append(key)
        elif key in optional_by_provider:
            continue
        elif key in ('TG_API_ID', 'TG_API_HASH') and (use_keychain or use_command):
            continue
        elif env_current[key] in default_values:
            empty_keys.append(key)
    
    # Отчет
    if missing_keys:
        print(f'❌ Missing keys ({len(missing_keys)}):')
        for key in missing_keys:
            print(f'  - {key}')
        print('💡 Run "make sync-env" to add them')
    else:
        print('✅ All keys present')
    
    if empty_keys:
        print(f'⚠️  Keys with default/empty values ({len(empty_keys)}):')
        for key in empty_keys:
            print(f'  - {key} = {env_current[key]}')
        print('💡 Update these with your actual values')
    else:
        print('✅ All keys have values')
    
    # Возвращаем код ошибки если есть проблемы
    if missing_keys or empty_keys:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    check_env() 
