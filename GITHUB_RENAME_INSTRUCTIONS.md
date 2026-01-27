# GitHub Repository Rename Instructions

## Переименование репозитория s16-leads → tganalytics

### 1. Переименовать репозиторий на GitHub

1. Открой https://github.com/YOUR_USERNAME/s16-leads/settings
2. В разделе "Repository name" измени `s16-leads` → `tganalytics`
3. Нажми "Rename"

GitHub автоматически создаст редирект с старого URL на новый.

### 2. Обновить локальный remote

```bash
# Проверить текущий remote
git remote -v

# Обновить URL (GitHub автоматически перенаправит, но лучше обновить)
git remote set-url origin git@github.com:YOUR_USERNAME/tganalytics.git

# Или для HTTPS:
git remote set-url origin https://github.com/YOUR_USERNAME/tganalytics.git

# Проверить
git remote -v
```

### 3. Обновить клоны на других машинах

На всех машинах где есть клон репозитория:

```bash
cd /path/to/s16-leads
git remote set-url origin git@github.com:YOUR_USERNAME/tganalytics.git
```

### 4. Переименовать локальную папку (опционально)

```bash
cd /path/to/parent/directory
mv s16-leads tganalytics
cd tganalytics
```

### 5. Обновить CI/CD и badges (если есть)

- GitHub Actions workflows (проверь `.github/workflows/`)
- README badges
- Documentation links

### 6. Уведомить команду

Если кто-то еще работает с репо:
- Отправь им новый URL
- Попроси обновить remotes

## Проверка

```bash
# Проверить что все работает
git fetch origin
git pull origin main

# Проверить импорты
PYTHONPATH=tganalytics:. python3 -c "from tganalytics.infra.limiter import get_rate_limiter; print('✅ OK')"

# Запустить тесты
PYTHONPATH=tganalytics:. python3 -m pytest tests/ -v
```

## Что изменилось в коде

- `packages/tg_core/` → `tganalytics/`
- `examples/` → `tganalytics/examples/`
- Все импорты: `from tg_core.*` → `from tganalytics.*`
- pyproject.toml: package name → `tganalytics`

## PYTHONPATH

Теперь для запуска нужно указывать `PYTHONPATH=tganalytics:.`

Можно добавить в `.envrc` (если используешь direnv):

```bash
export PYTHONPATH=tganalytics:$PYTHONPATH
```

Или создать alias в `~/.bashrc` / `~/.zshrc`:

```bash
alias tga='PYTHONPATH=tganalytics:. python3'
```

Использование:

```bash
tga -m pytest tests/
tga gconf/src/cli.py participants <group_id>
```
