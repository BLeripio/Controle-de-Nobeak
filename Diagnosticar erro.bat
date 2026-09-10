@echo off
cd /d "%~dp0"
python interface.py

echo.
echo ============================================
echo Se apareceu uma mensagem de erro (em vermelho ou texto)
echo acima desta linha, tire um print e envie para o Claude.
echo ============================================
pause
