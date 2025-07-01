"""
AI模块专用数据库操作类
实现零侵入设计，不修改现有数据库结构
"""

import sqlite_utils
import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from dataclasses import asdict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取项目根目录和数据库路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "wechat_jds.db"


class AIDatabase:
    """
    AI模块专用数据库管理器
    零侵入设计：只创建新表，不修改现有表
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """初始化AI数据库连接"""
        self.db_path = db_path or DB_FILE
        self.db = None
        self._initialize_connection()
        
    def _initialize_connection(self):
        """初始化数据库连接"""
        try:
            # 确保数据目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建带超时的原生连接
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            # 启用WAL模式提升并发性能
            conn.execute("PRAGMA journal_mode = WAL")
            # 使用sqlite-utils包装
            self.db = sqlite_utils.Database(conn)
            
            logger.info(f"AI数据库连接已建立: {self.db_path}")
        except Exception as e:
            logger.error(f"AI数据库连接失败: {e}")
            raise
    
    def setup_ai_tables(self) -> bool:
        """
        创建AI模块相关的所有表
        不影响现有表结构
        """
        logger.info("开始创建AI模块数据表...")
        
        try:
            # 1. 创建AI提取结果表
            self._create_ai_extracted_jobs_table()
            
            # 2. 创建处理批次表
            self._create_ai_processing_batches_table()
            
            # 3. 创建性能监控表
            self._create_ai_performance_metrics_table()
            
            # 4. 创建所有索引
            self._create_ai_indexes()
            
            logger.info("AI模块数据表创建完成！")
            return True
            
        except Exception as e:
            logger.error(f"AI数据表创建失败: {e}")
            raise
    
    def _create_ai_extracted_jobs_table(self):
        """创建AI提取结果表"""
        self.db["ai_extracted_jobs"].create({
            # 主键和关联
            "id": int,
            "message_id": int,
            
            # 处理元数据
            "processed_at": str,
            "processing_batch_id": str,
            "extraction_method": str,        # 'gpt4', 'claude3.5', 'tongyi'
            "model_version": str,            # 具体模型版本
            "confidence_score": float,       # 总体置信度 0.0-1.0
            "processing_time_ms": int,       # 处理耗时毫秒
            "api_cost_cents": int,           # API调用成本（分）
            
            # JD检测结果
            "is_job_posting": bool,          # 是否为招聘信息
            "jd_detection_confidence": float, # JD检测置信度
            
            # 提取的JD信息
            "company_name": str,
            "company_confidence": float,     # 公司名置信度
            "position_title": str,
            "position_confidence": float,    # 职位名置信度
            "work_location": str,
            "location_confidence": float,    # 地点置信度
            "salary_range": str,
            "salary_confidence": float,      # 薪资置信度
            "contact_email": str,
            "email_confidence": float,       # 邮箱置信度
            "contact_phone": str,
            "phone_confidence": float,       # 电话置信度
            "contact_wechat": str,
            "wechat_confidence": float,      # 微信置信度
            
            # 详细信息
            "job_requirements": str,         # 岗位要求
            "education_requirement": str,    # 学历要求
            "work_type": str,               # 全职/实习/兼职
            "experience_requirement": str,   # 经验要求
            "work_mode": str,               # 远程/现场/混合
            
            # 原始数据保存
            "raw_ai_response": str,         # 完整AI响应
            "extraction_prompt": str,       # 使用的提示词
            "prompt_tokens": int,           # 提示词token数
            "completion_tokens": int,       # 回复token数
            
            # 质量控制
            "quality_score": float,         # 整体质量评分
            "validation_status": str,       # pending, validated, rejected
            "validation_notes": str,        # 验证备注
            "human_verified": bool,         # 人工验证结果
            "human_feedback": str,          # 人工反馈
            
            # 业务状态
            "status": str,                  # extracted, processed, sent, archived
            "error_message": str,           # 错误信息
            "retry_count": int,             # 重试次数
            
            # 时间戳
            "created_at": str,
            "updated_at": str
        }, pk="id", if_not_exists=True)
        
        logger.info("✓ AI提取结果表 ai_extracted_jobs 创建完成")
    
    def _create_ai_processing_batches_table(self):
        """创建处理批次表"""
        self.db["ai_processing_batches"].create({
            "id": int,
            "batch_id": str,
            "started_at": str,
            "completed_at": str,
            "status": str,                  # running, completed, failed, cancelled
            
            # 批次统计
            "total_messages": int,
            "processed_messages": int,
            "successful_extractions": int,
            "failed_extractions": int,
            "jd_found_count": int,
            
            # 性能指标
            "total_processing_time_ms": int,
            "avg_confidence_score": float,
            "total_api_cost_cents": int,
            
            # 配置信息
            "provider_used": str,
            "model_version": str,
            "batch_size": int,
            
            # 元数据
            "triggered_by": str,            # manual, scheduled, api
            "config_snapshot": str,         # 使用的配置快照
            "notes": str
        }, pk="id", if_not_exists=True)
        
        # 创建batch_id唯一约束
        try:
            self.db["ai_processing_batches"].create_index(
                ["batch_id"], unique=True, if_not_exists=True
            )
        except:
            pass
        
        logger.info("✓ 处理批次表 ai_processing_batches 创建完成")
    
    def _create_ai_performance_metrics_table(self):
        """创建性能监控表"""
        self.db["ai_performance_metrics"].create({
            "id": int,
            "metric_date": str,             # 日期
            "provider": str,                # 提供商名称
            "model_version": str,           # 模型版本
            
            # 性能指标
            "total_requests": int,
            "successful_requests": int,
            "failed_requests": int,
            "avg_response_time_ms": float,
            "total_cost_cents": int,
            
            # 质量指标
            "avg_confidence_score": float,
            "jd_detection_accuracy": float,
            "extraction_accuracy": float,
            
            # 资源使用
            "total_prompt_tokens": int,
            "total_completion_tokens": int,
            "avg_tokens_per_request": float,
            
            "created_at": str
        }, pk="id", if_not_exists=True)
        
        # 创建复合唯一约束
        try:
            self.db["ai_performance_metrics"].create_index(
                ["metric_date", "provider", "model_version"], 
                unique=True, if_not_exists=True
            )
        except:
            pass
        
        logger.info("✓ 性能监控表 ai_performance_metrics 创建完成")
    
    def _create_ai_indexes(self):
        """创建AI表的索引"""
        # ai_extracted_jobs 表索引
        indexes = [
            (["message_id"], False),
            (["processing_batch_id"], False),
            (["extraction_method"], False),
            (["is_job_posting"], False),
            (["confidence_score"], False),
            (["status"], False),
            (["processed_at"], False),
            (["company_name"], False),
            (["position_title"], False)
        ]
        
        for columns, unique in indexes:
            try:
                self.db["ai_extracted_jobs"].create_index(
                    columns, unique=unique, if_not_exists=True
                )
            except:
                pass
        
        logger.info("✓ AI数据表索引创建完成")
    
    def get_unprocessed_messages(self, limit: int = 100) -> List[Dict]:
        """
        获取未被AI处理的消息
        使用LEFT JOIN判断，零侵入设计
        """
        sql = """
        SELECT m.id, m.group_name, m.sender, m.content, m.timestamp
        FROM messages_clean m
        LEFT JOIN ai_extracted_jobs a ON m.id = a.message_id  
        WHERE a.message_id IS NULL
        AND m.content IS NOT NULL
        AND LENGTH(m.content) > 20
        ORDER BY m.timestamp DESC
        LIMIT ?
        """
        
        try:
            return list(self.db.execute(sql, [limit]).fetchall())
        except Exception as e:
            logger.error(f"获取未处理消息失败: {e}")
            return []
    
    def save_extraction_result(self, result_data: Dict) -> int:
        """保存AI提取结果"""
        try:
            # 添加时间戳
            now = datetime.now().isoformat()
            result_data.update({
                "created_at": now,
                "updated_at": now
            })
            
            # 插入数据
            result = self.db["ai_extracted_jobs"].insert(result_data)
            logger.info(f"AI提取结果已保存，ID: {result.last_pk}")
            return result.last_pk
            
        except Exception as e:
            logger.error(f"保存AI提取结果失败: {e}")
            raise
    
    def create_processing_batch(self, batch_id: str, total_messages: int, 
                              config: Dict = None) -> int:
        """创建处理批次记录"""
        try:
            batch_data = {
                "batch_id": batch_id,
                "started_at": datetime.now().isoformat(),
                "status": "running",
                "total_messages": total_messages,
                "processed_messages": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
                "jd_found_count": 0,
                "total_processing_time_ms": 0,
                "avg_confidence_score": 0.0,
                "total_api_cost_cents": 0,
                "triggered_by": "manual",
                "config_snapshot": json.dumps(config) if config else "{}",
                "notes": ""
            }
            
            result = self.db["ai_processing_batches"].insert(batch_data)
            logger.info(f"处理批次已创建，ID: {result.last_pk}")
            return result.last_pk
            
        except Exception as e:
            logger.error(f"创建处理批次失败: {e}")
            raise
    
    def update_processing_batch(self, batch_id: str, updates: Dict):
        """更新处理批次状态"""
        try:
            # 直接使用 WHERE 条件更新，不需要先查询ID
            # 不自动添加updated_at字段，让调用者决定要更新的字段
            
            # 构建更新SQL
            update_fields = []
            update_values = []
            for key, value in updates.items():
                update_fields.append(f"{key} = ?")
                update_values.append(value)
            
            update_values.append(batch_id)
            
            sql = f"""
                UPDATE ai_processing_batches 
                SET {', '.join(update_fields)}
                WHERE batch_id = ?
            """
            
            result = self.db.execute(sql, update_values)
            
            if result.rowcount > 0:
                logger.info(f"批次 {batch_id} 状态已更新")
            else:
                logger.error(f"未找到批次: {batch_id}")
                raise ValueError(f"未找到批次: {batch_id}")
            
        except Exception as e:
            logger.error(f"更新处理批次失败: {e}")
            raise
    
    def get_processing_summary(self) -> Dict:
        """获取处理进度汇总"""
        try:
            sql = """
            SELECT 
                COUNT(m.id) as total_messages,
                COUNT(a.id) as processed_messages,
                COUNT(m.id) - COUNT(a.id) as pending_messages,
                ROUND(
                    CAST(COUNT(a.id) AS FLOAT) / COUNT(m.id) * 100, 2
                ) as completion_percentage,
                SUM(CASE WHEN a.is_job_posting = 1 THEN 1 ELSE 0 END) as jd_found,
                AVG(a.confidence_score) as avg_confidence
            FROM messages_clean m
            LEFT JOIN ai_extracted_jobs a ON m.id = a.message_id
            """
            
            result = self.db.execute(sql).fetchone()
            return dict(result) if result else {}
            
        except Exception as e:
            logger.error(f"获取处理汇总失败: {e}")
            return {}
    
    def is_message_processed(self, message_id: int) -> bool:
        """检查消息是否已被AI处理"""
        try:
            result = self.db.execute("""
                SELECT 1 FROM ai_extracted_jobs 
                WHERE message_id = ?
            """, [message_id]).fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"检查消息处理状态失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
            logger.info("AI数据库连接已关闭")


def get_ai_database() -> AIDatabase:
    """获取AI数据库实例的工厂函数"""
    return AIDatabase()


# 测试代码
if __name__ == "__main__":
    # 测试数据库创建
    ai_db = AIDatabase()
    ai_db.setup_ai_tables()
    
    # 测试获取未处理消息
    unprocessed = ai_db.get_unprocessed_messages(limit=5)
    print(f"未处理消息数量: {len(unprocessed)}")
    
    # 测试处理汇总
    summary = ai_db.get_processing_summary()
    print(f"处理汇总: {summary}")
    
    ai_db.close()
    print("AI数据库模块测试完成") 