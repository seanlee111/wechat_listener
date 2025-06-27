#!/usr/bin/env python3
"""
配置化高级监听器启动脚本 v1.0
从配置文件启动微信监听器，支持所有参数自定义
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# 添加src目录到路径
sys.path.append('src')

from config_loader import ConfigLoader, AppConfigFromFile
from wechat_listener_advanced import WeChatListenerAdvanced, ListenerConfig
from workflow_manager import WorkflowConfig
from database_v2 import DatabaseV2

# 确保日志目录存在
log_dir = Path('logs')
log_dir.mkdir(parents=True, exist_ok=True)

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/listener_startup.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class ConfigurableListener:
    """配置化监听器启动器"""
    
    def __init__(self, config_file: str = "config/listener_config.json"):
        """初始化配置化监听器"""
        self.config_file = config_file
        self.app_config = None
        self.listener = None
        
    def start(self) -> bool:
        """启动监听器"""
        try:
            # 第1步：加载配置
            logger.info("=== 启动配置化高级微信监听器 ===")
            if not self._load_config():
                return False
            
            # 第2步：显示配置摘要
            self._display_config_summary()
            
            # 第3步：初始化环境
            if not self._setup_environment():
                return False
            
            # 第4步：创建监听器
            if not self._create_listener():
                return False
            
            # 第5步：启动监听
            logger.info("启动监听器...")
            success = self.listener.start_monitoring()
            
            if success:
                logger.info("✓ 监听器启动成功")
            else:
                logger.error("✗ 监听器启动失败")
            
            return success
            
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在安全关闭...")
            if self.listener:
                self.listener.stop_monitoring()
            return True
            
        except Exception as e:
            logger.error(f"启动监听器时发生错误: {e}")
            return False
    
    def _load_config(self) -> bool:
        """加载配置文件"""
        try:
            # 检查配置文件是否存在
            if not Path(self.config_file).exists():
                logger.error(f"配置文件不存在: {self.config_file}")
                logger.info("正在创建配置模板...")
                
                # 创建配置目录和模板
                config_dir = Path(self.config_file).parent
                config_dir.mkdir(parents=True, exist_ok=True)
                
                from config_loader import create_config_template
                create_config_template(self.config_file)
                
                logger.info(f"✓ 配置模板已创建: {self.config_file}")
                logger.info("请修改配置文件后重新运行")
                return False
            
            # 加载配置
            loader = ConfigLoader(self.config_file)
            self.app_config = loader.load_config()
            
            logger.info(f"✓ 配置文件加载成功: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return False
    
    def _display_config_summary(self):
        """显示配置摘要"""
        try:
            listener = self.app_config.listener
            workflow = self.app_config.workflow
            
            print("\n" + "="*60)
            print("           高级微信监听器配置摘要")
            print("="*60)
            print(f"目标群聊: {', '.join(listener.target_groups)}")
            print(f"监听间隔: {listener.check_interval_seconds}秒")
            print(f"工作流间隔: {listener.workflow_check_interval_minutes}分钟")
            print(f"去重阈值: {workflow.dedup_threshold}条消息")
            print(f"缓冲区大小: {self.app_config.performance.message_buffer_size}条")
            print(f"最大会话时长: {listener.max_session_duration_hours}小时")
            print()
            print("功能开关:")
            print(f"  自动工作流: {'[开启]' if listener.auto_workflow_enabled else '[关闭]'}")
            print(f"  自动去重: {'[开启]' if workflow.auto_dedup_enabled else '[关闭]'}")
            print(f"  自动备份: {'[开启]' if workflow.auto_backup_enabled else '[关闭]'}")
            print(f"  数据验证: {'[开启]' if workflow.validation_enabled else '[关闭]'}")
            print(f"  实时监控: {'[开启]' if listener.enable_realtime_monitoring else '[关闭]'}")
            print("="*60)
            
        except Exception as e:
            logger.error(f"显示配置摘要时出错: {e}")
    
    def _setup_environment(self) -> bool:
        """设置运行环境"""
        try:
            # 创建必要的目录
            directories = [
                self.app_config.database.backup_path,
                Path(self.app_config.logging.log_file_path).parent,
                Path(self.app_config.database.db_path).parent
            ]
            
            for directory in directories:
                Path(directory).mkdir(parents=True, exist_ok=True)
            
            # 设置日志级别
            log_level = getattr(logging, self.app_config.logging.level.upper(), logging.INFO)
            logging.getLogger().setLevel(log_level)
            
            logger.info("✓ 运行环境设置完成")
            return True
            
        except Exception as e:
            logger.error(f"设置运行环境失败: {e}")
            return False
    
    def _create_listener(self) -> bool:
        """创建监听器实例"""
        try:
            # 转换配置格式
            listener_config = ListenerConfig(
                target_groups=self.app_config.listener.target_groups,
                check_interval_seconds=self.app_config.listener.check_interval_seconds,
                workflow_check_interval_minutes=self.app_config.listener.workflow_check_interval_minutes,
                auto_workflow_enabled=self.app_config.listener.auto_workflow_enabled,
                max_session_duration_hours=self.app_config.listener.max_session_duration_hours,
                enable_realtime_monitoring=self.app_config.listener.enable_realtime_monitoring,
                monitoring_port=self.app_config.listener.monitoring_port
            )
            
            # 创建高级监听器，同时传入工作流配置
            self.listener = WeChatListenerAdvanced(listener_config)
            
            # 更新工作流管理器配置
            workflow_config = WorkflowConfig(
                auto_dedup_enabled=self.app_config.workflow.auto_dedup_enabled,
                dedup_threshold=self.app_config.workflow.dedup_threshold,
                auto_backup_enabled=self.app_config.workflow.auto_backup_enabled,
                validation_enabled=self.app_config.workflow.validation_enabled,
                max_dedup_failures=self.app_config.workflow.max_dedup_failures,
                dedup_interval_minutes=self.app_config.workflow.dedup_interval_minutes,
                health_check_interval_minutes=self.app_config.workflow.health_check_interval_minutes
            )
            
            # 重新初始化工作流管理器
            from workflow_manager import WorkflowManager
            self.listener.workflow_manager = WorkflowManager(workflow_config)
            
            logger.info("✓ 监听器实例创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建监听器实例失败: {e}")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="配置化高级微信监听器")
    parser.add_argument(
        '-c', '--config', 
        default='config/listener_config.json',
        help='配置文件路径 (默认: config/listener_config.json)'
    )
    parser.add_argument(
        '--create-template',
        action='store_true',
        help='创建配置文件模板'
    )
    
    args = parser.parse_args()
    
    try:
        # 如果只是创建模板
        if args.create_template:
            from config_loader import create_config_template
            create_config_template(args.config)
            print(f"✓ 配置模板已创建: {args.config}")
            print("请修改配置文件中的参数后运行监听器")
            return
        
        # 启动监听器
        print(f"使用配置文件: {args.config}")
        listener = ConfigurableListener(args.config)
        success = listener.start()
        
        if not success:
            print("❌ 监听器启动失败")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n👋 监听器已停止")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 