@echo off
chcp 65001 > nul
TITLE Test JD Extractor

echo =======================================================
echo.
echo      正在独立测试JD提取逻辑...
echo.
echo =======================================================

call .\\venv\\Scripts\\activate
python .\\src\\test_extractor.py

echo.
echo =======================================================
echo.
echo      测试完成。按任意键退出。
echo.
echo =======================================================

pause >nul 