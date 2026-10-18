@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
 echo Installation fehlgeschlagen. Bitte Python und Internetverbindung pruefen.
 pause
 exit /b 1
)
py -3 app.py
if errorlevel 1 pause