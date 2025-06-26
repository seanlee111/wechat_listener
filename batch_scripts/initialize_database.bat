@echo off
chcp 65001 > nul
TITLE Initialize Database

echo =======================================================
echo.
echo      正在初始化或更新数据库...
echo      此操作将确保数据库表结构为最新状态。
echo.
echo =======================================================

call .\\venv\\Scripts\\activate
python .\\src\\initialize_database.py

echo.
echo =======================================================
echo.
echo      操作完成。按任意键退出。
echo.
echo =======================================================

pause >nul 