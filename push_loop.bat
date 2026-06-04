@echo off
chcp 65001 >nul
echo ========================================
echo Git 循环 Push 脚本
echo ========================================
powershell -ExecutionPolicy Bypass -File "%~dp0push_loop.ps1" %*
pause
