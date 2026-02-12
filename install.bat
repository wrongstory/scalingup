@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================================================
echo AI Upscaler - 100%% Verified Installation (Python 3.10 Required)
echo ================================================================
echo.

REM ===== Critical: Python 3.10 Check =====
echo [Step 1/7] Checking Python 3.10...

set PYTHON_CMD=
set PYTHON_VERSION=

REM Try Python 3.10 specifically
py -3.10 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.10
    for /f "tokens=2" %%v in ('py -3.10 --version 2^>^&1') do set PYTHON_VERSION=%%v
    echo Found Python 3.10 ^(!PYTHON_VERSION!^) - Perfect!
    goto :python_found
)

REM Check default Python
python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
    
    REM Check if it's 3.10.x
    echo !PYTHON_VERSION! | findstr /C:"3.10." >nul
    if not errorlevel 1 (
        set PYTHON_CMD=python
        echo Found Python 3.10 ^(!PYTHON_VERSION!^) - Perfect!
        goto :python_found
    )
    
    echo.
    echo [ERROR] Found Python !PYTHON_VERSION! but need Python 3.10
)

REM Python 3.10 not found
echo.
echo [ERROR] Python 3.10 is required for 100%% compatibility!
echo.
echo Current Python: !PYTHON_VERSION!
echo Required: Python 3.10.x
echo.
echo Download Python 3.10.11:
echo   https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
echo.
echo During installation:
echo   [x] Add Python 3.10 to PATH  ^<-- IMPORTANT!
echo.
echo After installation, run this script again.
echo.
pause
exit /b 1

:python_found
echo Using: !PYTHON_CMD! ^(!PYTHON_VERSION!^)
echo.

REM ===== Visual C++ Check =====
echo [Step 2/7] Checking Visual C++ Redistributable...

reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Version >nul 2>&1
if not errorlevel 1 (
    echo Visual C++ found - OK
) else (
    echo.
    echo [WARNING] Visual C++ Redistributable not detected
    echo.
    echo Download and install:
    echo   https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    echo This is required for PyTorch to work.
    echo.
    choice /C YN /M "Continue without it? (Not recommended)"
    if errorlevel 2 exit /b 1
)
echo.

REM ===== Clean Installation =====
echo [Step 3/7] Cleaning previous installation...

if exist "venv\" (
    echo Removing old virtual environment...
    rmdir /s /q venv 2>nul
    timeout /t 1 >nul
)

if exist "ai_upscaler.log" del ai_upscaler.log

echo Clean!
echo.

REM ===== Create Virtual Environment =====
echo [Step 4/7] Creating virtual environment with Python 3.10...

!PYTHON_CMD! -m venv venv

if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    echo.
    echo Try manually:
    echo   !PYTHON_CMD! -m venv venv
    echo.
    pause
    exit /b 1
)

echo Virtual environment created!
echo.

REM ===== Install Packages =====
echo [Step 5/7] Installing verified packages...
echo This will take 5-10 minutes...
echo.

call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip setuptools wheel --quiet

echo Detecting GPU...
nvidia-smi >nul 2>&1
if not errorlevel 1 (
    echo.
    echo NVIDIA GPU detected!
    nvidia-smi --query-gpu=name --format=csv,noheader
    echo Installing GPU version...
    echo.
    pip install torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118 --quiet
    pip install -r requirements_gpu.txt --quiet
) else (
    echo No NVIDIA GPU detected. Installing CPU version...
    echo.
    pip install -r requirements.txt -- quiet
)

if errorlevel 1 (
    echo.
    echo [ERROR] Package installation failed
    echo.
    echo Please check:
    echo   1. Internet connection
    echo   2. Visual C++ is installed
    echo   3. Python version is exactly 3.10.x
    echo.
    pause
    exit /b 1
)

echo.
echo All packages installed!
echo.

REM ===== Verify Installation =====
echo [Step 6/7] Verifying installation...
echo.

echo Checking Python...
python --version
if errorlevel 1 goto :verify_failed

echo.
echo Checking PySide6...
python -c "import PySide6; print(f'  PySide6 {PySide6.__version__}: OK')" 2>nul
if errorlevel 1 goto :verify_failed

echo Checking PyTorch...
python -c "import torch; print(f'  PyTorch {torch.__version__}: OK')" 2>nul
if errorlevel 1 (
    echo   [ERROR] PyTorch import failed
    echo.
    echo Missing Visual C++ Redistributable:
    echo   https://aka.ms/vs/17/release/vc_redist.x64.exe
    goto :verify_failed
)

echo Checking torchvision...
python -c "import torchvision; print(f'  torchvision {torchvision.__version__}: OK')" 2>nul
if errorlevel 1 goto :verify_failed

echo Checking OpenCV...
python -c "import cv2; print('  OpenCV: OK')" 2>nul
if errorlevel 1 goto :verify_failed

echo Checking basicsr...
python -c "import basicsr; print('  basicsr: OK')" 2>nul
if errorlevel 1 goto :verify_failed

echo Checking Real-ESRGAN...
python -c "from realesrgan import RealESRGANer; print('  Real-ESRGAN: OK')" 2>nul
if errorlevel 1 goto :verify_failed

echo.
echo [Step 7/7] Final verification...
python -c "from realesrgan import RealESRGANer; from basicsr.archs.rrdbnet_arch import RRDBNet; print('All modules verified!')"
if errorlevel 1 goto :verify_failed

echo.
echo ================================================================
echo Installation Complete! 100%% Verified
echo ================================================================
echo.
echo Python: !PYTHON_VERSION!
echo Location: %CD%\venv
echo.
echo To run:
echo   run.bat
echo.
echo Or manually:
echo   venv\Scripts\activate
echo   python -m app.main
echo.
echo Optional - FFmpeg for video processing:
echo   Check: ffmpeg -version
echo   Install: https://ffmpeg.org
echo.
pause
exit /b 0

:verify_failed
echo.
echo ================================================================
echo [ERROR] Verification Failed
echo ================================================================
echo.
echo Troubleshooting:
echo.
echo 1. Install Visual C++ Redistributable:
echo    https://aka.ms/vs/17/release/vc_redist.x64.exe
echo.
echo 2. Restart computer
echo.
echo 3. Verify Python 3.10 is installed:
echo    py -3.10 --version
echo.
echo 4. Run this script again
echo.
pause
exit /b 1
