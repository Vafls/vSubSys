@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

:: ==========================================
::  vLaunch Master Bootloader (Windows Port)
:: ==========================================

:: --- Color Configuration (ANSI Escape codes for Windows 10+) ---
for /F %%a in ('"prompt $E$S & echo on & for %%b in (1) do rem"') do set "ESC=%%a"
set "ESC=%ESC:~0,1%"
set "C_RST=%ESC%[0m"
set "C_BLU=%ESC%[1;34m"
set "C_GRN=%ESC%[1;32m"
set "C_RED=%ESC%[1;31m"
set "C_YLW=%ESC%[1;33m"
set "C_CYN=%ESC%[1;36m"
set "C_DIM=%ESC%[90m"

:: --- Path Definitions ---
set "BASE_DIR=%~dp0"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"

:: CRITICAL FIX: Explicitly set working directory to project root
cd /d "%BASE_DIR%"

set "KERNEL_PATH=%BASE_DIR%\kernel\kernel.py"
set "REQ_PATH=%BASE_DIR%\requirements.txt"

:: --- Default Flag Values ---
set GUI_MODE=1
set ASK_MODE=0
set NO_BOOT=0
set DO_CLEAN=0
set DO_SHELL=0

:: ==========================================
::  Argument Parsing (Order Independent)
:: ==========================================
:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="--nogui" ( set GUI_MODE=0 & shift & goto :parse_args )
if /I "%~1"=="--ask" ( set ASK_MODE=1 & shift & goto :parse_args )
if /I "%~1"=="--no-boot" ( set NO_BOOT=1 & shift & goto :parse_args )
if /I "%~1"=="--clean" ( set DO_CLEAN=1 & shift & goto :parse_args )
if /I "%~1"=="--shell" ( set DO_SHELL=1 & shift & goto :parse_args )
if /I "%~1"=="--help" goto :show_help
if /I "%~1"=="-h" goto :show_help

call :err "Unknown flag: %~1"
call :dim "Use --help for usage details."
exit /b 1

:show_help
echo %C_BLU%vLaunch Bootloader (Windows)%C_RST%
echo Usage: %~nx0 [FLAGS]
echo   --nogui    Run without exporting graphical plugins (No GUI)
echo   --ask      Prompt for confirmation (Enter) before booting the kernel
echo   --no-boot  Run structural checks, but do not start the kernel
echo   --shell    Open the built-in secure read-only shell environment
echo   --clean    Clear project cache files (__pycache__, .pyc)
echo   --help     Display this help menu
exit /b 0

:args_done

echo.
echo %C_BLU%▶ vLaunch Master Bootloader%C_RST%
echo.

:: ==========================================
::  Initialization & Dependency Validation
:: ==========================================
call :info "Verifying project environment..."

if not exist "%KERNEL_PATH%" (
    call :err "Kernel core not found! (%KERNEL_PATH%)"
    exit /b 1
)

:: Validate and sync dependencies globally/environmentally
if exist "%REQ_PATH%" (
    call :info "Synchronizing dependencies via requirements.txt..."
    python -m pip install -q -r "%REQ_PATH%"
    if errorlevel 1 (
        call :err "Dependency sync failed! Please verify pip installation status."
        exit /b 1
    )
    call :succ "Dependencies are up to date."
) else (
    call :warn "requirements.txt missing! Skipping environment dependency check."
)

call :succ "Project structure integrity verified."

:: Cache Cleanup
if "%DO_CLEAN%"=="1" (
    call :info "Cleaning Python cache targets..."
    for /d /r "%BASE_DIR%" %%d in (__pycache__) do (
        if exist "%%d" rd /s /q "%%d" 2>nul
    )
    del /s /q "%BASE_DIR%\*.pyc" 2>nul
    call :dim "__pycache__ structures purged successfully."
)

:: ==========================================
::  Shell Environment Entry
:: ==========================================
if "%DO_SHELL%"=="1" (
    call :vlaunch_shell
)

:: ==========================================
::  Environment Variable Exports
:: ==========================================
if "%GUI_MODE%"=="1" (
    :: Fixed safe execution for PyQt5 path lookup using double quotes and internal escaping
    set "QT_QPA_PLATFORM_PLUGIN_PATH="
    for /f "delims=" %%i in ('python -c "import os, PyQt5; print(os.path.abspath(os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins')))" 2^>nul') do set "QT_QPA_PLATFORM_PLUGIN_PATH=%%i"
    
    set "QT_QPA_PLATFORM=windows"
    
    call :info "Graphics engine: %C_GRN%ENABLED%C_RST% (Windows Native Execution)"
    if not "!QT_QPA_PLATFORM_PLUGIN_PATH!"=="" (
        call :dim "QT Plugins mapped to: !QT_QPA_PLATFORM_PLUGIN_PATH!"
    ) else (
        call :warn "Could not resolve explicit PyQt5 plugin path. Falling back to system default."
    )
) else (
    call :info "Graphics engine: %C_YLW%DISABLED%C_RST%"
)

:: ==========================================
::  Pre-Boot Confirmation Sequence
:: ==========================================
if "%ASK_MODE%"=="1" if "%NO_BOOT%"=="0" (
    echo.
    echo %C_YLW%Ready Status: Environment prepared for system boot.%C_RST%
    set /p "DUMMY=%ESC%[1;33mPress [ENTER] to execute kernel sequence (or Ctrl+C to abort)...%ESC%[0m"
)

:: ==========================================
::  Kernel Execution
:: ==========================================
if "%NO_BOOT%"=="1" (
    call :warn "--no-boot parameter matched. Kernel execution bypassed."
    call :succ "Bootloader execution cycle complete."
    exit /b 0
)

call :info "Transferring execution control to system core (kernel.py)..."
echo %C_DIM%--------------------------------------------------%C_RST%

:: Capture execution start time epoch
for /f %%a in ('powershell -NoProfile -Command "[int][double]::Parse((Get-Date (Get-Date).ToUniversalTime() -UFormat '%%s'))"') do set START_TIME=%%a

python "%KERNEL_PATH%" --gui=%GUI_MODE%
set EXIT_CODE=%ERRORLEVEL%

:: Capture execution end time epoch
for /f %%a in ('powershell -NoProfile -Command "[int][double]::Parse((Get-Date (Get-Date).ToUniversalTime() -UFormat '%%s'))"') do set END_TIME=%%a

echo %C_DIM%--------------------------------------------------%C_RST%

if "%EXIT_CODE%"=="0" (
    call :succ "System core terminated normally."
) else (
    call :err "Kernel execution panic or unclean exit reported (Code: %EXIT_CODE%)."
)

set /A EXEC_TIME=END_TIME - START_TIME
call :dim "Total running uptime: %EXEC_TIME% seconds."
echo.
exit /b %EXIT_CODE%

:: ==========================================
::  LOGGING RUNTIME FUNCTIONS
:: ==========================================

:info
echo %C_BLU%::%C_RST% %~1
exit /b 0

:succ
echo %C_GRN%::%C_RST% %~1
exit /b 0

:warn
echo %C_YLW%::%C_RST% %~1
exit /b 0

:err
echo %C_RED%::%C_RST% %~1
exit /b 0

:dim
echo    %C_DIM%└─ %~1%C_RST%
exit /b 0

:: ==========================================
::  Secure Read-Only Shell Console
:: ==========================================
:vlaunch_shell
call :info "Entering secure vLaunch Shell environment (Read-Only Mode)."
call :dim "Allowed commands: ls, cd, cat, pwd, clear, exit"

set "CURRENT_DIR=%BASE_DIR%"
cd /d "%CURRENT_DIR%"

:shell_loop
setlocal EnableDelayedExpansion

set "REL_PATH=!CURRENT_DIR:%BASE_DIR%=!"
if "!REL_PATH!"=="" set "REL_PATH=\"
set "REL_PATH=!REL_PATH:\=/!"

echo.
set "CMD="
set "ARGS="
set /p "INPUT=%C_CYN%vLaunch%C_DIM%[!REL_PATH!]%C_RST% > "

if "!INPUT!"=="" (
    endlocal
    goto :shell_loop
)

for /F "tokens=1*" %%A in ("!INPUT!") do (
    set "CMD=%%A"
    set "ARGS=%%B"
)

if /I "!CMD!"=="exit" goto :shell_exit
if /I "!CMD!"=="quit" goto :shell_exit
if /I "!CMD!"=="clear" ( cls & endlocal & goto :shell_loop )
if /I "!CMD!"=="pwd" ( echo %C_DIM%!CURRENT_DIR!%C_RST% & endlocal & goto :shell_loop )
if /I "!CMD!"=="ls" ( dir /w "!CURRENT_DIR!" & endlocal & goto :shell_loop )

if /I "!CMD!"=="cd" (
    if "!ARGS!"=="" (
        set "TARGET_DIR=%BASE_DIR%"
    ) else (
        pushd "!CURRENT_DIR!" 2>nul
        cd /d "!ARGS!" 2>nul
        set "TARGET_DIR=!CD!"
        popd 2>nul
    )
    
    echo !TARGET_DIR! | findstr /B /I /C:"%BASE_DIR%" >nul
    if not errorlevel 1 (
        if exist "!TARGET_DIR!\" (
            endlocal
            set "CURRENT_DIR=%TARGET_DIR%"
            cd /d "%TARGET_DIR%"
            goto :shell_loop
        ) else (
            call :err "Access denied: Destination out of bounds or path non-existent."
        )
    ) else (
        call :err "Access denied: Destination out of bounds or path non-existent."
    )
    endlocal
    goto :shell_loop
)

if /I "!CMD!"=="cat" (
    if "!ARGS!"=="" (
        call :warn "Argument required: cat <file_name>"
    ) else (
        for %%F in ("!CURRENT_DIR!\!ARGS!") do set "TARGET_FILE=%%~dpnxF"
        
        echo !TARGET_FILE! | findstr /B /I /C:"%BASE_DIR%" >nul
        if not errorlevel 1 (
            if exist "!TARGET_FILE!" (
                echo %C_DIM%--- File Buffer Begin: !ARGS! ---%C_RST%
                type "!TARGET_FILE!"
                echo.
                echo %C_DIM%--- File Buffer End ---%C_RST%
            ) else (
                call :err "File not found or system permissions missing."
            )
        ) else (
            call :err "File not found or system permissions missing."
        )
    )
    endlocal
    goto :shell_loop
)

call :err "Command unrecognized. Valid options: ls, cd, cat, pwd, clear, exit"
endlocal
goto :shell_loop

:shell_exit
endlocal
call :info "Exiting shell framework."
goto :eof