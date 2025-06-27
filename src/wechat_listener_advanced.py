"""
微信监听器 v2.0 高级版
整合工作流管理、实时监控和自动化处理
"""

import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import logging
from pathlib import Path

import wxauto

from database_v2 import DatabaseV2
from workflow_manager import WorkflowManager, WorkflowConfig
from backup_manager import BackupManager

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class ListenerConfig:
    """监听器配置"""
    target_groups: List[str]  # 目标群聊列表
    check_interval_seconds: int = 10  # 检查间隔
    workflow_check_interval_minutes: int = 30  # 工作流检查间隔
    auto_workflow_enabled: bool = True  # 自动工作流
    max_session_duration_hours: int = 12  # 最大会话时长
    enable_realtime_monitoring: bool = True  # 实时监控
    monitoring_port: int = 8080  # 监控端口
    
@dataclass
class SessionStats:
    """会话统计"""
    session_id: str
    start_time: datetime
    messages_collected: int = 0
    groups_monitored: int = 0
    workflow_runs: int = 0
    last_activity_time: Optional[datetime] = None
    is_active: bool = True

class WeChatListenerAdvanced:
    """
    微信监听器高级版
    支持工作流管理、实时监控和自动化处理
    """
    
    def __init__(self, config: ListenerConfig):
        """初始化高级监听器"""
        self.config = config
        
        # 初始化组件
        self.db_v2 = DatabaseV2()
        self.workflow_manager = WorkflowManager(
            WorkflowConfig(
                auto_dedup_enabled=True,
                dedup_threshold=50,  # 更低的阈值，更频繁的去重
                auto_backup_enabled=True,
                validation_enabled=True
            )
        )
        
        # 会话管理
        self.session_stats = SessionStats(
            session_id=self._generate_session_id(),
            start_time=datetime.now()
        )
        
        # 微信自动化
        self.wx = None
        self.is_running = False
        self.monitoring_thread = None
        self.workflow_thread = None
        
        # 性能监控
        self.message_buffer = []
        self.last_workflow_run = None
        
        # 简单去重：记录最近处理的消息
        self.processed_messages = set()  # 存储 (group_name, sender, content) 的哈希
        
        logger.info(f"高级微信监听器初始化完成，会话ID: {self.session_stats.session_id}")
        logger.info(f"目标群聊: {self.config.target_groups}")
        logger.info(f"自动工作流: {self.config.auto_workflow_enabled}")
    
    def start_monitoring(self) -> bool:
        """启动监控"""
        try:
            logger.info("=== 启动高级微信监听器 ===")
            
            # 初始化微信自动化
            if not self._initialize_wechat():
                logger.error("微信初始化失败")
                return False
            
            # 记录会话开始
            self._log_session_start()
            
            # 启动主监听循环
            self.is_running = True
            
            # 启动后台工作流线程
            if self.config.auto_workflow_enabled:
                self._start_workflow_thread()
            
            # 启动实时监控线程
            if self.config.enable_realtime_monitoring:
                self._start_monitoring_thread()
            
            # 主监听循环
            self._run_main_loop()
            
            return True
            
        except Exception as e:
            logger.error(f"启动监控时发生错误: {e}")
            return False
        finally:
            self._cleanup()
    
    def stop_monitoring(self):
        """停止监控"""
        logger.info("正在停止监控...")
        self.is_running = False
        
        # 等待线程结束
        if self.workflow_thread and self.workflow_thread.is_alive():
            self.workflow_thread.join(timeout=30)
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=10)
        
        # 记录会话结束
        self._log_session_end()
        
        logger.info("监控已停止")
    
    def get_session_status(self) -> Dict[str, Any]:
        """获取会话状态"""
        runtime = datetime.now() - self.session_stats.start_time
        
        status = {
            "session_info": {
                "session_id": self.session_stats.session_id,
                "start_time": self.session_stats.start_time.isoformat(),
                "runtime_seconds": runtime.total_seconds(),
                "is_active": self.session_stats.is_active and self.is_running
            },
            "statistics": {
                "messages_collected": self.session_stats.messages_collected,
                "groups_monitored": len(self.config.target_groups),
                "workflow_runs": self.session_stats.workflow_runs,
                "buffer_size": len(self.message_buffer)
            },
            "configuration": {
                "target_groups": self.config.target_groups,
                "check_interval": self.config.check_interval_seconds,
                "auto_workflow": self.config.auto_workflow_enabled,
                "realtime_monitoring": self.config.enable_realtime_monitoring
            },
            "system_status": self.workflow_manager.get_system_status() if self.workflow_manager else {}
        }
        
        return status
    
    def force_workflow_run(self) -> bool:
        """强制执行工作流"""
        logger.info("强制执行工作流...")
        try:
            # 首先保存缓冲区中的消息
            if self.message_buffer:
                self._save_buffered_messages()
            
            # 执行工作流
            success = self.workflow_manager.execute_complete_workflow()
            
            if success:
                self.session_stats.workflow_runs += 1
                self.last_workflow_run = datetime.now()
                logger.info("✓ 工作流执行成功")
            else:
                logger.error("工作流执行失败")
            
            return success
            
        except Exception as e:
            logger.error(f"强制执行工作流时出错: {e}")
            return False
    
    def _initialize_wechat(self) -> bool:
        """初始化微信自动化"""
        try:
            logger.info("初始化微信自动化...")
            self.wx = wxauto.WeChat()
            
            # 验证微信连接
            if not self.wx:
                logger.error("无法连接到微信")
                return False
            
            # 检查目标群聊是否存在
            available_groups = []
            for group_name in self.config.target_groups:
                try:
                    # 尝试选择群聊
                    group = self.wx.ChatWith(group_name)
                    if group:
                        available_groups.append(group_name)
                        logger.info(f"✓ 找到目标群聊: {group_name}")
                    else:
                        logger.warning(f"找不到群聊: {group_name}")
                except Exception as e:
                    logger.warning(f"检查群聊 {group_name} 时出错: {e}")
            
            if not available_groups:
                logger.error("没有找到任何可用的目标群聊")
                return False
            
            self.session_stats.groups_monitored = len(available_groups)
            logger.info(f"✓ 微信初始化成功，监控 {len(available_groups)} 个群聊")
            return True
            
        except Exception as e:
            logger.error(f"初始化微信时出错: {e}")
            return False
    
    def _run_main_loop(self):
        """运行主监听循环"""
        logger.info("开始主监听循环...")
        
        try:
            while self.is_running:
                # 检查会话是否超时
                if self._is_session_expired():
                    logger.info("会话超时，停止监听")
                    break
                
                # 收集所有群聊的新消息
                new_messages = self._collect_messages_from_all_groups()
                
                if new_messages:
                    # 添加到缓冲区
                    self.message_buffer.extend(new_messages)
                    self.session_stats.messages_collected += len(new_messages)
                    self.session_stats.last_activity_time = datetime.now()
                    
                    logger.info(f"收集到 {len(new_messages)} 条新消息，缓冲区大小: {len(self.message_buffer)}")
                    
                    # 如果缓冲区达到一定大小，保存到数据库
                    if len(self.message_buffer) >= 20:
                        self._save_buffered_messages()
                
                # 等待下次检查
                time.sleep(self.config.check_interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("收到停止信号")
        except Exception as e:
            logger.error(f"主监听循环中发生错误: {e}")
        finally:
            # 保存剩余的缓冲消息
            if self.message_buffer:
                self._save_buffered_messages()
    
    def _collect_messages_from_all_groups(self) -> List[Dict]:
        """从所有目标群聊收集消息"""
        all_new_messages = []
        
        for group_name in self.config.target_groups:
            try:
                # 获取该群聊的新消息
                new_messages = self._collect_messages_from_group(group_name)
                all_new_messages.extend(new_messages)
                
            except Exception as e:
                logger.error(f"从群聊 {group_name} 收集消息时出错: {e}")
                continue
        
        return all_new_messages
    
    def _collect_messages_from_group(self, group_name: str) -> List[Dict]:
        """从单个群聊收集消息"""
        try:
            # 切换到目标群聊
            self.wx.ChatWith(group_name)
            
            # 获取最近的消息（直接从wx实例获取）
            messages = self.wx.GetAllMessage()
            if not messages:
                return []
            
            # 获取数据库中该群最后一条消息的时间戳
            last_timestamp = self._get_last_message_timestamp(group_name)
            
            # 过滤新消息（简化处理，使用当前时间）
            new_messages = []
            for msg in messages:
                try:
                    # 获取消息基本信息
                    sender = msg.sender if hasattr(msg, 'sender') else "Unknown"
                    content = msg.content if hasattr(msg, 'content') else str(msg)
                    
                    # 简单去重：基于群聊、发送者、内容生成唯一标识
                    message_key = (group_name, sender, content)
                    if message_key in self.processed_messages:
                        continue  # 跳过已处理的消息
                    
                    # 标记为已处理
                    self.processed_messages.add(message_key)
                    
                    # 简化处理：使用当前时间作为消息时间
                    current_time = datetime.now()
                    
                    message_data = {
                        "group_name": group_name,
                        "sender": sender,
                        "content": content,
                        "msg_type": "text",  # 简化处理
                        "timestamp": current_time.isoformat(),
                        "session_id": self.session_stats.session_id,
                        "collected_at": current_time.isoformat()
                    }
                    new_messages.append(message_data)
                    
                except Exception as e:
                    logger.error(f"解析消息时出错: {e}")
                    continue
            
            return new_messages
            
        except Exception as e:
            logger.error(f"从群聊 {group_name} 收集消息时出错: {e}")
            return []
    
    def _parse_message_time(self, time_str: str) -> datetime:
        """解析消息时间"""
        try:
            # 这里需要根据wxauto返回的时间格式进行解析
            # 简化处理，假设是标准格式
            if isinstance(time_str, datetime):
                return time_str
            elif isinstance(time_str, str):
                # 尝试多种时间格式
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%m-%d %H:%M",
                    "%H:%M:%S",
                    "%H:%M"
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(time_str, fmt)
                    except ValueError:
                        continue
                
                # 如果都失败了，返回当前时间
                logger.warning(f"无法解析时间格式: {time_str}")
                return datetime.now()
            else:
                return datetime.now()
                
        except Exception as e:
            logger.error(f"解析消息时间时出错: {e}")
            return datetime.now()
    
    def _get_last_message_timestamp(self, group_name: str) -> Optional[datetime]:
        """获取该群聊最后一条消息的时间戳"""
        try:
            result = list(self.db_v2.db.execute("""
                SELECT MAX(timestamp) as last_time FROM messages_raw 
                WHERE group_name = ?
            """, [group_name]))
            
            if result and result[0][0]:
                return datetime.fromisoformat(result[0][0])
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取最后消息时间戳时出错: {e}")
            return None
    
    def _save_buffered_messages(self):
        """保存缓冲区中的消息"""
        if not self.message_buffer:
            return
        
        try:
            logger.info(f"保存 {len(self.message_buffer)} 条缓冲消息到数据库...")
            
            # 批量保存到数据库
            saved_count = 0
            for message in self.message_buffer:
                try:
                    self.db_v2.save_raw_message(
                        group_name=message["group_name"],
                        sender=message["sender"],
                        content=message["content"],
                        msg_type=message["msg_type"]
                    )
                    saved_count += 1
                except Exception as e:
                    logger.error(f"保存消息时出错: {e}")
                    continue
            
            logger.info(f"✓ 成功保存 {saved_count} 条消息")
            
            # 清空缓冲区
            self.message_buffer.clear()
            
            # 定期清理已处理消息记录（防止内存无限增长）
            if len(self.processed_messages) > 1000:
                self.processed_messages.clear()
                logger.info("已清理消息去重记录")
            
        except Exception as e:
            logger.error(f"保存缓冲消息时出错: {e}")
    
    def _start_workflow_thread(self):
        """启动工作流线程"""
        def workflow_worker():
            logger.info("工作流线程启动")
            
            while self.is_running:
                try:
                    # 等待工作流检查间隔
                    for _ in range(self.config.workflow_check_interval_minutes * 60):
                        if not self.is_running:
                            break
                        time.sleep(1)
                    
                    if not self.is_running:
                        break
                    
                    # 保存当前缓冲区消息
                    if self.message_buffer:
                        self._save_buffered_messages()
                    
                    # 执行工作流
                    logger.info("定时执行工作流...")
                    success = self.workflow_manager.execute_complete_workflow()
                    
                    if success:
                        self.session_stats.workflow_runs += 1
                        self.last_workflow_run = datetime.now()
                        logger.info("✓ 定时工作流执行成功")
                    else:
                        logger.warning("定时工作流执行失败")
                        
                except Exception as e:
                    logger.error(f"工作流线程中发生错误: {e}")
            
            logger.info("工作流线程结束")
        
        self.workflow_thread = threading.Thread(target=workflow_worker, daemon=True)
        self.workflow_thread.start()
        logger.info("工作流线程已启动")
    
    def _start_monitoring_thread(self):
        """启动监控线程"""
        def monitoring_worker():
            logger.info("监控线程启动")
            
            while self.is_running:
                try:
                    # 每60秒输出一次状态
                    time.sleep(60)
                    
                    if not self.is_running:
                        break
                    
                    # 输出状态信息
                    status = self.get_session_status()
                    logger.info(f"监控状态 - 消息: {status['statistics']['messages_collected']}, "
                              f"缓冲: {status['statistics']['buffer_size']}, "
                              f"工作流: {status['statistics']['workflow_runs']}")
                    
                    # 检查系统健康状况
                    system_status = status.get('system_status', {})
                    if 'database' in system_status:
                        db_status = system_status['database']
                        logger.info(f"数据库状态 - 原始: {db_status.get('raw_messages', 0)}, "
                                  f"清洁: {db_status.get('clean_messages', 0)}, "
                                  f"未处理: {db_status.get('unprocessed_messages', 0)}")
                        
                except Exception as e:
                    logger.error(f"监控线程中发生错误: {e}")
            
            logger.info("监控线程结束")
        
        self.monitoring_thread = threading.Thread(target=monitoring_worker, daemon=True)
        self.monitoring_thread.start()
        logger.info("监控线程已启动")
    
    def _is_session_expired(self) -> bool:
        """检查会话是否超时"""
        runtime = datetime.now() - self.session_stats.start_time
        return runtime.total_seconds() / 3600 >= self.config.max_session_duration_hours
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"listener_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _log_session_start(self):
        """记录会话开始"""
        try:
            session_data = {
                "session_id": self.session_stats.session_id,
                "target_groups": self.config.target_groups,
                "config": {
                    "check_interval": self.config.check_interval_seconds,
                    "auto_workflow": self.config.auto_workflow_enabled,
                    "realtime_monitoring": self.config.enable_realtime_monitoring
                }
            }
            
            batch_id = self.db_v2.generate_batch_id()
            self.db_v2.log_processing_batch(
                batch_id=batch_id,
                operation_type="listener_session_start",
                status="started",
                config_snapshot=json.dumps(session_data)
            )
            
            logger.info(f"会话开始已记录，批次ID: {batch_id}")
            
        except Exception as e:
            logger.error(f"记录会话开始时出错: {e}")
    
    def _log_session_end(self):
        """记录会话结束"""
        try:
            self.session_stats.is_active = False
            runtime = datetime.now() - self.session_stats.start_time
            
            session_summary = {
                "session_id": self.session_stats.session_id,
                "runtime_seconds": runtime.total_seconds(),
                "messages_collected": self.session_stats.messages_collected,
                "workflow_runs": self.session_stats.workflow_runs,
                "groups_monitored": self.session_stats.groups_monitored
            }
            
            batch_id = self.db_v2.generate_batch_id()
            self.db_v2.log_processing_batch(
                batch_id=batch_id,
                operation_type="listener_session_end",
                status="completed",
                records_processed=self.session_stats.messages_collected,
                execution_time_ms=int(runtime.total_seconds() * 1000),
                config_snapshot=json.dumps(session_summary)
            )
            
            logger.info(f"会话结束已记录，批次ID: {batch_id}")
            logger.info(f"会话统计 - 运行时间: {runtime.total_seconds()/3600:.1f}小时, "
                       f"收集消息: {self.session_stats.messages_collected}条, "
                       f"工作流运行: {self.session_stats.workflow_runs}次")
            
        except Exception as e:
            logger.error(f"记录会话结束时出错: {e}")
    
    def _cleanup(self):
        """清理资源"""
        try:
            # 保存剩余消息
            if self.message_buffer:
                self._save_buffered_messages()
            
            # 关闭数据库连接
            if self.db_v2:
                self.db_v2.close()
            
            # 关闭工作流管理器
            if self.workflow_manager:
                self.workflow_manager.close()
            
            logger.info("资源清理完成")
            
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")

# --- 便利函数 ---

def start_advanced_listener(target_groups: List[str], 
                          auto_workflow: bool = True,
                          check_interval: int = 10) -> bool:
    """启动高级监听器的便利函数"""
    
    config = ListenerConfig(
        target_groups=target_groups,
        check_interval_seconds=check_interval,
        auto_workflow_enabled=auto_workflow,
        enable_realtime_monitoring=True
    )
    
    listener = WeChatListenerAdvanced(config)
    return listener.start_monitoring()

# --- 主程序入口 ---
if __name__ == "__main__":
    # 测试高级监听器
    print("=== 微信监听器高级版测试 ===")
    
    # 配置目标群聊（需要根据实际情况修改）
    target_groups = ["NFC金融实习分享群（一）",
      "NJU后浪-优质实习交流群"]
    
    try:
        success = start_advanced_listener(
            target_groups=target_groups,
            auto_workflow=True,
            check_interval=15
        )
        
        if success:
            print("✓ 高级监听器启动成功")
        else:
            print("❌ 高级监听器启动失败")
            
    except KeyboardInterrupt:
        print("\n监听器已停止")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise 