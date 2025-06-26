from wxauto import WeChat
import time
import random
import keyboard
# 引入数据库模块
from database import save_message

# --- 全局控制变量 ---
running = True

def stop_script():
    """停止脚本的函数"""
    global running
    print("\n[!] 检测到停止指令，将在当前轮询结束后安全退出...")
    running = False

# 注册 'esc' 键为停止脚本的热键
keyboard.add_hotkey('esc', stop_script)

# --- 可配置参数 ---
# 要监听的群聊名称列表
GROUP_NAMES = [
    "NFC金融实习分享群（一）",
    "NJU后浪-优质实习交流群"
]
# 主循环的随机等待间隔（秒）
MIN_INTERVAL = 1
MAX_INTERVAL = 3
# 切换群聊后的随机等待间隔（秒）
MIN_SWITCH_DELAY = 0.5
MAX_SWITCH_DELAY = 1

# --- 核心功能 ---
def listen_groups():
    """
    附带随机延时和安全停止功能的微信群聊监听器
    """
    print("--- 微信群聊监听已启动 ---")
    print(f"[*] 监听群聊: {', '.join(GROUP_NAMES)}")
    print(f"[*] 按下 'Esc' 键可随时安全停止脚本。")
    print("--------------------------")

    wx = WeChat()
    last_msgs = {name: [] for name in GROUP_NAMES}
    
    # 使用全局变量 'running' 控制循环
    while running:
        for group in GROUP_NAMES:
            if not running:
                break
            try:
                wx.ChatWith(group)
                # 模拟人工切换后的短暂思考
                time.sleep(random.uniform(MIN_SWITCH_DELAY, MAX_SWITCH_DELAY))
                
                msgs = wx.GetAllMessage()
                
                # 首次运行时，将当前消息记为基准
                if not last_msgs[group]:
                    last_msgs[group] = msgs
                    print(f"[*] 已初始化群聊 [{group}] 的消息基准，将从此之后开始监听新消息。")
                    continue

                new_msgs = [msg for msg in msgs if msg not in last_msgs[group]]
                if new_msgs:
                    for msg in new_msgs:
                        # 增加过滤器：只处理真实用户的消息
                        if msg.sender not in ['system', 'base']:
                            # 将消息存入数据库
                            print(f"[*] 新消息存入数据库: [{group}] {msg.sender}") # 优化打印信息
                            save_message(
                                group_name=group,
                                sender=msg.sender,
                                content=msg.content,
                                msg_type=msg.type
                            )
                    last_msgs[group] = msgs # 更新最新的消息列表
                
            except Exception as e:
                print(f"[!] 监听群聊 [{group}] 时出错: {e}")
        
        if running:
            sleep_duration = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
            print(f"\n[*] 本轮监听完成，休眠 {sleep_duration:.2f} 秒... (按 'Esc' 停止)")
            time.sleep(sleep_duration)

    print("\n--- 微信群聊监听已安全停止 ---")

if __name__ == "__main__":
    listen_groups() 