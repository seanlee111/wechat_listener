"""
配置文件加载器 v1.0
读取和验证高级监听器的配置参数
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class ListenerConfigFromFile:
    """监听器配置（从文件加载）"""
    target_groups: List[str]
    check_interval_seconds: int
    workflow_check_interval_minutes: int
    auto_workflow_enabled: bool
    max_session_duration_hours: int
    enable_realtime_monitoring: bool
    monitoring_port: int

@dataclass
class WorkflowConfigFromFile:
    """工作流配置（从文件加载）"""
    auto_dedup_enabled: bool
    dedup_threshold: int
    auto_backup_enabled: bool
    validation_enabled: bool
    max_dedup_failures: int
    dedup_interval_minutes: int
    health_check_interval_minutes: int

@dataclass
class DatabaseConfigFromFile:
    """数据库配置（从文件加载）"""
    db_path: str
    backup_path: str
    max_backup_files: int
    auto_cleanup_enabled: bool

@dataclass
class LoggingConfigFromFile:
    """日志配置（从文件加载）"""
    level: str
    file_enabled: bool
    console_enabled: bool
    max_log_files: int
    log_file_path: str

@dataclass
class SecurityConfigFromFile:
    """安全配置（从文件加载）"""
    enable_data_encryption: bool
    backup_compression: bool
    data_retention_days: int

@dataclass
class PerformanceConfigFromFile:
    """性能配置（从文件加载）"""
    message_buffer_size: int
    batch_processing_size: int
    max_memory_usage_mb: int
    enable_performance_monitoring: bool

@dataclass
class AppConfigFromFile:
    """应用总配置（从文件加载）"""
    listener: ListenerConfigFromFile
    workflow: WorkflowConfigFromFile
    database: DatabaseConfigFromFile
    logging: LoggingConfigFromFile
    security: SecurityConfigFromFile
    performance: PerformanceConfigFromFile

class ConfigLoader:
    """配置文件加载器"""
    
    def __init__(self, config_file_path: str = "config/listener_config.json"):
        """初始化配置加载器"""
        self.config_file_path = Path(config_file_path)
        self.config_data = None
        self.app_config = None
        
    def load_config(self) -> AppConfigFromFile:
        """加载配置文件"""
        try:
            # 检查配置文件是否存在
            if not self.config_file_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_file_path}")
            
            # 读取配置文件
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            # 验证配置结构
            self._validate_config_structure()
            
            # 解析配置
            self.app_config = self._parse_config()
            
            logger.info(f"✓ 配置文件加载成功: {self.config_file_path}")
            return self.app_config
            
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            raise
    
    def _validate_config_structure(self):
        """验证配置文件结构"""
        required_sections = ["listener", "workflow", "database", "logging", "security", "performance"]
        
        for section in required_sections:
            if section not in self.config_data:
                raise ValueError(f"配置文件缺少必要的节: {section}")
        
        # 验证监听器配置
        listener_config = self.config_data["listener"]
        required_listener_fields = ["target_groups", "check_interval_seconds"]
        
        for field in required_listener_fields:
            if field not in listener_config:
                raise ValueError(f"监听器配置缺少必要字段: {field}")
        
        # 验证目标群聊不为空
        if not listener_config["target_groups"] or len(listener_config["target_groups"]) == 0:
            raise ValueError("目标群聊列表不能为空")
        
        logger.info("✓ 配置文件结构验证通过")
    
    def _parse_config(self) -> AppConfigFromFile:
        """解析配置数据"""
        try:
            # 解析监听器配置
            listener_data = self.config_data["listener"]
            listener_config = ListenerConfigFromFile(
                target_groups=listener_data["target_groups"],
                check_interval_seconds=listener_data.get("check_interval_seconds", 10),
                workflow_check_interval_minutes=listener_data.get("workflow_check_interval_minutes", 30),
                auto_workflow_enabled=listener_data.get("auto_workflow_enabled", True),
                max_session_duration_hours=listener_data.get("max_session_duration_hours", 12),
                enable_realtime_monitoring=listener_data.get("enable_realtime_monitoring", True),
                monitoring_port=listener_data.get("monitoring_port", 8080)
            )
            
            # 解析工作流配置
            workflow_data = self.config_data["workflow"]
            workflow_config = WorkflowConfigFromFile(
                auto_dedup_enabled=workflow_data.get("auto_dedup_enabled", True),
                dedup_threshold=workflow_data.get("dedup_threshold", 50),
                auto_backup_enabled=workflow_data.get("auto_backup_enabled", True),
                validation_enabled=workflow_data.get("validation_enabled", True),
                max_dedup_failures=workflow_data.get("max_dedup_failures", 3),
                dedup_interval_minutes=workflow_data.get("dedup_interval_minutes", 30),
                health_check_interval_minutes=workflow_data.get("health_check_interval_minutes", 60)
            )
            
            # 解析数据库配置
            database_data = self.config_data["database"]
            database_config = DatabaseConfigFromFile(
                db_path=database_data.get("db_path", "data/wechat_jds.db"),
                backup_path=database_data.get("backup_path", "backups/"),
                max_backup_files=database_data.get("max_backup_files", 30),
                auto_cleanup_enabled=database_data.get("auto_cleanup_enabled", True)
            )
            
            # 解析日志配置
            logging_data = self.config_data["logging"]
            logging_config = LoggingConfigFromFile(
                level=logging_data.get("level", "INFO"),
                file_enabled=logging_data.get("file_enabled", True),
                console_enabled=logging_data.get("console_enabled", True),
                max_log_files=logging_data.get("max_log_files", 7),
                log_file_path=logging_data.get("log_file_path", "logs/wechat_listener.log")
            )
            
            # 解析安全配置
            security_data = self.config_data["security"]
            security_config = SecurityConfigFromFile(
                enable_data_encryption=security_data.get("enable_data_encryption", False),
                backup_compression=security_data.get("backup_compression", True),
                data_retention_days=security_data.get("data_retention_days", 365)
            )
            
            # 解析性能配置
            performance_data = self.config_data["performance"]
            performance_config = PerformanceConfigFromFile(
                message_buffer_size=performance_data.get("message_buffer_size", 20),
                batch_processing_size=performance_data.get("batch_processing_size", 500),
                max_memory_usage_mb=performance_data.get("max_memory_usage_mb", 512),
                enable_performance_monitoring=performance_data.get("enable_performance_monitoring", True)
            )
            
            # 组装总配置
            app_config = AppConfigFromFile(
                listener=listener_config,
                workflow=workflow_config,
                database=database_config,
                logging=logging_config,
                security=security_config,
                performance=performance_config
            )
            
            logger.info("✓ 配置数据解析完成")
            return app_config
            
        except Exception as e:
            logger.error(f"配置数据解析失败: {e}")
            raise
    
    def get_listener_summary(self) -> str:
        """获取监听器配置摘要"""
        if not self.app_config:
            return "配置未加载"
        
        listener = self.app_config.listener
        workflow = self.app_config.workflow
        
        summary = f"""
=== 高级监听器配置摘要 ===
目标群聊: {', '.join(listener.target_groups)}
监听间隔: {listener.check_interval_seconds}秒
工作流间隔: {listener.workflow_check_interval_minutes}分钟
去重阈值: {workflow.dedup_threshold}条消息
自动工作流: {'开启' if listener.auto_workflow_enabled else '关闭'}
实时监控: {'开启' if listener.enable_realtime_monitoring else '关闭'}
自动去重: {'开启' if workflow.auto_dedup_enabled else '关闭'}
自动备份: {'开启' if workflow.auto_backup_enabled else '关闭'}
数据验证: {'开启' if workflow.validation_enabled else '关闭'}
最大会话时长: {listener.max_session_duration_hours}小时
缓冲区大小: {self.app_config.performance.message_buffer_size}条消息
        """.strip()
        
        return summary
    
    def save_config_template(self, output_path: str = "config/listener_config_template.json"):
        """保存配置文件模板"""
        template = {
            "listener": {
                "target_groups": ["请修改为你的微信群名称"],
                "check_interval_seconds": 10,
                "workflow_check_interval_minutes": 30,
                "auto_workflow_enabled": True,
                "max_session_duration_hours": 12,
                "enable_realtime_monitoring": True,
                "monitoring_port": 8080
            },
            "workflow": {
                "auto_dedup_enabled": True,
                "dedup_threshold": 50,
                "auto_backup_enabled": True,
                "validation_enabled": True,
                "max_dedup_failures": 3,
                "dedup_interval_minutes": 30,
                "health_check_interval_minutes": 60
            },
            "database": {
                "db_path": "data/wechat_jds.db",
                "backup_path": "backups/",
                "max_backup_files": 30,
                "auto_cleanup_enabled": True
            },
            "logging": {
                "level": "INFO",
                "file_enabled": True,
                "console_enabled": True,
                "max_log_files": 7,
                "log_file_path": "logs/wechat_listener.log"
            },
            "security": {
                "enable_data_encryption": False,
                "backup_compression": True,
                "data_retention_days": 365
            },
            "performance": {
                "message_buffer_size": 20,
                "batch_processing_size": 500,
                "max_memory_usage_mb": 512,
                "enable_performance_monitoring": True
            }
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ 配置模板已保存: {output_file}")

# --- 便利函数 ---
def load_listener_config(config_file: str = "config/listener_config.json") -> AppConfigFromFile:
    """加载监听器配置的便利函数"""
    loader = ConfigLoader(config_file)
    return loader.load_config()

def create_config_template(output_path: str = "config/listener_config_template.json"):
    """创建配置模板的便利函数"""
    loader = ConfigLoader()
    loader.save_config_template(output_path)

# --- 主程序入口 ---
if __name__ == "__main__":
    print("=== 配置加载器测试 ===")
    
    try:
        # 创建配置模板
        create_config_template()
        print("✓ 配置模板创建成功")
        
        # 加载配置
        config = load_listener_config()
        
        # 显示配置摘要
        loader = ConfigLoader()
        loader.app_config = config
        print(loader.get_listener_summary())
        
    except Exception as e:
        print(f"❌ 测试失败: {e}") 