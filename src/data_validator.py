"""
数据验证器 v2.0
验证去重过程中的数据完整性和质量
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import logging

from database_v2 import DatabaseV2

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    error_count: int
    warning_count: int
    errors: List[str]
    warnings: List[str]
    statistics: Dict[str, Any]
    
    def add_error(self, message: str):
        """添加错误"""
        self.errors.append(message)
        self.error_count += 1
        self.is_valid = False
        
    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(message)
        self.warning_count += 1

@dataclass
class ValidationConfig:
    """验证配置"""
    check_foreign_keys: bool = True
    check_duplicates: bool = True
    check_data_consistency: bool = True
    check_orphaned_records: bool = True
    max_error_count: int = 100
    max_warning_count: int = 500

class DataValidator:
    """
    数据验证器
    验证数据完整性、一致性和质量
    """
    
    def __init__(self, db_v2: Optional[DatabaseV2] = None, 
                 config: Optional[ValidationConfig] = None):
        """初始化数据验证器"""
        self.db_v2 = db_v2 or DatabaseV2()
        self.config = config or ValidationConfig()
        
        logger.info("数据验证器初始化完成")
    
    def validate_database_integrity(self) -> ValidationResult:
        """
        验证整个数据库的完整性
        """
        logger.info("开始数据库完整性验证...")
        
        result = ValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            errors=[],
            warnings=[],
            statistics={}
        )
        
        try:
            # 1. 验证表结构
            self._validate_table_structure(result)
            
            # 2. 验证外键完整性
            if self.config.check_foreign_keys:
                self._validate_foreign_keys(result)
            
            # 3. 验证重复数据
            if self.config.check_duplicates:
                self._validate_no_duplicates(result)
            
            # 4. 验证数据一致性
            if self.config.check_data_consistency:
                self._validate_data_consistency(result)
            
            # 5. 验证孤立记录
            if self.config.check_orphaned_records:
                self._validate_orphaned_records(result)
            
            # 6. 收集统计信息
            self._collect_database_statistics(result)
            
            logger.info(f"数据库验证完成: 错误 {result.error_count} 个, 警告 {result.warning_count} 个")
            return result
            
        except Exception as e:
            logger.error(f"数据库验证时发生异常: {e}")
            result.add_error(f"验证过程异常: {e}")
            return result
    
    def validate_dedup_operation(self, batch_id: str) -> ValidationResult:
        """
        验证特定去重操作的结果
        """
        logger.info(f"开始验证去重操作: {batch_id}")
        
        result = ValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            errors=[],
            warnings=[],
            statistics={}
        )
        
        try:
            # 1. 验证批次存在
            if not self._validate_batch_exists(batch_id, result):
                return result
            
            # 2. 验证处理状态一致性
            self._validate_processing_status(batch_id, result)
            
            # 3. 验证去重效果
            self._validate_dedup_effectiveness(batch_id, result)
            
            # 4. 验证数据完整性
            self._validate_batch_data_integrity(batch_id, result)
            
            logger.info(f"去重操作验证完成: {batch_id}")
            return result
            
        except Exception as e:
            logger.error(f"验证去重操作时发生异常: {e}")
            result.add_error(f"验证过程异常: {e}")
            return result
    
    def _validate_table_structure(self, result: ValidationResult):
        """验证表结构"""
        try:
            required_tables = [
                "messages_raw", "messages_staging", "messages_clean",
                "processing_logs", "backup_metadata", "jobs", "schema_info"
            ]
            
            existing_tables = self.db_v2.db.table_names()
            
            for table in required_tables:
                if table not in existing_tables:
                    result.add_error(f"缺少必要的表: {table}")
            
            # 验证关键字段
            self._validate_table_columns(result)
            
        except Exception as e:
            result.add_error(f"验证表结构时出错: {e}")
    
    def _validate_table_columns(self, result: ValidationResult):
        """验证表列结构"""
        try:
            # 验证messages_raw表的关键字段
            raw_columns = self.db_v2.db["messages_raw"].columns_dict
            required_raw_columns = [
                "id", "group_name", "sender", "content", 
                "processed_status", "timestamp"
            ]
            
            for col in required_raw_columns:
                if col not in raw_columns:
                    result.add_error(f"messages_raw表缺少字段: {col}")
            
            # 验证messages_clean表的关键字段
            if "messages_clean" in self.db_v2.db.table_names():
                clean_columns = self.db_v2.db["messages_clean"].columns_dict
                required_clean_columns = [
                    "id", "raw_message_id", "group_name", "sender", 
                    "content", "dedup_hash"
                ]
                
                for col in required_clean_columns:
                    if col not in clean_columns:
                        result.add_error(f"messages_clean表缺少字段: {col}")
            
        except Exception as e:
            result.add_error(f"验证表字段时出错: {e}")
    
    def _validate_foreign_keys(self, result: ValidationResult):
        """验证外键完整性"""
        try:
            # 验证messages_clean中的raw_message_id外键
            orphaned_clean = list(self.db_v2.db.execute("""
                SELECT COUNT(*) as count FROM messages_clean c
                LEFT JOIN messages_raw r ON c.raw_message_id = r.id
                WHERE r.id IS NULL
            """))
            
            if orphaned_clean[0][0] > 0:
                result.add_error(f"发现 {orphaned_clean[0][0]} 条clean记录的raw_message_id外键无效")
            
            # 验证jobs中的message_id外键
            if "jobs" in self.db_v2.db.table_names():
                orphaned_jobs = list(self.db_v2.db.execute("""
                    SELECT COUNT(*) as count FROM jobs j
                    LEFT JOIN messages_clean c ON j.message_id = c.id
                    WHERE c.id IS NULL AND j.message_id IS NOT NULL
                """))
                
                if orphaned_jobs[0][0] > 0:
                    result.add_warning(f"发现 {orphaned_jobs[0][0]} 条jobs记录的message_id外键无效")
            
        except Exception as e:
            result.add_error(f"验证外键完整性时出错: {e}")
    
    def _validate_no_duplicates(self, result: ValidationResult):
        """验证无重复数据"""
        try:
            # 检查messages_clean表中的重复哈希值
            duplicate_hashes = list(self.db_v2.db.execute("""
                SELECT dedup_hash, COUNT(*) as count 
                FROM messages_clean 
                GROUP BY dedup_hash 
                HAVING count > 1
            """))
            
            if duplicate_hashes:
                result.add_error(f"发现 {len(duplicate_hashes)} 个重复的去重哈希值")
                
                # 记录前几个重复示例
                for i, (hash_val, count) in enumerate(duplicate_hashes[:5]):
                    result.add_error(f"重复哈希 {hash_val[:16]}... 出现 {count} 次")
            
            # 检查messages_clean表中的内容重复
            content_duplicates = list(self.db_v2.db.execute("""
                SELECT group_name, sender, content, COUNT(*) as count
                FROM messages_clean
                GROUP BY group_name, sender, content
                HAVING count > 1
            """))
            
            if content_duplicates:
                result.add_error(f"发现 {len(content_duplicates)} 组内容重复的记录")
            
        except Exception as e:
            result.add_error(f"验证重复数据时出错: {e}")
    
    def _validate_data_consistency(self, result: ValidationResult):
        """验证数据一致性"""
        try:
            # 验证处理状态一致性
            inconsistent_status = list(self.db_v2.db.execute("""
                SELECT r.id, r.processed_status, 
                       CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END as in_clean
                FROM messages_raw r
                LEFT JOIN messages_clean c ON r.id = c.raw_message_id
                WHERE (r.processed_status = 1 AND c.id IS NULL) 
                   OR (r.processed_status = 0 AND c.id IS NOT NULL)
            """))
            
            if inconsistent_status:
                result.add_error(f"发现 {len(inconsistent_status)} 条消息的处理状态不一致")
            
            # 验证时间戳合理性
            invalid_timestamps = list(self.db_v2.db.execute("""
                SELECT COUNT(*) as count FROM messages_raw
                WHERE timestamp > datetime('now') 
                   OR timestamp < datetime('2020-01-01')
            """))
            
            if invalid_timestamps[0][0] > 0:
                result.add_warning(f"发现 {invalid_timestamps[0][0]} 条消息的时间戳异常")
            
        except Exception as e:
            result.add_error(f"验证数据一致性时出错: {e}")
    
    def _validate_orphaned_records(self, result: ValidationResult):
        """验证孤立记录"""
        try:
            # 检查staging表中的孤立记录
            if "messages_staging" in self.db_v2.db.table_names():
                orphaned_staging = list(self.db_v2.db.execute("""
                    SELECT COUNT(*) as count FROM messages_staging s
                    LEFT JOIN messages_raw r ON s.raw_message_id = r.id
                    WHERE r.id IS NULL
                """))
                
                if orphaned_staging[0][0] > 0:
                    result.add_warning(f"发现 {orphaned_staging[0][0]} 条staging表的孤立记录")
            
            # 检查过期的staging记录
            expiry_time = datetime.now() - timedelta(hours=24)
            expired_staging = list(self.db_v2.db.execute("""
                SELECT COUNT(*) as count FROM messages_staging
                WHERE created_at < ?
            """, [expiry_time.isoformat()]))
            
            if expired_staging[0][0] > 0:
                result.add_warning(f"发现 {expired_staging[0][0]} 条过期的staging记录")
            
        except Exception as e:
            result.add_error(f"验证孤立记录时出错: {e}")
    
    def _validate_batch_exists(self, batch_id: str, result: ValidationResult) -> bool:
        """验证批次是否存在"""
        try:
            batch_logs = list(self.db_v2.db.execute("""
                SELECT * FROM processing_logs 
                WHERE batch_id = ? AND operation_type = 'dedup'
            """, [batch_id]))
            
            if not batch_logs:
                result.add_error(f"找不到批次: {batch_id}")
                return False
            
            return True
            
        except Exception as e:
            result.add_error(f"验证批次存在性时出错: {e}")
            return False
    
    def _validate_processing_status(self, batch_id: str, result: ValidationResult):
        """验证处理状态"""
        try:
            # 检查该批次处理的消息状态
            batch_messages = list(self.db_v2.db.execute("""
                SELECT r.id, r.processed_status, c.id as clean_id
                FROM messages_raw r
                LEFT JOIN messages_clean c ON r.id = c.raw_message_id 
                                             AND c.processed_batch_id = ?
                WHERE r.updated_at >= (
                    SELECT created_at FROM processing_logs 
                    WHERE batch_id = ? AND operation_type = 'dedup' 
                    ORDER BY created_at DESC LIMIT 1
                )
            """, [batch_id, batch_id]))
            
            for msg_id, status, clean_id in batch_messages:
                if status == 1 and clean_id is None:
                    result.add_error(f"消息 {msg_id} 标记为已处理但不在clean表中")
                elif status == 0 and clean_id is not None:
                    result.add_error(f"消息 {msg_id} 未标记为已处理但在clean表中")
            
        except Exception as e:
            result.add_error(f"验证处理状态时出错: {e}")
    
    def _validate_dedup_effectiveness(self, batch_id: str, result: ValidationResult):
        """验证去重效果"""
        try:
            # 检查该批次是否有效去重
            batch_stats = list(self.db_v2.db.execute("""
                SELECT 
                    COUNT(*) as total_processed,
                    COUNT(DISTINCT c.dedup_hash) as unique_hashes
                FROM messages_clean c
                WHERE c.processed_batch_id = ?
            """, [batch_id]))
            
            if batch_stats:
                total, unique = batch_stats[0]
                if total != unique:
                    result.add_error(f"批次 {batch_id} 去重不完整: {total} 条记录, {unique} 个唯一哈希")
            
        except Exception as e:
            result.add_error(f"验证去重效果时出错: {e}")
    
    def _validate_batch_data_integrity(self, batch_id: str, result: ValidationResult):
        """验证批次数据完整性"""
        try:
            # 验证该批次的所有记录都有有效的哈希值
            invalid_hashes = list(self.db_v2.db.execute("""
                SELECT COUNT(*) as count FROM messages_clean
                WHERE processed_batch_id = ? 
                  AND (dedup_hash IS NULL OR dedup_hash = '')
            """, [batch_id]))
            
            if invalid_hashes[0][0] > 0:
                result.add_error(f"批次 {batch_id} 中有 {invalid_hashes[0][0]} 条记录的去重哈希无效")
            
        except Exception as e:
            result.add_error(f"验证批次数据完整性时出错: {e}")
    
    def _collect_database_statistics(self, result: ValidationResult):
        """收集数据库统计信息"""
        try:
            stats = {}
            
            # 基本统计
            stats["raw_messages"] = self.db_v2.db["messages_raw"].count
            stats["clean_messages"] = self.db_v2.db["messages_clean"].count
            stats["processing_logs"] = self.db_v2.db["processing_logs"].count
            
            # 处理状态统计
            status_stats = list(self.db_v2.db.execute("""
                SELECT processed_status, COUNT(*) as count
                FROM messages_raw
                GROUP BY processed_status
            """))
            
            for status, count in status_stats:
                stats[f"raw_status_{status}"] = count
            
            # 去重效率统计
            if stats["raw_messages"] > 0:
                stats["dedup_ratio"] = stats["clean_messages"] / stats["raw_messages"]
            else:
                stats["dedup_ratio"] = 0.0
            
            # 最近处理情况
            recent_batches = list(self.db_v2.db.execute("""
                SELECT COUNT(*) as count FROM processing_logs
                WHERE operation_type = 'dedup' 
                  AND created_at > datetime('now', '-24 hours')
            """))
            
            stats["recent_batches_24h"] = recent_batches[0][0] if recent_batches else 0
            
            result.statistics = stats
            
        except Exception as e:
            result.add_warning(f"收集统计信息时出错: {e}")
    
    def generate_validation_report(self, result: ValidationResult) -> str:
        """生成验证报告"""
        report_lines = []
        
        # 报告头
        report_lines.append("=" * 60)
        report_lines.append("数据验证报告")
        report_lines.append("=" * 60)
        report_lines.append(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"总体状态: {'通过' if result.is_valid else '失败'}")
        report_lines.append(f"错误数量: {result.error_count}")
        report_lines.append(f"警告数量: {result.warning_count}")
        report_lines.append("")
        
        # 错误详情
        if result.errors:
            report_lines.append("错误详情:")
            report_lines.append("-" * 40)
            for i, error in enumerate(result.errors, 1):
                report_lines.append(f"{i}. {error}")
            report_lines.append("")
        
        # 警告详情
        if result.warnings:
            report_lines.append("警告详情:")
            report_lines.append("-" * 40)
            for i, warning in enumerate(result.warnings, 1):
                report_lines.append(f"{i}. {warning}")
            report_lines.append("")
        
        # 统计信息
        if result.statistics:
            report_lines.append("数据库统计:")
            report_lines.append("-" * 40)
            for key, value in result.statistics.items():
                report_lines.append(f"{key}: {value}")
            report_lines.append("")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)

# --- 便利函数 ---

def validate_database() -> ValidationResult:
    """验证数据库的便利函数"""
    validator = DataValidator()
    return validator.validate_database_integrity()

def validate_dedup_batch(batch_id: str) -> ValidationResult:
    """验证去重批次的便利函数"""
    validator = DataValidator()
    return validator.validate_dedup_operation(batch_id)

def generate_health_check_report() -> str:
    """生成数据库健康检查报告"""
    validator = DataValidator()
    result = validator.validate_database_integrity()
    return validator.generate_validation_report(result)

# --- 主程序入口 ---
if __name__ == "__main__":
    # 测试数据验证器
    print("=== 数据验证器测试 ===")
    
    try:
        # 执行完整的数据库验证
        result = validate_database()
        
        print(f"验证结果: {'通过' if result.is_valid else '失败'}")
        print(f"错误: {result.error_count} 个")
        print(f"警告: {result.warning_count} 个")
        
        if result.errors:
            print("\n错误详情:")
            for error in result.errors[:5]:  # 只显示前5个错误
                print(f"  - {error}")
        
        if result.warnings:
            print("\n警告详情:")
            for warning in result.warnings[:5]:  # 只显示前5个警告
                print(f"  - {warning}")
        
        # 生成完整报告
        print("\n生成完整验证报告...")
        validator = DataValidator()
        report = validator.generate_validation_report(result)
        
        # 保存报告到文件
        report_path = Path(__file__).parent.parent / "reports" / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✓ 验证报告已保存: {report_path}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise 