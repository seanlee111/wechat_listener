"""
微信监听器 v2.0
兼容安全去重架构，支持新的分层存储
"""

from wxauto import WeChat
import time
import random
import keyboard
import logging
from pathlib import Path

# 引入新的数据库模块
from database_v2 import DatabaseV2, save_message  # 保持向后兼容
from backup_manager import BackupManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 全局控制变量 ---
running = True

def stop_script():
    """停止脚本的函数"""
    global running
    print("\n[!] 检测到停止指令，将在当前轮询结束后安全退出...")
    logger.info("收到停止指令，准备安全退出")
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

class WeChatListenerV2:
    """
    微信监听器 v2.0
    支持新的安全数据库架构
    """
    
    def __init__(self, enable_auto_backup: bool = True):
        """初始化监听器"""
        self.db_v2 = DatabaseV2()
        self.backup_manager = BackupManager()
        self.enable_auto_backup = enable_auto_backup
        self.session_start_time = time.time()
        self.messages_collected = 0
        
        logger.info("微信监听器 v2.0 初始化完成")
        logger.info(f"自动备份: {'启用' if enable_auto_backup else '禁用'}")
    
    def start_listening(self):
        """开始监听群聊"""
        logger.info("=== 微信群聊监听器 v2.0 启动 ===")
        print("--- 微信群聊监听已启动 (v2.0) ---")
        print(f"[*] 监听群聊: {', '.join(GROUP_NAMES)}")
        print(f"[*] 按下 'Esc' 键可随时安全停止脚本。")
        print(f"[*] 数据库版本: {self.db_v2.get_db_version()}")
        print("--------------------------")
        
        # 创建启动前备份（如果启用）
        if self.enable_auto_backup:
            backup_path = self.backup_manager.create_automatic_backup("session_start")
            if backup_path:
                logger.info(f"会话启动备份创建成功: {backup_path}")
        
        try:
            self._main_listening_loop()
        except Exception as e:
            logger.error(f"监听过程中发生错误: {e}")
            print(f"[!] 监听过程中发生错误: {e}")
        finally:
            self._cleanup_and_exit()
    
    def _main_listening_loop(self):
        """主要的监听循环"""
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
                        logger.info(f"群聊 {group} 消息基准初始化完成")
                        continue

                    new_msgs = [msg for msg in msgs if msg not in last_msgs[group]]
                    if new_msgs:
                        for msg in new_msgs:
                            # 增加过滤器：只处理真实用户的消息
                            if msg.sender not in ['system', 'base']:
                                self._save_message_safely(group, msg)
                                
                        last_msgs[group] = msgs # 更新最新的消息列表
                        
                        # 检查是否需要创建周期性备份
                        self._check_periodic_backup()
                    
                except Exception as e:
                    logger.error(f"监听群聊 [{group}] 时出错: {e}")
                    print(f"[!] 监听群聊 [{group}] 时出错: {e}")
            
            if running:
                sleep_duration = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
                print(f"\n[*] 本轮监听完成，休眠 {sleep_duration:.2f} 秒... (按 'Esc' 停止)")
                time.sleep(sleep_duration)
    
    def _save_message_safely(self, group_name: str, msg):
        """安全保存消息到数据库"""
        try:
            # 使用新的安全保存方法
            message_id = self.db_v2.save_raw_message(
                group_name=group_name,
                sender=msg.sender,
                content=msg.content,
                msg_type=msg.type
            )
            
            if message_id:
                self.messages_collected += 1
                print(f"[*] 新消息存入数据库: [{group_name}] {msg.sender}")
                logger.debug(f"消息已保存: ID={message_id}, 群={group_name}, 发送者={msg.sender}")
                
        except Exception as e:
            logger.error(f"保存消息时出错: {e}")
            print(f"[!] 保存消息失败: {e}")
    
    def _check_periodic_backup(self):
        """检查是否需要创建周期性备份"""
        if not self.enable_auto_backup:
            return
            
        # 每收集100条消息创建一次备份
        if self.messages_collected > 0 and self.messages_collected % 100 == 0:
            try:
                backup_path = self.backup_manager.create_automatic_backup("periodic")
                if backup_path:
                    logger.info(f"周期性备份创建成功: {backup_path}")
                    print(f"[*] 已创建周期性备份 (收集了{self.messages_collected}条消息)")
            except Exception as e:
                logger.error(f"创建周期性备份失败: {e}")
    
    def _cleanup_and_exit(self):
        """清理资源并安全退出"""
        logger.info("开始清理资源...")
        
        # 创建退出前备份
        if self.enable_auto_backup and self.messages_collected > 0:
            try:
                backup_path = self.backup_manager.create_automatic_backup("session_end")
                if backup_path:
                    logger.info(f"会话结束备份创建成功: {backup_path}")
                    print(f"[*] 会话结束备份已创建: {backup_path}")
            except Exception as e:
                logger.error(f"创建会话结束备份失败: {e}")
        
        # 记录会话统计
        session_duration = time.time() - self.session_start_time
        logger.info(f"监听会话统计:")
        logger.info(f"  会话时长: {session_duration:.1f}秒")
        logger.info(f"  收集消息: {self.messages_collected}条")
        
        print(f"\n[*] 本次会话收集了 {self.messages_collected} 条消息")
        print(f"[*] 会话时长: {session_duration:.1f} 秒")
        
        # 关闭数据库连接
        try:
            self.db_v2.close()
        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {e}")
        
        print("\n--- 微信群聊监听已安全停止 ---")
        logger.info("微信监听器 v2.0 安全退出完成")

# --- 向后兼容函数 ---
def listen_groups():
    """
    向后兼容的监听函数
    内部使用新的WeChatListenerV2类
    """
    listener = WeChatListenerV2(enable_auto_backup=True)
    listener.start_listening()

# --- 高级功能 ---
def listen_with_custom_config(groups: list = None, 
                            auto_backup: bool = True,
                            backup_interval: int = 100):
    """
    带自定义配置的监听函数
    """
    global GROUP_NAMES
    
    if groups:
        GROUP_NAMES = groups
    
    listener = WeChatListenerV2(enable_auto_backup=auto_backup)
    listener.start_listening()

# --- 主程序入口 ---
if __name__ == "__main__":
    print("=== 微信监听器 v2.0 ===")
    print("支持安全去重架构，自动备份功能")
    print("按 Esc 键安全停止监听\n")
    
    try:
        # 使用新的监听器
        listener = WeChatListenerV2(enable_auto_backup=True)
        listener.start_listening()
        
    except KeyboardInterrupt:
        print("\n[!] 收到中断信号，正在安全退出...")
    except Exception as e:
        print(f"\n[!] 程序异常: {e}")
        logger.error(f"程序异常退出: {e}")
    finally:
        print("程序已退出") 