@echo off
start "" python -m http.server 8000
timeout /t 2
start http://localhost:8000