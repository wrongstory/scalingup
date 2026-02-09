@echo off
chcp 65001 >nul

echo ================================================================
echo AI Upscaler - Build EXE
echo ================================================================
echo.

call venv\Scripts\activate.bat

echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building executable...
echo This may take several minutes...
echo.

pyinstaller --clean ^
    --name="AI-Upscaler" ^
    --windowed ^
    --onefile ^
    --add-data="models;models" ^
    --hidden-import=PySide6.QtCore ^
    --hidden-import=basicsr ^
    --hidden-import=realesrgan ^
    app/main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ================================================================
echo Build Complete!
echo ================================================================
echo.
echo Executable: dist\AI-Upscaler.exe
echo.
echo Note:
echo   - FFmpeg must be installed separately
echo   - AI models will download on first run
echo.
pause
