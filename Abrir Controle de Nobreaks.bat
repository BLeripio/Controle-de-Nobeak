@echo off
REM Este arquivo abre o Controle de Nobreaks sem precisar do terminal.
REM Basta dar dois cliques nele.

cd /d "%~dp0"
start "" pythonw interface.py
