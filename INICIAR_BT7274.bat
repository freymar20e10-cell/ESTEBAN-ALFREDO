@echo off
title BT-7274
color 0B
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 server.py
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        python server.py
    ) else (
        echo.
        echo No se encontro Python 3. Instala Python y marca la opcion "Add Python to PATH".
        echo Luego ejecuta: py -3 -m pip install -r requirements.txt
    )
)
pause
