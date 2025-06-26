@echo off
chcp 65001 > nul
TITLE Process JDs

echo =======================================================
echo.
echo      正在扫描新消息并提取JD信息...
echo.
echo =======================================================

call .\\venv\\Scripts\\activate
python .\\src\\jd_extractor.py

echo.
echo =======================================================
echo.
echo      处理完成。按任意键退出。
echo.
echo =======================================================

pause >nul 