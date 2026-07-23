@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo [Streamlit Dashboard Starting...]
echo Opening: http://localhost:8501
streamlit run dashboard.py
pause
