@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH="
set "OMP_NUM_THREADS=1"
set "OPENBLAS_NUM_THREADS=1"
set "DEMO_PY=.venv\Scripts\python.exe"
if not exist "%DEMO_PY%" (
    echo Preparing MedRoute X. Python 3.10 or newer is required.
    python -m venv .venv
    if errorlevel 1 goto failed
)
"%DEMO_PY%" -c "import scipy.optimize" >nul 2>&1
if errorlevel 1 (
    echo Installing demo dependencies. Internet access is needed on first setup.
    "%DEMO_PY%" -m pip install "scipy>=1.10,<2"
    if errorlevel 1 goto failed
)
"%DEMO_PY%" scripts\launch_demo.py
if errorlevel 1 goto failed
exit /b 0

:failed
echo MedRoute X could not start. See the message above.
pause
exit /b 1
