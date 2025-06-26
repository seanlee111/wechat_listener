@echo off
chcp 65001 > nul
TITLE View WeChat Database

echo =======================================================
echo.
echo      正在读取数据库内容...
echo.
echo =======================================================

call .\\venv\\Scripts\\activate
python .\\src\\view_db.py

echo.
echo =======================================================
echo.
echo      查询完成。按任意键退出。
echo.
echo =======================================================

pause >nul 