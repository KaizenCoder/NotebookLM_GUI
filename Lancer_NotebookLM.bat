@echo off
REM Ce script trouve l'emplacement actuel de ce dossier automatiquement.
cd /d "%~dp0"
REM Lance Python sans ouvrir de fenêtre noire Terminal grâce a pythonw.exe
start "" ".\.venv\Scripts\pythonw.exe" "app.py"
