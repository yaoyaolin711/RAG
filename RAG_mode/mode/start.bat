@echo off
cd /d "%~dp0"
echo 启动目录: %CD%
echo.
streamlit run app.py
pause
