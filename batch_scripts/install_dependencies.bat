@echo off
chcp 65001 > nul
TITLE Install Dependencies

echo =======================================================
echo.
echo      正在安装项目依赖...
echo.
echo =======================================================

REM 激活虚拟环境
call .\venv\Scripts\activate

REM 升级pip
python -m pip install --upgrade pip

REM 安装依赖
pip install -r requirements.txt

echo.
echo =======================================================
echo.
echo      依赖安装完成！
echo.
echo =======================================================

pause 