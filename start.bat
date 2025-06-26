@echo off
chcp 65001 > nul
REM 设置窗口标题
TITLE WeChat Listener

echo =======================================================
echo.
echo      正在启动微信群聊监听器...
echo.
echo      请确保微信PC版已经登录并正在运行。
echo.
echo      脚本启动后，您可以最小化此窗口。
echo      当需要停止时，请点击此窗口然后按下 [Esc] 键。
echo.
echo =======================================================

REM 激活虚拟环境
call .\\venv\\Scripts\\activate

REM 运行Python主程序
python .\\src\\wechat_listener.py

echo.
echo =======================================================
echo.
echo      监听脚本已安全停止。
echo.
echo =======================================================

REM 暂停窗口，以便用户可以看到最终信息
pause 