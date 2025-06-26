@echo off
chcp 65001 > nul
TITLE WeChat Listener Workflow

echo.
echo =======================================================
echo          STEP 1: 启动微信群聊监听器
echo =======================================================
echo.
echo - 请确保微信PC版已经登录并正在运行。
echo - 监听过程中，您可以最小化此窗口。
echo - 当需要停止时，请点击此窗口然后按下 [Esc] 键。
echo.

REM 运行监听脚本，它会在这里暂停，直到用户按 ESC 停止
call .\\start.bat

echo.
echo =======================================================
echo          STEP 2: 执行数据库消息去重
echo =======================================================
echo.
echo - 正在清理数据库中的重复消息...
echo.

REM 激活虚拟环境
call .\\venv\\Scripts\\activate

REM 运行去重脚本
python .\\src\\deduplicate_messages.py

echo.
echo =======================================================
echo.
echo          工作流执行完毕！
echo.
echo =======================================================

pause 