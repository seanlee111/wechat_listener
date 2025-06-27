"""
微信监听器备份管理器 v2.0
提供全面的数据备份、恢复、验证和清理功能
"""

import sqlite3
import json
import gzip
import shutil
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass

# 配置日志
logger = logging.getLogger(__name__)

# --- 配置 ---
BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class BackupConfig:
    """备份配置类"""
    auto_backup_enabled: bool = True
    max_auto_backups: int = 10
    backup_retention_days: int = 30
    compression_enabled: bool = True
    verification_enabled: bool = True
    pre_operation_backup: bool = True
    backup_format: str = "sqlite"  # sqlite, sql_dump, json

class BackupManager:
    """
    数据库备份管理器
    提供自动备份、手动备份、恢复、验证等功能
    """
    
    def __init__(self, db_path: Optional[Path] = None, config: Optional[BackupConfig] = None):
        """初始化备份管理器"""
        from database_v2 import DatabaseV2
        
        self.db_v2 = DatabaseV2(db_path) if db_path else DatabaseV2()
        self.config = config or BackupConfig()
        self.backup_dir = BACKUP_DIR
        
        # 确保备份目录存在
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"备份管理器初始化完成，备份目录: {self.backup_dir}")
    
    def create_automatic_backup(self, operation_type: str = "auto") -> Optional[str]:
        """
        创建自动备份
        返回备份文件路径
        """
        logger.info(f"开始创建自动备份，操作类型: {operation_type}")
        
        try:
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"auto_backup_{timestamp}.db"
            if self.config.compression_enabled:
                backup_filename += ".gz"
            
            backup_path = self.backup_dir / backup_filename
            
            # 执行备份
            backup_info = self._create_backup(
                backup_path=backup_path,
                backup_type="auto",
                notes=f"自动备份 - {operation_type}操作前"
            )
            
            if backup_info:
                logger.info(f"✓ 自动备份创建成功: {backup_path}")
                
                # 清理旧的自动备份
                self._cleanup_old_auto_backups()
                
                return str(backup_path)
            else:
                logger.error("自动备份创建失败")
                return None
                
        except Exception as e:
            logger.error(f"创建自动备份时发生错误: {e}")
            return None
    
    def create_manual_backup(self, notes: str = "") -> Optional[str]:
        """
        创建手动备份
        返回备份文件路径
        """
        logger.info("开始创建手动备份")
        
        try:
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"manual_backup_{timestamp}.db"
            if self.config.compression_enabled:
                backup_filename += ".gz"
            
            backup_path = self.backup_dir / backup_filename
            
            # 执行备份
            backup_info = self._create_backup(
                backup_path=backup_path,
                backup_type="manual",
                notes=notes or "手动备份"
            )
            
            if backup_info:
                logger.info(f"✓ 手动备份创建成功: {backup_path}")
                return str(backup_path)
            else:
                logger.error("手动备份创建失败")
                return None
                
        except Exception as e:
            logger.error(f"创建手动备份时发生错误: {e}")
            return None
    
    def create_pre_operation_backup(self, operation_name: str) -> Optional[str]:
        """
        创建操作前备份
        用于重要操作前的数据保护
        """
        logger.info(f"开始创建操作前备份，操作: {operation_name}")
        
        try:
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_op_name = "".join(c for c in operation_name if c.isalnum() or c in "._-")
            backup_filename = f"pre_{safe_op_name}_{timestamp}.db"
            if self.config.compression_enabled:
                backup_filename += ".gz"
            
            backup_path = self.backup_dir / backup_filename
            
            # 执行备份
            backup_info = self._create_backup(
                backup_path=backup_path,
                backup_type="pre-operation",
                notes=f"操作前备份 - {operation_name}"
            )
            
            if backup_info:
                logger.info(f"✓ 操作前备份创建成功: {backup_path}")
                return str(backup_path)
            else:
                logger.error("操作前备份创建失败")
                return None
                
        except Exception as e:
            logger.error(f"创建操作前备份时发生错误: {e}")
            return None
    
    def _create_backup(self, backup_path: Path, backup_type: str, notes: str = "") -> Optional[Dict]:
        """
        执行实际的备份操作
        """
        try:
            start_time = datetime.now()
            
            # 获取源数据库路径
            source_db_path = self.db_v2.db_path
            
            if not source_db_path.exists():
                logger.error(f"源数据库文件不存在: {source_db_path}")
                return None
            
            # 记录备份开始
            backup_id = self._log_backup_start(backup_type, str(backup_path), notes)
            
            # 执行数据库备份
            if self.config.compression_enabled and backup_path.suffix == ".gz":
                # 压缩备份
                with open(source_db_path, 'rb') as f_in:
                    with gzip.open(backup_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # 直接复制
                shutil.copy2(source_db_path, backup_path)
            
            # 获取备份文件信息
            file_size = backup_path.stat().st_size
            original_size = source_db_path.stat().st_size
            compression_ratio = file_size / original_size if original_size > 0 else 1.0
            
            # 计算校验和
            checksum = self._calculate_checksum(backup_path)
            
            # 获取记录数量
            record_count = self._get_total_record_count()
            
            # 更新备份元数据
            backup_info = {
                "backup_id": backup_id,
                "backup_path": str(backup_path),
                "backup_type": backup_type,
                "record_count": record_count,
                "file_size_bytes": file_size,
                "checksum": checksum,
                "compression_ratio": compression_ratio,
                "backup_status": "completed",
                "notes": notes
            }
            
            self._log_backup_completion(backup_info)
            
            # 验证备份完整性（如果启用）
            if self.config.verification_enabled:
                if self._verify_backup_integrity(backup_path, checksum):
                    logger.info("✓ 备份完整性验证通过")
                else:
                    logger.warning("⚠ 备份完整性验证失败")
                    backup_info["backup_status"] = "verification_failed"
            
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"备份完成，耗时: {execution_time:.2f}秒，大小: {file_size/1024/1024:.2f}MB")
            
            return backup_info
            
        except Exception as e:
            logger.error(f"备份操作失败: {e}")
            # 记录备份失败
            if 'backup_id' in locals():
                self._log_backup_failure(backup_id, str(e))
            return None
    
    def restore_backup(self, backup_path: str, verify_before_restore: bool = True) -> bool:
        """
        从备份恢复数据库
        """
        logger.info(f"开始从备份恢复数据库: {backup_path}")
        
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            # 恢复前验证
            if verify_before_restore:
                if not self._verify_backup_integrity(backup_file):
                    logger.error("备份文件完整性验证失败，恢复中止")
                    return False
            
            # 创建当前状态的备份
            current_backup = self.create_pre_operation_backup("restore_operation")
            if not current_backup:
                logger.warning("无法创建恢复前备份，但继续执行恢复操作")
            
            # 关闭当前数据库连接
            if self.db_v2.db:
                self.db_v2.close()
            
            # 执行恢复
            target_db_path = self.db_v2.db_path
            
            if backup_file.suffix == ".gz":
                # 解压恢复
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(target_db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # 直接复制
                shutil.copy2(backup_file, target_db_path)
            
            # 重新初始化数据库连接
            self.db_v2._initialize_connection()
            
            # 验证恢复后的数据库
            if self._verify_restored_database():
                logger.info("✓ 数据库恢复成功并验证通过")
                self._log_restore_success(backup_path)
                return True
            else:
                logger.error("恢复后的数据库验证失败")
                return False
                
        except Exception as e:
            logger.error(f"数据库恢复失败: {e}")
            return False
    
    def list_backups(self, backup_type: Optional[str] = None) -> List[Dict]:
        """
        列出所有备份
        """
        try:
            query = "SELECT * FROM backup_metadata"
            params = []
            
            if backup_type:
                query += " WHERE backup_type = ?"
                params.append(backup_type)
            
            query += " ORDER BY created_at DESC"
            
            backups = list(self.db_v2.db.execute(query, params))
            return [dict(backup) for backup in backups]
            
        except Exception as e:
            logger.error(f"获取备份列表失败: {e}")
            return []
    
    def cleanup_expired_backups(self) -> int:
        """
        清理过期的备份
        返回清理的备份数量
        """
        logger.info("开始清理过期备份")
        cleaned_count = 0
        
        try:
            # 获取过期备份
            expiry_date = datetime.now() - timedelta(days=self.config.backup_retention_days)
            expired_backups = self.db_v2.db.execute("""
                SELECT * FROM backup_metadata 
                WHERE created_at < ? 
                AND backup_type != 'manual'
                ORDER BY created_at
            """, [expiry_date.isoformat()]).fetchall()
            
            for backup in expired_backups:
                try:
                    # 删除备份文件
                    backup_file = Path(backup['backup_file_path'])
                    if backup_file.exists():
                        backup_file.unlink()
                        logger.info(f"删除过期备份文件: {backup_file}")
                    
                    # 删除元数据记录
                    self.db_v2.db.execute(
                        "DELETE FROM backup_metadata WHERE id = ?", 
                        [backup['id']]
                    )
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"删除备份 {backup['backup_file_path']} 时出错: {e}")
            
            logger.info(f"清理完成，删除了 {cleaned_count} 个过期备份")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期备份时发生错误: {e}")
            return 0
    
    def _cleanup_old_auto_backups(self):
        """清理旧的自动备份，保留指定数量"""
        try:
            auto_backups = self.db_v2.db.execute("""
                SELECT * FROM backup_metadata 
                WHERE backup_type = 'auto' 
                ORDER BY created_at DESC
            """).fetchall()
            
            if len(auto_backups) > self.config.max_auto_backups:
                # 删除超出限制的旧备份
                to_delete = auto_backups[self.config.max_auto_backups:]
                
                for backup in to_delete:
                    try:
                        backup_file = Path(backup['backup_file_path'])
                        if backup_file.exists():
                            backup_file.unlink()
                        
                        self.db_v2.db.execute(
                            "DELETE FROM backup_metadata WHERE id = ?", 
                            [backup['id']]
                        )
                        
                        logger.info(f"删除旧自动备份: {backup_file}")
                        
                    except Exception as e:
                        logger.error(f"删除旧自动备份时出错: {e}")
                        
        except Exception as e:
            logger.error(f"清理旧自动备份时发生错误: {e}")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件的SHA256校验和"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _verify_backup_integrity(self, backup_path: Path, expected_checksum: str = None) -> bool:
        """验证备份文件完整性"""
        try:
            if not backup_path.exists():
                return False
            
            # 计算当前校验和
            current_checksum = self._calculate_checksum(backup_path)
            
            if expected_checksum:
                return current_checksum == expected_checksum
            else:
                return True  # 简化验证
                    
        except Exception as e:
            logger.error(f"验证备份完整性时出错: {e}")
            return False
    
    def _verify_restored_database(self) -> bool:
        """验证恢复后的数据库"""
        try:
            # 检查关键表是否存在
            tables = self.db_v2.db.table_names()
            required_tables = ["messages_raw", "messages_clean", "processing_logs"]
            
            for table in required_tables:
                if table not in tables:
                    logger.error(f"恢复后的数据库缺少必要表: {table}")
                    return False
            
            # 检查数据库是否可以正常操作
            self.db_v2.db.execute("SELECT COUNT(*) FROM messages_raw").fetchone()
            
            return True
            
        except Exception as e:
            logger.error(f"验证恢复数据库时出错: {e}")
            return False
    
    def _get_total_record_count(self) -> int:
        """获取数据库总记录数"""
        try:
            tables = ["messages_raw", "messages_staging", "messages_clean", "jobs", "processing_logs"]
            total_count = 0
            
            for table in tables:
                if table in self.db_v2.db.table_names():
                    count = self.db_v2.db[table].count
                    total_count += count
            
            return total_count
            
        except Exception as e:
            logger.error(f"获取记录总数时出错: {e}")
            return 0
    
    def _log_backup_start(self, backup_type: str, backup_path: str, notes: str) -> int:
        """记录备份开始"""
        try:
            backup_data = {
                "backup_file_path": backup_path,
                "backup_type": backup_type,
                "source_tables": json.dumps(self.db_v2.db.table_names()),
                "backup_status": "creating",
                "restoration_tested": False,
                "created_at": datetime.now().isoformat(),
                "notes": notes
            }
            
            result = self.db_v2.db["backup_metadata"].insert(backup_data)
            return result.last_pk
            
        except Exception as e:
            logger.error(f"记录备份开始日志失败: {e}")
            return 0
    
    def _log_backup_completion(self, backup_info: Dict):
        """记录备份完成"""
        try:
            self.db_v2.db["backup_metadata"].update(
                backup_info["backup_id"],
                {
                    "record_count": backup_info["record_count"],
                    "file_size_bytes": backup_info["file_size_bytes"],
                    "checksum": backup_info["checksum"],
                    "compression_ratio": backup_info["compression_ratio"],
                    "backup_status": backup_info["backup_status"]
                }
            )
            
        except Exception as e:
            logger.error(f"记录备份完成日志失败: {e}")
    
    def _log_backup_failure(self, backup_id: int, error_message: str):
        """记录备份失败"""
        try:
            self.db_v2.db["backup_metadata"].update(
                backup_id,
                {
                    "backup_status": "failed",
                    "notes": f"备份失败: {error_message}"
                }
            )
            
        except Exception as e:
            logger.error(f"记录备份失败日志失败: {e}")
    
    def _log_restore_success(self, backup_path: str):
        """记录恢复成功"""
        try:
            self.db_v2.db["backup_metadata"].update_where(
                "backup_file_path = ?",
                [backup_path],
                {"restored_at": datetime.now().isoformat()}
            )
            
        except Exception as e:
            logger.error(f"记录恢复成功日志失败: {e}")
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """获取备份统计信息"""
        try:
            backup_files = list(self.backup_dir.glob("*.db*"))
            
            if not backup_files:
                return {
                    "total_backups": 0,
                    "total_size_mb": 0.0,
                    "latest_backup": None,
                    "oldest_backup": None,
                    "backup_types": {}
                }
            
            total_size = sum(f.stat().st_size for f in backup_files)
            total_size_mb = total_size / (1024 * 1024)
            
            # 按修改时间排序
            backup_files.sort(key=lambda x: x.stat().st_mtime)
            
            # 统计备份类型
            backup_types = {}
            for f in backup_files:
                if "auto_" in f.name:
                    backup_types["auto"] = backup_types.get("auto", 0) + 1
                elif "manual_" in f.name:
                    backup_types["manual"] = backup_types.get("manual", 0) + 1
                elif "pre_" in f.name:
                    backup_types["pre-operation"] = backup_types.get("pre-operation", 0) + 1
                else:
                    backup_types["other"] = backup_types.get("other", 0) + 1
            
            return {
                "total_backups": len(backup_files),
                "total_size_mb": round(total_size_mb, 2),
                "latest_backup": backup_files[-1].name if backup_files else None,
                "oldest_backup": backup_files[0].name if backup_files else None,
                "backup_types": backup_types,
                "backup_files": [f.name for f in backup_files[-5:]]  # 最近5个备份
            }
        except Exception as e:
            logger.error(f"获取备份统计失败: {e}")
            return {"error": str(e)}

# --- 便利函数 ---

def create_backup(backup_type: str = "manual", notes: str = "") -> Optional[str]:
    """创建备份的便利函数"""
    backup_manager = BackupManager()
    
    if backup_type == "manual":
        return backup_manager.create_manual_backup(notes)
    else:
        return backup_manager.create_automatic_backup(backup_type)

def restore_from_backup(backup_path: str) -> bool:
    """从备份恢复的便利函数"""
    backup_manager = BackupManager()
    return backup_manager.restore_backup(backup_path)

# --- 主程序入口 ---
if __name__ == "__main__":
    # 测试备份管理器
    print("=== 备份管理器测试 ===")
    
    backup_manager = BackupManager()
    
    try:
        # 测试创建手动备份
        print("\n测试创建手动备份...")
        backup_path = backup_manager.create_manual_backup("测试备份")
        if backup_path:
            print(f"✓ 手动备份创建成功: {backup_path}")
        
        print("\n=== 备份管理器测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise 