"""
微信监听器数据迁移工具 v2.0
从旧架构(v1.0)安全迁移到新架构(v2.0)
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable
import logging
from dataclasses import dataclass
import time

from database_v2 import DatabaseV2
from backup_manager import BackupManager

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class MigrationConfig:
    """迁移配置类"""
    batch_size: int = 1000
    verify_after_migration: bool = True
    create_backup_before_migration: bool = True
    preserve_original_data: bool = True
    migration_timeout_seconds: int = 3600
    progress_callback: Optional[Callable] = None

class MigrationProgress:
    """迁移进度跟踪"""
    def __init__(self):
        self.total_records = 0
        self.processed_records = 0
        self.migrated_records = 0
        self.failed_records = 0
        self.start_time = None
        self.current_table = ""
        self.current_batch = 0
        
    def update_progress(self, processed: int, migrated: int = 0, failed: int = 0):
        """更新进度"""
        self.processed_records += processed
        self.migrated_records += migrated
        self.failed_records += failed
        
    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100
    
    def get_eta_seconds(self) -> Optional[float]:
        """估算剩余时间"""
        if not self.start_time or self.processed_records == 0:
            return None
        
        elapsed = time.time() - self.start_time
        rate = self.processed_records / elapsed
        remaining = self.total_records - self.processed_records
        
        return remaining / rate if rate > 0 else None

class DataMigrator:
    """
    数据迁移器
    负责从v1.0架构迁移到v2.0架构
    """
    
    def __init__(self, source_db_path: Optional[Path] = None, 
                 target_db_path: Optional[Path] = None,
                 config: Optional[MigrationConfig] = None):
        """初始化迁移器"""
        self.config = config or MigrationConfig()
        
        # 数据库路径
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        
        self.source_db_path = source_db_path or (data_dir / "wechat_jds.db")
        self.target_db_path = target_db_path or (data_dir / "wechat_jds.db")
        
        # 初始化组件
        self.backup_manager = BackupManager()
        self.progress = MigrationProgress()
        
        logger.info(f"迁移器初始化完成")
        logger.info(f"源数据库: {self.source_db_path}")
        logger.info(f"目标数据库: {self.target_db_path}")
    
    def check_migration_required(self) -> bool:
        """检查是否需要迁移"""
        try:
            # 检查数据库版本
            db_v2 = DatabaseV2(self.target_db_path)
            current_version = db_v2.get_db_version()
            db_v2.close()
            
            if current_version == "2.0":
                logger.info("数据库已经是v2.0版本，无需迁移")
                return False
            
            logger.info(f"检测到数据库版本 {current_version}，需要迁移到v2.0")
            return True
            
        except Exception as e:
            logger.error(f"检查迁移需求时出错: {e}")
            return True  # 出错时假设需要迁移
    
    def analyze_source_data(self) -> Dict[str, int]:
        """分析源数据库，统计各表数据量"""
        try:
            conn = sqlite3.connect(str(self.source_db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall()]
            
            analysis = {}
            total_records = 0
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM [{table}]")
                count = cursor.fetchone()['count']
                analysis[table] = count
                total_records += count
                
            analysis['_total'] = total_records
            self.progress.total_records = total_records
            
            conn.close()
            
            logger.info("源数据分析完成:")
            for table, count in analysis.items():
                if table != '_total':
                    logger.info(f"  {table}: {count} 条记录")
            logger.info(f"  总计: {total_records} 条记录")
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析源数据时出错: {e}")
            return {}
    
    def execute_migration(self) -> bool:
        """
        执行完整的数据迁移流程
        """
        logger.info("=== 开始数据迁移流程 ===")
        self.progress.start_time = time.time()
        
        try:
            # 1. 检查是否需要迁移
            if not self.check_migration_required():
                return True
            
            # 2. 分析源数据
            source_analysis = self.analyze_source_data()
            if not source_analysis:
                logger.error("源数据分析失败，迁移中止")
                return False
            
            # 3. 创建迁移前备份
            if self.config.create_backup_before_migration:
                logger.info("创建迁移前备份...")
                backup_path = self.backup_manager.create_automatic_backup("migration")
                if not backup_path:
                    logger.error("创建迁移前备份失败，迁移中止")
                    return False
                logger.info(f"✓ 迁移前备份创建成功: {backup_path}")
            
            # 4. 初始化目标数据库v2.0架构
            logger.info("初始化目标数据库v2.0架构...")
            target_db = DatabaseV2(self.target_db_path)
            target_db.setup_database_v2()
            
            # 5. 迁移数据
            logger.info("开始迁移数据...")
            migration_success = self._migrate_all_tables(target_db)
            
            if not migration_success:
                logger.error("数据迁移失败")
                target_db.close()
                return False
            
            # 6. 验证迁移结果
            if self.config.verify_after_migration:
                logger.info("验证迁移结果...")
                verification_success = self._verify_migration(target_db)
                if not verification_success:
                    logger.error("迁移验证失败")
                    target_db.close()
                    return False
            
            target_db.close()
            
            # 7. 记录迁移完成
            self._log_migration_completion()
            
            logger.info("=== 数据迁移流程完成 ===")
            return True
            
        except Exception as e:
            logger.error(f"数据迁移过程中发生错误: {e}")
            return False
    
    def _migrate_all_tables(self, target_db: DatabaseV2) -> bool:
        """迁移所有表的数据"""
        try:
            # 连接源数据库
            source_conn = sqlite3.connect(str(self.source_db_path))
            source_conn.row_factory = sqlite3.Row
            
            # 迁移messages表到messages_raw
            success = self._migrate_messages_table(source_conn, target_db)
            if not success:
                source_conn.close()
                return False
            
            # 迁移jobs表
            success = self._migrate_jobs_table(source_conn, target_db)
            if not success:
                source_conn.close()
                return False
            
            source_conn.close()
            return True
            
        except Exception as e:
            logger.error(f"迁移表数据时出错: {e}")
            return False
    
    def _migrate_messages_table(self, source_conn: sqlite3.Connection, target_db: DatabaseV2) -> bool:
        """迁移messages表到messages_raw"""
        try:
            self.progress.current_table = "messages"
            logger.info("开始迁移messages表到messages_raw...")
            
            cursor = source_conn.cursor()
            
            # 获取总记录数
            cursor.execute("SELECT COUNT(*) as count FROM messages")
            total_count = cursor.fetchone()['count']
            
            if total_count == 0:
                logger.info("messages表为空，跳过迁移")
                return True
            
            # 分批迁移
            batch_num = 0
            offset = 0
            migrated_count = 0
            
            while offset < total_count:
                batch_num += 1
                self.progress.current_batch = batch_num
                
                # 获取一批数据
                cursor.execute("""
                    SELECT * FROM messages 
                    ORDER BY id 
                    LIMIT ? OFFSET ?
                """, [self.config.batch_size, offset])
                
                batch_records = cursor.fetchall()
                
                if not batch_records:
                    break
                
                # 迁移当前批次
                batch_migrated = self._migrate_messages_batch(batch_records, target_db)
                migrated_count += batch_migrated
                
                # 更新进度
                self.progress.update_progress(
                    processed=len(batch_records),
                    migrated=batch_migrated,
                    failed=len(batch_records) - batch_migrated
                )
                
                # 调用进度回调
                if self.config.progress_callback:
                    self.config.progress_callback(self.progress)
                
                progress_pct = self.progress.get_progress_percentage()
                logger.info(f"迁移进度: {progress_pct:.1f}% ({migrated_count}/{total_count})")
                
                offset += self.config.batch_size
            
            logger.info(f"✓ messages表迁移完成，共迁移 {migrated_count} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"迁移messages表时出错: {e}")
            return False
    
    def _migrate_messages_batch(self, records: List[sqlite3.Row], target_db: DatabaseV2) -> int:
        """迁移一批messages记录"""
        migrated_count = 0
        
        for record in records:
            try:
                # 将旧记录迁移到messages_raw
                message_id = target_db.save_raw_message(
                    group_name=record.get('group_name', ''),
                    sender=record.get('sender', ''),
                    content=record.get('content', ''),
                    msg_type=record.get('msg_type', 'Text')
                )
                
                if message_id:
                    migrated_count += 1
                    
                    # 如果原记录已处理，同时添加到clean表
                    if record.get('processed', 0) == 1:
                        self._add_to_clean_table(record, message_id, target_db)
                        
            except Exception as e:
                logger.error(f"迁移单条消息记录时出错: {e}")
                continue
        
        return migrated_count
    
    def _add_to_clean_table(self, record: sqlite3.Row, raw_message_id: int, target_db: DatabaseV2):
        """将已处理的记录添加到clean表"""
        try:
            now = datetime.now().isoformat()
            
            # 生成去重哈希
            dedup_hash = target_db.generate_dedup_hash(
                record.get('group_name', ''),
                record.get('sender', ''),
                record.get('content', '')
            )
            
            clean_data = {
                "raw_message_id": raw_message_id,
                "staging_message_id": raw_message_id,  # 临时使用相同ID
                "group_name": record.get('group_name', ''),
                "sender": record.get('sender', ''),
                "content": record.get('content', ''),
                "msg_type": record.get('msg_type', 'Text'),
                "timestamp": record.get('timestamp', now),
                "dedup_hash": dedup_hash,
                "processed_batch_id": "migration_v1_to_v2",
                "quality_score": 1.0,
                "created_at": now,
                "updated_at": now
            }
            
            target_db.db["messages_clean"].insert(clean_data)
            
        except Exception as e:
            logger.debug(f"添加到clean表时出错（可能是重复记录）: {e}")
    
    def _migrate_jobs_table(self, source_conn: sqlite3.Connection, target_db: DatabaseV2) -> bool:
        """迁移jobs表"""
        try:
            self.progress.current_table = "jobs"
            logger.info("开始迁移jobs表...")
            
            cursor = source_conn.cursor()
            
            # 检查jobs表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
            if not cursor.fetchone():
                logger.info("jobs表不存在，跳过迁移")
                return True
            
            # 获取所有jobs记录
            cursor.execute("SELECT * FROM jobs")
            jobs = cursor.fetchall()
            
            if not jobs:
                logger.info("jobs表为空，跳过迁移")
                return True
            
            migrated_count = 0
            for job in jobs:
                try:
                    # 迁移job记录
                    job_data = {
                        "message_id": job.get('message_id'),
                        "raw_message_id": job.get('message_id'),  # 初始设为相同
                        "company": job.get('company', ''),
                        "position": job.get('position', ''),
                        "location": job.get('location', ''),
                        "contact_email": job.get('contact_email', ''),
                        "resume_format": job.get('resume_format', ''),
                        "email_subject_format": job.get('email_subject_format', ''),
                        "full_text": job.get('full_text', ''),
                        "extraction_confidence": 0.8,  # 默认置信度
                        "parsed_at": job.get('parsed_at', datetime.now().isoformat()),
                        "created_at": datetime.now().isoformat()
                    }
                    
                    target_db.db["jobs"].insert(job_data)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"迁移单条job记录时出错: {e}")
                    continue
            
            logger.info(f"✓ jobs表迁移完成，共迁移 {migrated_count} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"迁移jobs表时出错: {e}")
            return False
    
    def _verify_migration(self, target_db: DatabaseV2) -> bool:
        """验证迁移结果"""
        try:
            logger.info("开始验证迁移结果...")
            
            # 连接源数据库进行对比
            source_conn = sqlite3.connect(str(self.source_db_path))
            source_conn.row_factory = sqlite3.Row
            cursor = source_conn.cursor()
            
            # 验证messages表迁移
            cursor.execute("SELECT COUNT(*) as count FROM messages")
            source_messages_count = cursor.fetchone()['count']
            
            target_raw_count = target_db.db["messages_raw"].count
            
            if source_messages_count != target_raw_count:
                logger.error(f"messages迁移验证失败: 源{source_messages_count} != 目标{target_raw_count}")
                source_conn.close()
                return False
            
            # 验证jobs表迁移
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) as count FROM jobs")
                source_jobs_count = cursor.fetchone()['count']
                target_jobs_count = target_db.db["jobs"].count
                
                if source_jobs_count != target_jobs_count:
                    logger.error(f"jobs迁移验证失败: 源{source_jobs_count} != 目标{target_jobs_count}")
                    source_conn.close()
                    return False
            
            source_conn.close()
            
            logger.info("✓ 迁移验证通过")
            return True
            
        except Exception as e:
            logger.error(f"验证迁移时出错: {e}")
            return False
    
    def _log_migration_completion(self):
        """记录迁移完成日志"""
        try:
            target_db = DatabaseV2(self.target_db_path)
            
            # 生成迁移报告
            migration_report = {
                "migration_type": "v1_to_v2",
                "total_records_processed": self.progress.processed_records,
                "total_records_migrated": self.progress.migrated_records,
                "total_records_failed": self.progress.failed_records,
                "execution_time_seconds": time.time() - self.progress.start_time,
                "completed_at": datetime.now().isoformat()
            }
            
            # 记录到处理日志
            batch_id = target_db.generate_batch_id()
            target_db.log_processing_batch(
                batch_id=batch_id,
                operation_type="migrate",
                status="completed",
                records_processed=self.progress.processed_records,
                records_affected=self.progress.migrated_records,
                execution_time_ms=int((time.time() - self.progress.start_time) * 1000),
                config_snapshot=json.dumps(migration_report)
            )
            
            target_db.close()
            
            logger.info(f"迁移完成统计:")
            logger.info(f"  处理记录数: {self.progress.processed_records}")
            logger.info(f"  迁移成功: {self.progress.migrated_records}")
            logger.info(f"  迁移失败: {self.progress.failed_records}")
            logger.info(f"  执行时间: {migration_report['execution_time_seconds']:.2f}秒")
            
        except Exception as e:
            logger.error(f"记录迁移完成日志时出错: {e}")

# --- 便利函数 ---

def migrate_database(source_db_path: Optional[Path] = None, 
                    target_db_path: Optional[Path] = None,
                    progress_callback: Optional[Callable] = None) -> bool:
    """执行数据库迁移的便利函数"""
    config = MigrationConfig(progress_callback=progress_callback)
    migrator = DataMigrator(source_db_path, target_db_path, config)
    return migrator.execute_migration()

def print_migration_progress(progress: MigrationProgress):
    """打印迁移进度的回调函数"""
    pct = progress.get_progress_percentage()
    eta = progress.get_eta_seconds()
    
    eta_str = f"，预计剩余 {eta:.0f}秒" if eta else ""
    print(f"迁移进度: {pct:.1f}% ({progress.processed_records}/{progress.total_records}){eta_str}")

# --- 主程序入口 ---
if __name__ == "__main__":
    # 测试数据迁移
    print("=== 数据迁移工具测试 ===")
    
    # 设置进度回调
    def progress_callback(progress: MigrationProgress):
        print_migration_progress(progress)
    
    try:
        success = migrate_database(progress_callback=progress_callback)
        
        if success:
            print("✓ 数据迁移测试完成")
        else:
            print("❌ 数据迁移测试失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise 