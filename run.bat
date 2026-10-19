@echo off
rem Tetris launcher (uses whatever `python` is on PATH; needs tkinter)
cd /d "%~dp0"
python tetris.py
if errorlevel 1 (
    echo.
    echo Failed to start. Make sure Python 3.x with tkinter is installed.
    pause
)
