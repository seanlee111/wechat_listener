"""
微信监听器安全数据库架构 v2.0
支持分层存储、安全去重、备份恢复和向后兼容
"""

import sqlite_utils
import sqlite3
import hashlib
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 配置 ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "wechat_jds.db"

# 数据库版本
DB_VERSION = "2.0"
SCHEMA_VERSION = 2

class DatabaseV2:
    """
    微信监听器安全数据库管理器 v2.0
    实现分层存储、安全去重、备份恢复等功能
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """初始化数据库连接"""
        self.db_path = db_path or DB_FILE
        self.db = None
        self._initialize_connection()
        
    def _initialize_connection(self):
        """初始化数据库连接"""
        try:
            # 创建带超时的原生连接
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            # 启用WAL模式提升并发性能
            conn.execute("PRAGMA journal_mode = WAL")
            # 使用sqlite-utils包装
            self.db = sqlite_utils.Database(conn)
            logger.info(f"数据库连接已建立: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def get_db_version(self) -> str:
        """获取数据库版本"""
        try:
            if "schema_info" in self.db.table_names():
                info = self.db["schema_info"].get(1)
                return info.get("version", "1.0")
            return "1.0"  # 默认为旧版本
        except:
            return "1.0"
    
    def setup_database_v2(self):
        """
        初始化v2数据库架构
        包含所有新表和索引
        """
        logger.info("开始初始化数据库架构 v2.0...")
        
        try:
            # 1. 创建架构信息表
            self._create_schema_info_table()
            
            # 2. 创建原始数据表
            self._create_messages_raw_table()
            
            # 3. 创建处理缓存表
            self._create_messages_staging_table()
            
            # 4. 创建清洁数据表
            self._create_messages_clean_table()
            
            # 5. 创建处理日志表
            self._create_processing_logs_table()
            
            # 6. 创建备份元数据表
            self._create_backup_metadata_table()
            
            # 7. 保持jobs表兼容性
            self._ensure_jobs_table_compatibility()
            
            # 8. 创建向后兼容视图
            self._create_compatibility_views()
            
            # 9. 创建所有索引
            self._create_all_indexes()
            
            # 10. 更新架构版本
            self._update_schema_version()
            
            logger.info("数据库架构 v2.0 初始化完成！")
            return True
            
        except Exception as e:
            logger.error(f"数据库架构初始化失败: {e}")
            raise
    
    def _create_schema_info_table(self):
        """创建架构信息表"""
        self.db["schema_info"].create({
            "id": int,
            "version": str,
            "schema_version": int,
            "created_at": str,
            "updated_at": str,
            "migration_history": str  # JSON格式的迁移历史
        }, pk="id", if_not_exists=True)
        
        logger.info("✓ 架构信息表创建完成")
    
    def _create_messages_raw_table(self):
        """创建原始数据表 - 永不删除的数据存储"""
        self.db["messages_raw"].create({
            "id": int,
            "group_name": str,
            "sender": str,
            "content": str,
            "msg_type": str,
            "timestamp": str,
            "captured_at": str,
            "processed_status": int,  # 0:未处理 1:已处理 2:处理失败 3:跳过
            "processing_attempts": int,
            "last_processing_attempt": str,
            "processing_error": str,
            "created_at": str,
            "updated_at": str
        }, pk="id", if_not_exists=True)
        
        logger.info("✓ 原始数据表 messages_raw 创建完成")
    
    def _create_messages_staging_table(self):
        """创建处理缓存表 - 临时处理数据"""
        self.db["messages_staging"].create({
            "id": int,
            "raw_message_id": int,
            "group_name": str,
            "sender": str,
            "content": str,
            "msg_type": str,
            "timestamp": str,
            "dedup_hash": str,
            "processing_batch_id": str,
            "batch_sequence": int,
            "validation_status": str,  # 'pending', 'valid', 'invalid', 'duplicate'
            "created_at": str
        }, pk="id", if_not_exists=True,
        foreign_keys=[("raw_message_id", "messages_raw", "id")])
        
        logger.info("✓ 处理缓存表 messages_staging 创建完成")
    
    def _create_messages_clean_table(self):
        """创建清洁数据表 - 最终的去重数据"""
        self.db["messages_clean"].create({
            "id": int,
            "raw_message_id": int,
            "staging_message_id": int,  # 允许为NULL
            "group_name": str,
            "sender": str,
            "content": str,
            "msg_type": str,
            "timestamp": str,
            "dedup_hash": str,
            "processed_batch_id": str,
            "quality_score": float,  # 数据质量评分
            "created_at": str,
            "updated_at": str
        }, pk="id", if_not_exists=True,
        foreign_keys=[
            ("raw_message_id", "messages_raw", "id")
            # 移除staging_message_id的外键约束，允许为NULL
        ])
        
        # 添加唯一性约束
        try:
            self.db["messages_clean"].create_index(
                ["group_name", "sender", "content"], 
                unique=True, 
                if_not_exists=True
            )
        except:
            pass  # 索引可能已存在
        
        logger.info("✓ 清洁数据表 messages_clean 创建完成")
    
    def _create_processing_logs_table(self):
        """创建处理日志表"""
        self.db["processing_logs"].create({
            "id": int,
            "batch_id": str,
            "operation_type": str,  # 'dedup', 'backup', 'migrate', 'cleanup'
            "status": str,  # 'started', 'completed', 'failed', 'cancelled'
            "records_processed": int,
            "records_affected": int,
            "records_added": int,
            "records_updated": int,
            "records_deleted": int,
            "error_message": str,
            "execution_time_ms": int,
            "memory_usage_mb": float,
            "config_snapshot": str,  # JSON格式的配置快照
            "created_at": str,
            "completed_at": str
        }, pk="id", if_not_exists=True)
        
        logger.info("✓ 处理日志表 processing_logs 创建完成")
    
    def _create_backup_metadata_table(self):
        """创建备份元数据表"""
        self.db["backup_metadata"].create({
            "id": int,
            "backup_file_path": str,
            "backup_type": str,  # 'auto', 'manual', 'pre-operation', 'scheduled'
            "source_tables": str,  # JSON格式的表名列表
            "record_count": int,
            "file_size_bytes": int,
            "checksum": str,
            "compression_ratio": float,
            "backup_status": str,  # 'creating', 'completed', 'failed', 'corrupted'
            "restoration_tested": bool,
            "created_at": str,
            "expiry_date": str,
            "restored_at": str,
            "notes": str
        }, pk="id", if_not_exists=True)
        
        logger.info("✓ 备份元数据表 backup_metadata 创建完成")
    
    def _ensure_jobs_table_compatibility(self):
        """确保jobs表与新架构兼容"""
        jobs_table = self.db["jobs"]
        
        # 检查是否存在，不存在则创建
        if "jobs" not in self.db.table_names():
            jobs_table.create({
                "id": int,
                "message_id": int,  # 将关联到messages_clean表
                "raw_message_id": int,  # 新增：关联到原始消息
                "company": str,
                "position": str,
                "location": str,
                "contact_email": str,
                "resume_format": str,
                "email_subject_format": str,
                "full_text": str,
                "extraction_confidence": float,  # 新增：提取置信度
                "parsed_at": str,
                "created_at": str
            }, pk="id", if_not_exists=True)
        else:
            # 添加新字段到现有表
            columns = jobs_table.columns_dict
            if "raw_message_id" not in columns:
                try:
                    jobs_table.add_column("raw_message_id", int)
                    logger.info("✓ jobs表添加raw_message_id字段")
                except:
                    pass
            
            if "extraction_confidence" not in columns:
                try:
                    jobs_table.add_column("extraction_confidence", float, fk=None)
                    logger.info("✓ jobs表添加extraction_confidence字段")
                except:
                    pass
        
        logger.info("✓ jobs表兼容性检查完成")
    
    def _create_compatibility_views(self):
        """创建向后兼容视图"""
        try:
            # 创建messages视图，映射到messages_clean表
            self.db.execute("""
                CREATE VIEW IF NOT EXISTS messages AS
                SELECT 
                    id,
                    group_name,
                    sender,
                    content,
                    msg_type,
                    timestamp,
                    1 as processed  -- 在clean表中的都是已处理的
                FROM messages_clean
                ORDER BY id
            """)
            
            logger.info("✓ 向后兼容视图 messages 创建完成")
            
        except Exception as e:
            logger.warning(f"创建兼容视图时出现警告: {e}")
    
    def _create_all_indexes(self):
        """创建所有必要的索引"""
        logger.info("开始创建数据库索引...")
        
        # messages_raw表索引
        indexes_raw = [
            (["group_name"], False),
            (["sender"], False),
            (["processed_status"], False),
            (["captured_at"], False),
            (["group_name", "sender"], False),
            (["processed_status", "captured_at"], False)
        ]
        
        for cols, unique in indexes_raw:
            try:
                self.db["messages_raw"].create_index(cols, unique=unique, if_not_exists=True)
            except:
                pass
        
        # messages_staging表索引
        indexes_staging = [
            (["raw_message_id"], False),
            (["processing_batch_id"], False),
            (["dedup_hash"], False),
            (["validation_status"], False),
            (["processing_batch_id", "batch_sequence"], False)
        ]
        
        for cols, unique in indexes_staging:
            try:
                self.db["messages_staging"].create_index(cols, unique=unique, if_not_exists=True)
            except:
                pass
        
        # messages_clean表索引
        indexes_clean = [
            (["raw_message_id"], False),
            (["processed_batch_id"], False),
            (["dedup_hash"], True),  # 唯一索引
            (["group_name"], False),
            (["sender"], False),
            (["timestamp"], False)
        ]
        
        for cols, unique in indexes_clean:
            try:
                self.db["messages_clean"].create_index(cols, unique=unique, if_not_exists=True)
            except:
                pass
        
        # processing_logs表索引
        try:
            self.db["processing_logs"].create_index(["batch_id"], if_not_exists=True)
            self.db["processing_logs"].create_index(["operation_type", "status"], if_not_exists=True)
            self.db["processing_logs"].create_index(["created_at"], if_not_exists=True)
        except:
            pass
        
        # backup_metadata表索引
        try:
            self.db["backup_metadata"].create_index(["backup_type"], if_not_exists=True)
            self.db["backup_metadata"].create_index(["created_at"], if_not_exists=True)
            self.db["backup_metadata"].create_index(["backup_status"], if_not_exists=True)
        except:
            pass
        
        logger.info("✓ 数据库索引创建完成")
    
    def _update_schema_version(self):
        """更新架构版本信息"""
        now = datetime.now().isoformat()
        migration_history = {
            "v2.0_migration": {
                "timestamp": now,
                "description": "升级到安全去重架构v2.0",
                "tables_added": [
                    "messages_raw", "messages_staging", "messages_clean",
                    "processing_logs", "backup_metadata", "schema_info"
                ]
            }
        }
        
        # 插入或更新版本信息
        try:
            self.db["schema_info"].insert({
                "id": 1,
                "version": DB_VERSION,
                "schema_version": SCHEMA_VERSION,
                "created_at": now,
                "updated_at": now,
                "migration_history": json.dumps(migration_history)
            }, replace=True)
            
            logger.info(f"✓ 数据库版本更新为 {DB_VERSION}")
        except Exception as e:
            logger.error(f"更新版本信息失败: {e}")
    
    # --- 数据操作方法 ---
    
    def save_raw_message(self, group_name: str, sender: str, content: str, msg_type: str) -> int:
        """
        保存原始消息到messages_raw表
        返回消息ID
        """
        now = datetime.now().isoformat()
        
        message_data = {
            "group_name": group_name,
            "sender": sender,
            "content": content,
            "msg_type": str(msg_type),
            "timestamp": now,
            "captured_at": now,
            "processed_status": 0,  # 未处理
            "processing_attempts": 0,
            "created_at": now,
            "updated_at": now
        }
        
        try:
            result = self.db["messages_raw"].insert(message_data)
            message_id = result.last_pk
            logger.debug(f"原始消息已保存: ID={message_id}, 群={group_name}, 发送者={sender}")
            return message_id
        except Exception as e:
            logger.error(f"保存原始消息失败: {e}")
            raise
    
    def get_unprocessed_raw_messages(self, limit: int = 1000) -> List[Dict]:
        """获取未处理的原始消息"""
        try:
            messages = list(self.db["messages_raw"].rows_where(
                "processed_status = 0", 
                limit=limit,
                order_by="id"
            ))
            logger.info(f"获取到 {len(messages)} 条未处理消息")
            return messages
        except Exception as e:
            logger.error(f"获取未处理消息失败: {e}")
            return []
    
    def generate_dedup_hash(self, group_name: str, sender: str, content: str) -> str:
        """生成去重哈希值"""
        # 标准化内容用于去重
        normalized_content = content.strip().lower()
        hash_string = f"{group_name}|{sender}|{normalized_content}"
        return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
    
    def generate_batch_id(self) -> str:
        """生成批次ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        uuid_part = str(uuid.uuid4())[:8]
        return f"batch_{timestamp}_{uuid_part}"
    
    def log_processing_batch(self, batch_id: str, operation_type: str, 
                           status: str, **kwargs) -> int:
        """记录处理批次日志"""
        now = datetime.now().isoformat()
        
        log_data = {
            "batch_id": batch_id,
            "operation_type": operation_type,
            "status": status,
            "created_at": now,
            **kwargs
        }
        
        if status == "completed":
            log_data["completed_at"] = now
        
        try:
            result = self.db["processing_logs"].insert(log_data)
            return result.last_pk
        except Exception as e:
            logger.error(f"记录处理日志失败: {e}")
            return 0
    
    def close(self):
        """关闭数据库连接"""
        if self.db and hasattr(self.db, 'close'):
            self.db.close()
            logger.info("数据库连接已关闭")

# --- 向后兼容函数 ---

def save_message(group_name: str, sender: str, content: str, msg_type: str):
    """
    向后兼容的消息保存函数
    内部调用新的save_raw_message方法
    """
    db_v2 = DatabaseV2()
    try:
        return db_v2.save_raw_message(group_name, sender, content, msg_type)
    finally:
        db_v2.close()

def get_db():
    """向后兼容的数据库获取函数"""
    db_v2 = DatabaseV2()
    return db_v2.db

def setup_database():
    """向后兼容的数据库初始化函数"""
    db_v2 = DatabaseV2()
    try:
        current_version = db_v2.get_db_version()
        if current_version == "1.0":
            logger.info("检测到旧版本数据库，开始升级到v2.0...")
        return db_v2.setup_database_v2()
    finally:
        db_v2.close()

# --- 主程序入口 ---
if __name__ == "__main__":
    # 测试数据库架构
    print("=== 微信监听器数据库架构 v2.0 测试 ===")
    
    db_v2 = DatabaseV2()
    try:
        # 初始化数据库
        db_v2.setup_database_v2()
        
        # 测试保存消息
        print("\n测试保存原始消息...")
        msg_id = db_v2.save_raw_message(
            "测试群", "测试用户", "这是一条测试消息", "Text"
        )
        print(f"✓ 消息保存成功，ID: {msg_id}")
        
        # 测试获取未处理消息
        print("\n测试获取未处理消息...")
        unprocessed = db_v2.get_unprocessed_raw_messages(10)
        print(f"✓ 获取到 {len(unprocessed)} 条未处理消息")
        
        # 测试生成去重哈希
        print("\n测试去重哈希生成...")
        hash_val = db_v2.generate_dedup_hash("测试群", "测试用户", "这是一条测试消息")
        print(f"✓ 去重哈希: {hash_val[:16]}...")
        
        # 测试批次日志
        print("\n测试批次日志...")
        batch_id = db_v2.generate_batch_id()
        log_id = db_v2.log_processing_batch(
            batch_id, "test", "started", 
            records_processed=1
        )
        print(f"✓ 批次日志记录成功，批次ID: {batch_id}")
        
        print("\n=== 数据库架构 v2.0 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise
    finally:
        db_v2.close() 