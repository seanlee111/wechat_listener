"""
工作流管理器 v2.0
整合监听、去重、验证等所有组件的统一工作流
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from pathlib import Path
import logging

from database_v2 import DatabaseV2
from backup_manager import BackupManager
from safe_deduplicator import SafeDeduplicator, DedupStats
from data_validator import DataValidator, ValidationResult

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class WorkflowConfig:
    """工作流配置"""
    auto_dedup_enabled: bool = True
    dedup_threshold: int = 100  # 积累多少条未处理消息后触发去重
    auto_backup_enabled: bool = True
    validation_enabled: bool = True
    max_dedup_failures: int = 3
    dedup_interval_minutes: int = 30
    health_check_interval_minutes: int = 60

@dataclass
class WorkflowStats:
    """工作流统计"""
    total_messages_processed: int = 0
    total_dedups_executed: int = 0
    total_backups_created: int = 0
    total_validations_performed: int = 0
    last_dedup_time: Optional[datetime] = None
    last_backup_time: Optional[datetime] = None
    last_validation_time: Optional[datetime] = None
    dedup_failure_count: int = 0

class WorkflowManager:
    """
    工作流管理器
    协调各个组件的工作，提供统一的接口
    """
    
    def __init__(self, config: Optional[WorkflowConfig] = None):
        """初始化工作流管理器"""
        self.config = config or WorkflowConfig()
        
        # 初始化组件
        self.db_v2 = DatabaseV2()
        self.backup_manager = BackupManager()
        self.deduplicator = SafeDeduplicator()
        self.validator = DataValidator()
        
        # 统计信息
        self.stats = WorkflowStats()
        
        logger.info("工作流管理器初始化完成")
        logger.info(f"配置: 自动去重={self.config.auto_dedup_enabled}, 去重阈值={self.config.dedup_threshold}")
    
    def execute_complete_workflow(self) -> bool:
        """
        执行完整的数据处理工作流
        """
        logger.info("=== 开始执行完整数据处理工作流 ===")
        
        try:
            # 第1步：健康检查
            if not self._perform_health_check():
                logger.error("健康检查失败，工作流中止")
                return False
            
            # 第2步：检查是否需要执行去重
            if self._should_execute_deduplication():
                if not self._execute_deduplication_workflow():
                    logger.error("去重工作流失败")
                    return False
            
            # 第3步：执行数据验证
            if self.config.validation_enabled:
                if not self._execute_validation_workflow():
                    logger.warning("验证工作流失败，但继续执行")
            
            # 第4步：执行清理和优化
            self._execute_cleanup_workflow()
            
            # 第5步：生成状态报告
            self._generate_status_report()
            
            logger.info("=== 完整数据处理工作流执行完成 ===")
            return True
            
        except Exception as e:
            logger.error(f"执行工作流时发生错误: {e}")
            return False
    
    def execute_deduplication_only(self) -> bool:
        """只执行去重操作"""
        logger.info("执行去重操作...")
        return self._execute_deduplication_workflow()
    
    def execute_validation_only(self) -> bool:
        """只执行验证操作"""
        logger.info("执行验证操作...")
        return self._execute_validation_workflow()
    
    def execute_backup_only(self) -> bool:
        """只执行备份操作"""
        logger.info("执行备份操作...")
        return self._execute_backup_workflow()
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 获取数据库统计
            raw_count = self.db_v2.db["messages_raw"].count
            clean_count = self.db_v2.db["messages_clean"].count
            
            # 获取未处理消息数量
            unprocessed = list(self.db_v2.db.execute("""
                SELECT COUNT(*) as count FROM messages_raw WHERE processed_status = 0
            """))
            unprocessed_count = unprocessed[0][0] if unprocessed else 0
            
            # 获取最近的处理日志
            recent_logs = list(self.db_v2.db.execute("""
                SELECT operation_type, status, created_at 
                FROM processing_logs 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            
            status = {
                "database": {
                    "raw_messages": raw_count,
                    "clean_messages": clean_count,
                    "unprocessed_messages": unprocessed_count,
                    "dedup_ratio": clean_count / max(raw_count, 1)
                },
                "workflow_stats": {
                    "total_messages_processed": self.stats.total_messages_processed,
                    "total_dedups_executed": self.stats.total_dedups_executed,
                    "total_backups_created": self.stats.total_backups_created,
                    "dedup_failure_count": self.stats.dedup_failure_count,
                    "last_dedup_time": self.stats.last_dedup_time.isoformat() if self.stats.last_dedup_time else None
                },
                "system": {
                    "database_version": self.db_v2.get_db_version(),
                    "auto_dedup_enabled": self.config.auto_dedup_enabled,
                    "needs_deduplication": self._should_execute_deduplication()
                },
                "recent_operations": [
                    {
                        "operation": log[0],
                        "status": log[1],
                        "time": log[2]
                    } for log in recent_logs
                ]
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取系统状态时出错: {e}")
            return {"error": str(e)}
    
    def _perform_health_check(self) -> bool:
        """执行系统健康检查"""
        try:
            logger.info("执行系统健康检查...")
            
            # 检查数据库连接
            if not self.db_v2.db:
                logger.error("数据库连接失败")
                return False
            
            # 检查必要的表
            required_tables = ["messages_raw", "messages_clean", "processing_logs"]
            existing_tables = self.db_v2.db.table_names()
            
            for table in required_tables:
                if table not in existing_tables:
                    logger.error(f"缺少必要的表: {table}")
                    return False
            
            # 检查磁盘空间 (简化实现)
            try:
                # 尝试写入测试数据
                test_data = {"test": "health_check", "timestamp": datetime.now().isoformat()}
                self.db_v2.db.execute("CREATE TEMP TABLE IF NOT EXISTS health_check_test (data TEXT)")
                self.db_v2.db.execute("INSERT INTO health_check_test (data) VALUES (?)", [json.dumps(test_data)])
                self.db_v2.db.execute("DROP TABLE health_check_test")
            except Exception as e:
                logger.error(f"数据库写入测试失败: {e}")
                return False
            
            logger.info("✓ 系统健康检查通过")
            return True
            
        except Exception as e:
            logger.error(f"健康检查时出错: {e}")
            return False
    
    def _should_execute_deduplication(self) -> bool:
        """判断是否应该执行去重"""
        if not self.config.auto_dedup_enabled:
            return False
        
        try:
            # 检查未处理消息数量
            unprocessed = self.db_v2.get_unprocessed_raw_messages(1)
            if len(unprocessed) == 0:
                return False
            
            # 获取实际未处理数量
            unprocessed_count = list(self.db_v2.db.execute("""
                SELECT COUNT(*) as count FROM messages_raw WHERE processed_status = 0
            """))
            
            count = unprocessed_count[0][0] if unprocessed_count else 0
            
            if count >= self.config.dedup_threshold:
                logger.info(f"未处理消息数 ({count}) 达到阈值 ({self.config.dedup_threshold})，需要执行去重")
                return True
            
            # 检查是否超过时间间隔
            if self.stats.last_dedup_time:
                time_since_last = datetime.now() - self.stats.last_dedup_time
                if time_since_last.total_seconds() / 60 >= self.config.dedup_interval_minutes:
                    logger.info(f"距离上次去重已过 {time_since_last.total_seconds()/60:.1f} 分钟，需要执行去重")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"判断是否需要去重时出错: {e}")
            return False
    
    def _execute_deduplication_workflow(self) -> bool:
        """执行去重工作流"""
        try:
            logger.info("开始执行去重工作流...")
            
            # 创建操作前备份
            if self.config.auto_backup_enabled:
                backup_path = self.backup_manager.create_automatic_backup("pre_deduplication")
                if backup_path:
                    logger.info(f"✓ 去重前备份创建成功")
                    self.stats.total_backups_created += 1
                    self.stats.last_backup_time = datetime.now()
            
            # 执行去重
            success = self.deduplicator.execute_safe_deduplication()
            
            if success:
                logger.info("✓ 去重操作成功")
                self.stats.total_dedups_executed += 1
                self.stats.last_dedup_time = datetime.now()
                self.stats.dedup_failure_count = 0  # 重置失败计数
                
                # 更新处理消息统计
                self.stats.total_messages_processed += self.deduplicator.stats.processed_messages
                
                return True
            else:
                logger.error("去重操作失败")
                self.stats.dedup_failure_count += 1
                
                # 如果失败次数过多，禁用自动去重
                if self.stats.dedup_failure_count >= self.config.max_dedup_failures:
                    logger.error(f"去重连续失败 {self.stats.dedup_failure_count} 次，禁用自动去重")
                    self.config.auto_dedup_enabled = False
                
                return False
                
        except Exception as e:
            logger.error(f"执行去重工作流时出错: {e}")
            self.stats.dedup_failure_count += 1
            return False
    
    def _execute_validation_workflow(self) -> bool:
        """执行验证工作流"""
        try:
            logger.info("开始执行验证工作流...")
            
            # 执行数据库完整性验证
            result = self.validator.validate_database_integrity()
            
            self.stats.total_validations_performed += 1
            self.stats.last_validation_time = datetime.now()
            
            if result.is_valid:
                logger.info("✓ 数据验证通过")
                return True
            else:
                logger.warning(f"数据验证发现问题: {result.error_count} 个错误, {result.warning_count} 个警告")
                
                # 记录验证结果
                self._log_validation_result(result)
                return False
                
        except Exception as e:
            logger.error(f"执行验证工作流时出错: {e}")
            return False
    
    def _execute_backup_workflow(self) -> bool:
        """执行备份工作流"""
        try:
            logger.info("开始执行备份工作流...")
            
            backup_path = self.backup_manager.create_manual_backup("workflow_manual_backup")
            
            if backup_path:
                logger.info(f"✓ 手动备份创建成功: {backup_path}")
                self.stats.total_backups_created += 1
                self.stats.last_backup_time = datetime.now()
                return True
            else:
                logger.error("手动备份创建失败")
                return False
                
        except Exception as e:
            logger.error(f"执行备份工作流时出错: {e}")
            return False
    
    def _execute_cleanup_workflow(self):
        """执行清理工作流"""
        try:
            logger.info("开始执行清理工作流...")
            
            # 清理过期的staging记录
            if "messages_staging" in self.db_v2.db.table_names():
                from datetime import timedelta
                expiry_time = datetime.now() - timedelta(hours=24)
                
                deleted_count = self.db_v2.db.execute(
                    "DELETE FROM messages_staging WHERE created_at < ?",
                    [expiry_time.isoformat()]
                ).rowcount
                
                if deleted_count > 0:
                    logger.info(f"✓ 清理过期staging记录: {deleted_count} 条")
            
            # 清理过期的处理日志 (保留最近30天)
            log_expiry_time = datetime.now() - timedelta(days=30)
            deleted_logs = self.db_v2.db.execute(
                "DELETE FROM processing_logs WHERE created_at < ?",
                [log_expiry_time.isoformat()]
            ).rowcount
            
            if deleted_logs > 0:
                logger.info(f"✓ 清理过期处理日志: {deleted_logs} 条")
            
            logger.info("✓ 清理工作流完成")
            
        except Exception as e:
            logger.error(f"执行清理工作流时出错: {e}")
    
    def _log_validation_result(self, result: ValidationResult):
        """记录验证结果"""
        try:
            # 将验证结果记录到处理日志
            batch_id = self.db_v2.generate_batch_id()
            
            validation_summary = {
                "is_valid": result.is_valid,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "errors": result.errors[:10],  # 只记录前10个错误
                "warnings": result.warnings[:10],  # 只记录前10个警告
                "statistics": result.statistics
            }
            
            self.db_v2.log_processing_batch(
                batch_id=batch_id,
                operation_type="validation",
                status="completed" if result.is_valid else "failed",
                records_processed=result.statistics.get("raw_messages", 0),
                error_message="; ".join(result.errors[:3]) if result.errors else None,
                config_snapshot=json.dumps(validation_summary)
            )
            
            logger.info(f"验证结果已记录到批次: {batch_id}")
            
        except Exception as e:
            logger.error(f"记录验证结果时出错: {e}")
    
    def _generate_status_report(self):
        """生成状态报告"""
        try:
            status = self.get_system_status()
            
            logger.info("=== 系统状态报告 ===")
            logger.info(f"原始消息: {status['database']['raw_messages']}")
            logger.info(f"清洁消息: {status['database']['clean_messages']}")
            logger.info(f"未处理消息: {status['database']['unprocessed_messages']}")
            logger.info(f"去重比例: {status['database']['dedup_ratio']:.2%}")
            logger.info(f"已执行去重: {status['workflow_stats']['total_dedups_executed']} 次")
            logger.info(f"已创建备份: {status['workflow_stats']['total_backups_created']} 次")
            logger.info("==================")
            
        except Exception as e:
            logger.error(f"生成状态报告时出错: {e}")
    
    def close(self):
        """关闭工作流管理器"""
        try:
            if self.db_v2:
                self.db_v2.close()
            logger.info("工作流管理器已关闭")
        except Exception as e:
            logger.error(f"关闭工作流管理器时出错: {e}")

# --- 便利函数 ---

def execute_full_workflow() -> bool:
    """执行完整工作流的便利函数"""
    manager = WorkflowManager()
    try:
        return manager.execute_complete_workflow()
    finally:
        manager.close()

def execute_dedup_workflow() -> bool:
    """执行去重工作流的便利函数"""
    manager = WorkflowManager()
    try:
        return manager.execute_deduplication_only()
    finally:
        manager.close()

def get_system_status() -> Dict[str, Any]:
    """获取系统状态的便利函数"""
    manager = WorkflowManager()
    try:
        return manager.get_system_status()
    finally:
        manager.close()

# --- 主程序入口 ---
if __name__ == "__main__":
    print("=== 工作流管理器测试 ===")
    
    try:
        # 测试完整工作流
        success = execute_full_workflow()
        
        if success:
            print("✓ 完整工作流执行成功")
            
            # 显示系统状态
            print("\n系统状态:")
            status = get_system_status()
            for category, data in status.items():
                print(f"  {category}:")
                if isinstance(data, dict):
                    for key, value in data.items():
                        print(f"    {key}: {value}")
                else:
                    print(f"    {data}")
        else:
            print("❌ 完整工作流执行失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise 