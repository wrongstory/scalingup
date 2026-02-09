@echo off
chcp 65001 >nul

echo ================================================================
echo AI Upscaler - Installation Test
echo ================================================================
echo.

call venv\Scripts\activate.bat

echo Testing all modules...
echo.

python -c "import sys; print(f'Python: {sys.version}')"
echo.

python -c "import PySide6; print(f'PySide6: {PySide6.__version__}')"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import torchvision; print(f'torchvision: {torchvision.__version__}')"
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "import PIL; print(f'Pillow: {PIL.__version__}')"
python -c "import basicsr; print('basicsr: OK')"
python -c "import realesrgan; print('realesrgan: OK')"

echo.
echo Final test - importing RealESRGANer...
python -c "from realesrgan import RealESRGANer; from basicsr.archs.rrdbnet_arch import RRDBNet; print('SUCCESS! All modules working!')"

if errorlevel 1 (
    echo.
    echo [FAILED] Some modules are not working
    pause
    exit /b 1
)

echo.
echo ================================================================
echo All Tests Passed!
echo ================================================================
echo.
echo Your installation is 100%% working!
echo Run: run.bat
echo.
pause
