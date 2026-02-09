@echo off
chcp 65001 >nul

echo ================================================================
echo AI Upscaler - Starting
echo ================================================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    echo.
    echo Please run: install.bat
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Python version:
python --version

echo.
echo Starting AI Upscaler...
echo.

python -m app.main

if errorlevel 1 (
    echo.
    echo [ERROR] Application crashed
    echo Check ai_upscaler.log for details
    echo.
    pause
)
