@echo off
cd /d "%~dp0crm_agent\crm_agent"
set API_PORT=8002
echo ========================================
echo   RAG Agent — FastAPI
echo   文档    http://localhost:8002/docs
echo ========================================
echo.
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python main.py
pause
