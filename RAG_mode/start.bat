@echo off
cd /d "%~dp0mode"
echo 启动目录: %CD%
echo.
streamlit run app.py
pause
