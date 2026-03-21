#!/bin/bash

# ==========================================
#  vLaunch Master Bootloader
# ==========================================

# --- Настройка цветов ---
C_RST='\033[0m'
C_BLU='\033[1;34m'
C_GRN='\033[1;32m'
C_RED='\033[1;31m'
C_YLW='\033[1;33m'
C_CYN='\033[1;36m'
C_DIM='\033[2;37m'

# --- Функции логирования ---
info() { echo -e "${C_BLU}::${C_RST} $1"; }
succ() { echo -e "${C_GRN}::${C_RST} $1"; }
warn() { echo -e "${C_YLW}::${C_RST} $1"; }
err()  { echo -e "${C_RED}::${C_RST} $1"; }
dim()  { echo -e "   ${C_DIM}└─ $1${C_RST}"; }

# --- Перехват прерывания (Ctrl+C) ---
trap 'echo -e "\n"; err "Аварийное прерывание (SIGINT). Выход."; exit 130' SIGINT

# --- Определение путей ---
BASE_DIR=$(dirname "$(readlink -f "$0")")
VENV_PATH="$BASE_DIR/.venv"
KERNEL_PATH="$BASE_DIR/kernel/kernel.py"

# ==========================================
#  Безопасная Read-Only Консоль
# ==========================================
vlaunch_shell() {
    info "Вход в безопасную консоль vLaunch (только чтение)."
    dim "Доступные команды: ls, cd, cat, pwd, clear, exit"
    
    local current_dir="$BASE_DIR"
    
    while true; do
        # Вычисляем относительный путь для красивого промпта
        local rel_path="${current_dir#$BASE_DIR}"
        [[ -z "$rel_path" ]] && rel_path="/"
        
        # Читаем ввод
        read -e -p "$(echo -e "\n${C_CYN}vLaunch${C_DIM}[$rel_path]${C_RST} > ")" cmd args
        
        [[ -z "$cmd" ]] && continue
        
        case "$cmd" in
            exit|quit) 
                info "Выход из консоли."
                break 
                ;;
            clear) 
                clear 
                ;;
            pwd) 
                echo -e "${C_DIM}$current_dir${C_RST}" 
                ;;
            ls) 
                ls -lh --color=auto "$current_dir" 
                ;;
            cd)
                if [[ -z "$args" ]]; then
                    current_dir="$BASE_DIR"
                    continue
                fi
                # realpath -m вычисляет путь, убирая /../
                local target=$(realpath -m "$current_dir/$args")
                # Проверка: находится ли целевая папка внутри BASE_DIR?
                if [[ "$target" == "$BASE_DIR"* && -d "$target" ]]; then
                    current_dir="$target"
                else
                    err "Доступ запрещен: Выход за пределы vLaunch или папка не существует."
                fi
                ;;
            cat)
                if [[ -z "$args" ]]; then
                    warn "Укажите файл: cat <имя_файла>"
                    continue
                fi
                local target=$(realpath -m "$current_dir/$args")
                if [[ "$target" == "$BASE_DIR"* && -f "$target" ]]; then
                    echo -e "${C_DIM}--- Начало файла: $args ---${C_RST}"
                    cat "$target"
                    echo -e "${C_DIM}--- Конец файла ---${C_RST}"
                else
                    err "Файл не найден или доступ к нему запрещен."
                fi
                ;;
            *) 
                err "Неизвестная команда. Разрешены: ls, cd, cat, pwd, clear, exit" 
                ;;
        esac
    done
}

# ==========================================
#  Парсинг флагов (Независимо от порядка)
# ==========================================
GUI_MODE=1
ASK_MODE=0
NO_BOOT=0
DO_CLEAN=0
DO_SHELL=0

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --nogui) GUI_MODE=0 ;;
        --ask) ASK_MODE=1 ;;
        --no-boot) NO_BOOT=1 ;;
        --clean) DO_CLEAN=1 ;;
        --shell) DO_SHELL=1 ;;
        --help|-h)
            echo -e "${C_BLU}vLaunch Bootloader${C_RST}"
            echo -e "Использование: $0 [ФЛАГИ]"
            echo -e "  --nogui    Запуск без экспорта графических плагинов (без GUI)"
            echo -e "  --ask      Запросить подтверждение (Enter) перед запуском ядра"
            echo -e "  --no-boot  Выполнить проверки, но не запускать ядро"
            echo -e "  --shell    Открыть встроенную безопасную консоль для чтения файлов"
            echo -e "  --clean    Очистить проект от файлов кэша (__pycache__, .pyc)"
            echo -e "  --help     Показать эту справку"
            exit 0
            ;;
        *) err "Неизвестный флаг: $1"; dim "Используйте --help для справки."; exit 1 ;;
    esac
    shift # Сдвигаем аргументы влево
done

echo -e "\n${C_BLU}▶ vLaunch Master Bootloader${C_RST}\n"

# ==========================================
#  Инициализация и проверки
# ==========================================
info "Проверка структуры проекта..."
if [ ! -d "$VENV_PATH" ]; then
    err "Окружение .venv не найдено! ($VENV_PATH)"
    exit 1
fi
if [ ! -f "$KERNEL_PATH" ]; then
    err "Ядро не найдено! ($KERNEL_PATH)"
    exit 1
fi
succ "Структура целостна."

# Очистка кэша
if [ "$DO_CLEAN" -eq 1 ]; then
    info "Очистка кэша Python..."
    find "$BASE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find "$BASE_DIR" -type f -name "*.pyc" -delete 2>/dev/null
    dim "Папки __pycache__ удалены."
fi

# ==========================================
#  Вход в Shell (если запрошен)
# ==========================================
if [ "$DO_SHELL" -eq 1 ]; then
    vlaunch_shell
fi

# ==========================================
#  Настройка окружения
# ==========================================
if [ "$GUI_MODE" -eq 1 ]; then
    export QT_QPA_PLATFORM_PLUGIN_PATH="$VENV_PATH/lib/python3.14/site-packages/PyQt5/Qt5/plugins"
    export QT_QPA_PLATFORM=xcb
    info "Графический режим: ${C_GRN}ВКЛЮЧЕН${C_RST} (Wayland/XCB Ready)"
else
    info "Графический режим: ${C_YLW}ОТКЛЮЧЕН${C_RST}"
fi

info "Активация .venv..."
source "$VENV_PATH/bin/activate"

# ==========================================
#  Предзагрузочная пауза
# ==========================================
if [ "$ASK_MODE" -eq 1 ] && [ "$NO_BOOT" -eq 0 ]; then
    echo -e "\n${C_YLW}Внимание: Система готова к загрузке.${C_RST}"
    read -p "Нажми [ENTER] для старта ядра (или Ctrl+C для отмены)..."
fi

# ==========================================
#  Запуск Ядра
# ==========================================
if [ "$NO_BOOT" -eq 1 ]; then
    warn "Флаг --no-boot активен. Запуск ядра отменен."
    succ "Работа загрузчика завершена."
    exit 0
fi

info "Передача управления ядру (kernel.py)..."
echo -e "${C_DIM}--------------------------------------------------${C_RST}"

START_TIME=$(date +%s)
python "$KERNEL_PATH" --gui=$GUI_MODE
EXIT_CODE=$?
END_TIME=$(date +%s)

echo -e "${C_DIM}--------------------------------------------------${C_RST}"

if [ $EXIT_CODE -eq 0 ]; then
    succ "Система штатно завершила работу."
else
    err "Ядро упало или завершилось с ошибкой (Код: $EXIT_CODE)."
fi

EXEC_TIME=$((END_TIME - START_TIME))
dim "Время работы: ${EXEC_TIME} сек."
echo ""