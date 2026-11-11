@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Busca Python. En el PC original el "python" de WindowsApps es un acceso roto,
rem por eso primero se prueba la instalación real.
set "PY=C:\Users\PC\AppData\Local\Python\bin\python.exe"
if not exist "%PY%" set "PY=py"
"%PY%" -u bot.py
pause
