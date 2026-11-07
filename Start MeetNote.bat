@echo off
cd /d "%~dp0"
py -3.12 -m poetry run python -m meetnote
pause