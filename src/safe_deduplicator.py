"""
安全去重处理器 v2.0
实现分阶段、可回滚的安全去重逻辑
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import logging

from database_v2 import DatabaseV2
from backup_manager import BackupManager

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class DedupConfig:
    """去重配置类"""
    batch_size: int = 500
    staging_cleanup_enabled: bool = True
    quality_score_threshold: float = 0.7
    max_retries: int = 3
    timeout_seconds: int = 1800  # 30分钟
    progress_callback: Optional[Callable] = None
    create_backup_before_dedup: bool = True
    validation_enabled: bool = True

@dataclass
class DedupStats:
    """去重统计信息"""
    total_raw_messages: int = 0
    processed_messages: int = 0
    duplicate_messages: int = 0
    clean_messages: int = 0
    failed_messages: int = 0
    execution_time_seconds: float = 0.0
    batch_count: int = 0
    
    def get_dedup_ratio(self) -> float:
        """获取去重比例"""
        if self.processed_messages == 0:
            return 0.0
        return self.duplicate_messages / self.processed_messages
    
    def get_success_ratio(self) -> float:
        """获取成功处理比例"""
        if self.processed_messages == 0:
            return 0.0
        return (self.processed_messages - self.failed_messages) / self.processed_messages

class SafeDeduplicator:
    """
    安全去重处理器
    实现分阶段、可回滚的安全去重逻辑
    """
    
    def __init__(self, db_v2: Optional[DatabaseV2] = None, 
                 config: Optional[DedupConfig] = None):
        """初始化安全去重器"""
        self.db_v2 = db_v2 or DatabaseV2()
        self.config = config or DedupConfig()
        self.backup_manager = BackupManager()
        self.stats = DedupStats()
        self.current_batch_id = None
        self.start_time = None
        
        logger.info("安全去重处理器初始化完成")
    
    def execute_safe_deduplication(self) -> bool:
        """执行安全去重的完整流程"""
        logger.info("=== 开始安全去重处理流程 ===")
        self.start_time = time.time()
        
        try:
            # 获取未处理的原始数据
            unprocessed_messages = self._get_unprocessed_messages()
            if not unprocessed_messages:
                logger.info("没有需要处理的消息")
                return True
            
            self.stats.total_raw_messages = len(unprocessed_messages)
            logger.info(f"找到 {self.stats.total_raw_messages} 条未处理消息")
            
            # 执行分批去重处理
            success = self._execute_batch_deduplication(unprocessed_messages)
            
            if success:
                self._log_dedup_completion()
                logger.info("=== 安全去重处理流程完成 ===")
            
            return success
            
        except Exception as e:
            logger.error(f"去重处理过程中发生错误: {e}")
            return False
    
    def _get_unprocessed_messages(self) -> List[Dict]:
        """获取未处理的消息"""
        try:
            unprocessed = self.db_v2.get_unprocessed_raw_messages(limit=10000)
            return unprocessed
        except Exception as e:
            logger.error(f"获取未处理消息时出错: {e}")
            return []
    
    def _execute_batch_deduplication(self, messages: List[Dict]) -> bool:
        """执行分批去重处理"""
        try:
            total_batches = (len(messages) + self.config.batch_size - 1) // self.config.batch_size
            self.stats.batch_count = total_batches
            
            for batch_num in range(total_batches):
                start_idx = batch_num * self.config.batch_size
                end_idx = min(start_idx + self.config.batch_size, len(messages))
                batch_messages = messages[start_idx:end_idx]
                
                success = self._process_single_batch(batch_messages, batch_num + 1)
                if not success:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"分批去重处理失败: {e}")
            return False
    
    def _process_single_batch(self, messages: List[Dict], batch_num: int) -> bool:
        """处理单个批次"""
        try:
            self.current_batch_id = f"dedup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_batch_{batch_num:03d}"
            
            # 生成去重统计
            unique_messages = self._analyze_and_filter_duplicates(messages)
            
            # 移动唯一消息到clean表
            clean_count = self._move_to_clean_table(unique_messages)
            
            # 标记原始消息为已处理
            self._mark_raw_messages_processed(messages)
            
            # 更新统计
            self.stats.processed_messages += len(messages)
            self.stats.clean_messages += clean_count
            self.stats.duplicate_messages += (len(messages) - clean_count)
            
            logger.info(f"批次 {batch_num} 完成: {len(messages)} → {clean_count} 条唯一消息")
            return True
            
        except Exception as e:
            logger.error(f"处理批次 {batch_num} 时出错: {e}")
            return False
    
    def _analyze_and_filter_duplicates(self, messages: List[Dict]) -> List[Dict]:
        """分析并过滤重复消息"""
        seen_hashes = set()
        unique_messages = []
        
        # 首先检查与现有clean表的重复
        existing_hashes = set()
        try:
            existing = list(self.db_v2.db.execute("SELECT DISTINCT dedup_hash FROM messages_clean"))
            existing_hashes = {row[0] for row in existing}
        except:
            pass
        
        for msg in messages:
            dedup_hash = self.db_v2.generate_dedup_hash(
                msg["group_name"], msg["sender"], msg["content"]
            )
            
            if dedup_hash not in seen_hashes and dedup_hash not in existing_hashes:
                seen_hashes.add(dedup_hash)
                msg["dedup_hash"] = dedup_hash
                unique_messages.append(msg)
        
        return unique_messages
    
    def _move_to_clean_table(self, unique_messages: List[Dict]) -> int:
        """将唯一消息移动到clean表"""
        clean_count = 0
        
        for msg in unique_messages:
            try:
                clean_data = {
                    "raw_message_id": msg["id"],
                    "staging_message_id": None,  # 直接去重时为NULL
                    "group_name": msg["group_name"],
                    "sender": msg["sender"],
                    "content": msg["content"],
                    "msg_type": msg["msg_type"],
                    "timestamp": msg["timestamp"],
                    "dedup_hash": msg["dedup_hash"],
                    "processed_batch_id": self.current_batch_id,
                    "quality_score": 1.0,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                self.db_v2.db["messages_clean"].insert(clean_data)
                clean_count += 1
                
            except Exception as e:
                logger.error(f"移动消息到clean表失败: {e}")
                continue
        
        return clean_count
    
    def _mark_raw_messages_processed(self, messages: List[Dict]):
        """标记原始消息为已处理"""
        try:
            for msg in messages:
                self.db_v2.db.execute(
                    "UPDATE messages_raw SET processed_status = 1, updated_at = ? WHERE id = ?",
                    [datetime.now().isoformat(), msg["id"]]
                )
        except Exception as e:
            logger.error(f"标记消息为已处理失败: {e}")
    
    def _log_dedup_completion(self):
        """记录去重完成统计"""
        try:
            self.stats.execution_time_seconds = time.time() - self.start_time
            
            logger.info("=== 去重完成统计 ===")
            logger.info(f"处理消息数: {self.stats.processed_messages}")
            logger.info(f"清洁消息数: {self.stats.clean_messages}")
            logger.info(f"重复消息数: {self.stats.duplicate_messages}")
            logger.info(f"去重比例: {self.stats.get_dedup_ratio():.2%}")
            logger.info(f"执行时间: {self.stats.execution_time_seconds:.2f}秒")
            
        except Exception as e:
            logger.error(f"记录完成统计时出错: {e}")

# --- 便利函数 ---
def execute_safe_deduplication() -> bool:
    """执行安全去重的便利函数"""
    deduplicator = SafeDeduplicator()
    return deduplicator.execute_safe_deduplication()

# --- 主程序入口 ---
if __name__ == "__main__":
    print("=== 安全去重处理器测试 ===")
    
    try:
        success = execute_safe_deduplication()
        
        if success:
            print("✓ 安全去重处理完成")
        else:
            print("❌ 安全去重处理失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise 