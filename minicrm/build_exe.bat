@echo off
REM Compile MiniCRM.exe (Windows) avec PyInstaller.
REM Necessite : Python 3 installe (python dans le PATH).
pip install -r requirements.txt
pyinstaller --onefile --windowed --name MiniCRM crm.py
echo.
echo L'executable est disponible dans dist\MiniCRM.exe
pause
