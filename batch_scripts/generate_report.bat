@echo off
REM 设置脚本标题
TITLE JD Report Generator

REM 激活Python虚拟环境
CALL .\\venv\\Scripts\\activate.bat

echo.
echo =======================================================
echo.
echo      Generating JD Report from Database...
echo.
echo =======================================================


REM 运行报告生成脚本
python .\\src\\report_generator.py

echo.
echo =======================================================
echo.
echo      Report generation process finished.
echo.
echo =======================================================

REM 保持窗口打开，直到用户按键
pause 