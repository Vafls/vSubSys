#!/bin/bash

# 1. Определяем директорию, где лежит этот скрипт (корень vLaunch)
BASE_DIR=$(dirname "$(readlink -f "$0")")

# 2. Указываем путь к твоему .venv (теперь правильно)
VENV_PATH="$BASE_DIR/.venv"

# Проверка: существует ли вообще этот venv?
if [ ! -d "$VENV_PATH" ]; then
    echo "Ошибка: Виртуальное окружение не найдено по пути $VENV_PATH"
    exit 1
fi

# 3. Настройка переменных для PyQt5 (чтобы не было SIGABRT)
export QT_QPA_PLATFORM_PLUGIN_PATH="$VENV_PATH/lib/python3.14/site-packages/PyQt5/Qt5/plugins"
export QT_QPA_PLATFORM=xcb

# 4. Активация окружения и запуск скрипта
source "$VENV_PATH/bin/activate"
python "$BASE_DIR/boot/violence_boot.py"