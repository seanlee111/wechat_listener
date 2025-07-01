"""
AI模块数据库扩展
在现有DatabaseV2基础上添加AI专用表和功能
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.database_v2 import DatabaseV2

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIDatabaseExtension:
    """
    AI模块数据库扩展
    在现有DatabaseV2基础上添加AI专用功能
    """
    
    def __init__(self, db_v2: Optional[DatabaseV2] = None):
        """
        初始化AI数据库扩展
        
        Args:
            db_v2: DatabaseV2实例，如果为None则创建新实例
        """
        self.db_v2 = db_v2 or DatabaseV2()
        self.ai_tables_created = False
        
        logger.info("AI数据库扩展初始化完成")
    
    def setup_ai_tables(self) -> bool:
        """
        创建AI模块专用表
        
        Returns:
            创建成功返回True
        """
        try:
            logger.info("开始创建AI模块专用表...")
            
            # 1. 创建AI提取结果表
            self._create_ai_extracted_jobs_table()
            
            # 2. 创建AI处理日志表
            self._create_ai_processing_logs_table()
            
            # 3. 创建AI模型配置表
            self._create_ai_model_configs_table()
            
            # 4. 创建必要的索引
            self._create_ai_indexes()
            
            self.ai_tables_created = True
            logger.info("✅ AI模块专用表创建完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建AI专用表失败: {e}")
            raise
    
    def _create_ai_extracted_jobs_table(self):
        """创建AI提取的招聘信息表"""
        # 只在表不存在时创建，不再强制删除
        if "ai_extracted_jobs" not in self.db_v2.db.table_names():
            self.db_v2.db["ai_extracted_jobs"].create({
                "id": int,
                "clean_message_id": int,    # 关联消息ID (兼容不同表结构)
                "raw_message_id": int,      # 原始消息ID
                
                # 基础信息
                "company_name": str,
                "position_title": str,
                "work_location": str,
                
                # 联系信息
                "contact_email": str,
                "email_subject_format": str,
                "resume_naming_format": str,
                
                # 要求信息
                "education_requirement": str,
                "major_requirement": str,
                "internship_duration": str,
                "skills_required": str,
                
                # 工作信息
                "work_description": str,
                "special_requirements": str,
                
                # AI元数据
                "llm_confidence": float,
                "model_used": str,
                "extraction_timestamp": str,
                "original_content": str,    # 原始消息内容(截取)
                
                # 质量控制
                "validation_status": str,   # 'pending', 'validated', 'rejected'
                "validation_feedback": str,
                "ready_for_delivery": bool, # 是否准备好投递
                
                # 时间戳
                "created_at": str,
                "updated_at": str
            }, pk="id")
            logger.info("✓ AI提取结果表 ai_extracted_jobs 创建完成")
        else:
            logger.info("✓ AI提取结果表 ai_extracted_jobs 已存在，跳过创建")
    
    def _create_ai_processing_logs_table(self):
        """创建AI处理日志表"""
        if "ai_processing_logs" not in self.db_v2.db.table_names():
            self.db_v2.db["ai_processing_logs"].create({
                "id": int,
                "batch_id": str,
                "operation_type": str,      # 'extraction', 'validation', 'cleanup'
                "status": str,              # 'started', 'completed', 'failed'
                "model_used": str,
                "processing_time_ms": int,
                "messages_processed": int,
                "successful_extractions": int,
                "failed_extractions": int,
                "average_confidence": float,
                "error_message": str,
                "config_snapshot": str,     # JSON格式的配置快照
                "created_at": str,
                "completed_at": str
            }, pk="id")
            logger.info("✓ AI处理日志表 ai_processing_logs 创建完成")
        else:
            logger.info("✓ AI处理日志表 ai_processing_logs 已存在，跳过创建")
    
    def _create_ai_model_configs_table(self):
        """创建AI模型配置表"""
        if "ai_model_configs" not in self.db_v2.db.table_names():
            self.db_v2.db["ai_model_configs"].create({
                "id": int,
                "config_name": str,
                "provider": str,            # 'mock', 'volcano', 'qwen'
                "model_version": str,
                "config_data": str,         # JSON格式的配置数据
                "is_active": bool,
                "performance_score": float,
                "usage_count": int,
                "last_used_at": str,
                "created_at": str,
                "updated_at": str
            }, pk="id")
            logger.info("✓ AI模型配置表 ai_model_configs 创建完成")
        else:
            logger.info("✓ AI模型配置表 ai_model_configs 已存在，跳过创建")
    
    def _create_ai_indexes(self):
        """创建AI表的必要索引"""
        try:
            # ai_extracted_jobs表索引
            self.db_v2.db["ai_extracted_jobs"].create_index(
                ["clean_message_id"], if_not_exists=True
            )
            self.db_v2.db["ai_extracted_jobs"].create_index(
                ["raw_message_id"], if_not_exists=True
            )
            self.db_v2.db["ai_extracted_jobs"].create_index(
                ["validation_status"], if_not_exists=True
            )
            self.db_v2.db["ai_extracted_jobs"].create_index(
                ["ready_for_delivery"], if_not_exists=True
            )
            self.db_v2.db["ai_extracted_jobs"].create_index(
                ["created_at"], if_not_exists=True
            )
            
            # ai_processing_logs表索引
            self.db_v2.db["ai_processing_logs"].create_index(
                ["batch_id"], if_not_exists=True
            )
            self.db_v2.db["ai_processing_logs"].create_index(
                ["operation_type", "status"], if_not_exists=True
            )
            self.db_v2.db["ai_processing_logs"].create_index(
                ["created_at"], if_not_exists=True
            )
            
        except Exception as e:
            logger.warning(f"创建AI索引时出现警告: {e}")
        
        logger.info("✓ AI表索引创建完成")
    
    def save_extraction_result(self, extraction_data: Dict) -> int:
        """
        保存AI提取结果
        
        Args:
            extraction_data: 提取结果字典
            
        Returns:
            插入的记录ID
        """
        try:
            now = datetime.now().isoformat()
            
            # 准备插入数据
            insert_data = {
                "clean_message_id": extraction_data.get('source_message_id'),
                "raw_message_id": extraction_data.get('raw_message_id'),
                
                # 基础信息
                "company_name": extraction_data.get('company_name'),
                "position_title": extraction_data.get('position_title'),
                "work_location": extraction_data.get('work_location'),
                
                # 联系信息
                "contact_email": extraction_data.get('contact_email'),
                "email_subject_format": extraction_data.get('email_subject_format'),
                "resume_naming_format": extraction_data.get('resume_naming_format'),
                
                # 要求信息
                "education_requirement": extraction_data.get('education_requirement'),
                "major_requirement": extraction_data.get('major_requirement'),
                "internship_duration": extraction_data.get('internship_duration'),
                "skills_required": extraction_data.get('skills_required'),
                
                # 工作信息
                "work_description": extraction_data.get('work_description'),
                "special_requirements": extraction_data.get('special_requirements'),
                
                # AI元数据
                "llm_confidence": extraction_data.get('llm_confidence', 0.0),
                "model_used": extraction_data.get('model_used', 'unknown'),
                "extraction_timestamp": extraction_data.get('extraction_timestamp', now),
                "original_content": extraction_data.get('original_content', ''),
                
                # 质量控制
                "validation_status": 'pending',
                "validation_feedback": '',
                "ready_for_delivery": extraction_data.get('llm_confidence', 0.0) > 0.8,
                
                # 时间戳
                "created_at": now,
                "updated_at": now
            }
            
            # 插入数据
            result = self.db_v2.db["ai_extracted_jobs"].insert(insert_data)
            record_id = result.last_pk
            
            logger.debug(f"AI提取结果已保存: ID={record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"保存AI提取结果失败: {e}")
            raise
    
    def save_batch_results(self, batch_results: List[Dict]) -> int:
        """
        批量保存提取结果
        
        Args:
            batch_results: 提取结果列表
            
        Returns:
            成功保存的记录数
        """
        saved_count = 0
        
        for result_data in batch_results:
            try:
                self.save_extraction_result(result_data)
                saved_count += 1
            except Exception as e:
                logger.error(f"批量保存第{saved_count+1}条记录失败: {e}")
        
        logger.info(f"批量保存完成: {saved_count}/{len(batch_results)} 条记录成功")
        return saved_count
    
    def log_processing_batch(self, batch_data: Dict) -> int:
        """
        记录AI处理批次日志
        
        Args:
            batch_data: 批次处理数据
            
        Returns:
            日志记录ID
        """
        try:
            now = datetime.now().isoformat()
            
            log_data = {
                "batch_id": batch_data.get('batch_id', f"batch_{int(datetime.now().timestamp())}"),
                "operation_type": batch_data.get('operation_type', 'extraction'),
                "status": batch_data.get('status', 'completed'),
                "model_used": batch_data.get('model_used', 'unknown'),
                "processing_time_ms": batch_data.get('processing_time_ms', 0),
                "messages_processed": batch_data.get('messages_processed', 0),
                "successful_extractions": batch_data.get('successful_extractions', 0),
                "failed_extractions": batch_data.get('failed_extractions', 0),
                "average_confidence": batch_data.get('average_confidence', 0.0),
                "error_message": batch_data.get('error_message', ''),
                "config_snapshot": json.dumps(batch_data.get('config_snapshot', {})),
                "created_at": now,
                "completed_at": batch_data.get('completed_at', now)
            }
            
            result = self.db_v2.db["ai_processing_logs"].insert(log_data)
            return result.last_pk
            
        except Exception as e:
            logger.error(f"记录AI处理日志失败: {e}")
            return 0
    
    def get_extraction_stats(self) -> Dict:
        """获取AI提取统计信息"""
        try:
            stats = {}
            
            # 检查表是否存在
            if "ai_extracted_jobs" in self.db_v2.db.table_names():
                table = self.db_v2.db["ai_extracted_jobs"]
                
                stats.update({
                    'total_extractions': table.count,
                    'validated_extractions': table.count_where("validation_status = 'validated'"),
                    'pending_extractions': table.count_where("validation_status = 'pending'"),
                    'ready_for_delivery': table.count_where("ready_for_delivery = 1"),
                    'avg_confidence': table.execute("SELECT AVG(llm_confidence) FROM ai_extracted_jobs").fetchone()[0] or 0.0
                })
            else:
                stats = {
                    'total_extractions': 0,
                    'validated_extractions': 0,
                    'pending_extractions': 0,
                    'ready_for_delivery': 0,
                    'avg_confidence': 0.0
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取AI提取统计失败: {e}")
            return {}
    
    def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        return table_name in self.db_v2.db.table_names()

# 测试工具
def test_ai_database_extension():
    """测试AI数据库扩展"""
    print("=== 测试AI数据库扩展 ===")
    
    try:
        # 测试初始化
        print("\n1. 测试初始化:")
        ai_db = AIDatabaseExtension()
        print(f"   ✅ AI数据库扩展初始化成功")
        
        # 测试创建AI表
        print("\n2. 测试创建AI表:")
        success = ai_db.setup_ai_tables()
        if success:
            print("   ✅ AI专用表创建成功")
            
            # 检查表是否存在
            tables = ['ai_extracted_jobs', 'ai_processing_logs', 'ai_model_configs']
            for table in tables:
                exists = ai_db.check_table_exists(table)
                status = "✅" if exists else "❌"
                print(f"   {status} 表 {table}: {'存在' if exists else '不存在'}")
        
        # 测试保存提取结果
        print("\n3. 测试保存提取结果:")
        test_extraction = {
            'source_message_id': 1,
            'raw_message_id': 101,
            'company_name': '测试公司',
            'position_title': '测试职位',
            'work_location': '测试地点',
            'contact_email': 'test@example.com',
            'llm_confidence': 0.85,
            'model_used': 'test_model',
            'original_content': '这是一条测试消息内容...'
        }
        
        record_id = ai_db.save_extraction_result(test_extraction)
        if record_id > 0:
            print(f"   ✅ 提取结果保存成功: ID={record_id}")
        else:
            print("   ❌ 提取结果保存失败")
        
        # 测试批次日志
        print("\n4. 测试批次日志:")
        batch_data = {
            'batch_id': 'test_batch_001',
            'operation_type': 'extraction',
            'status': 'completed',
            'model_used': 'test_model',
            'messages_processed': 5,
            'successful_extractions': 3,
            'failed_extractions': 2,
            'average_confidence': 0.75
        }
        
        log_id = ai_db.log_processing_batch(batch_data)
        if log_id > 0:
            print(f"   ✅ 批次日志记录成功: ID={log_id}")
        else:
            print("   ❌ 批次日志记录失败")
        
        # 测试统计信息
        print("\n5. 测试统计信息:")
        stats = ai_db.get_extraction_stats()
        if stats:
            print("   ✅ 统计信息获取成功:")
            for key, value in stats.items():
                print(f"   - {key}: {value}")
        else:
            print("   ❌ 统计信息获取失败")
        
        print("\n✅ AI数据库扩展测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ AI数据库扩展测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ai_database_extension() 