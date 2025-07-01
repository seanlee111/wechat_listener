"""
AI作业处理器 - 主控制器
整合三阶段架构：数据准备 → 智能提取 → 结果输出
"""

import logging
import time
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

# 导入三阶段组件
from src.ai_module.data_pipeline import DataPipeline
from src.ai_module.llm_extractor import LLMExtractor
from src.ai_module.result_processor import ResultProcessor
from src.ai_module.ai_database_extension import AIDatabaseExtension
from src.ai_module.config import get_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIJobProcessor:
    """
    AI作业处理器主控制器
    协调三阶段架构完成完整的JD信息提取流程
    """
    
    def __init__(self, 
                 llm_provider: Optional[str] = None,
                 llm_config: Optional[Dict] = None,
                 batch_size: Optional[int] = None):
        """
        初始化AI作业处理器
        
        Args:
            llm_provider: LLM提供商 ('mock', 'volcano', 'qwen')，如果为None则从配置读取
            llm_config: LLM配置字典，如果为None则从配置读取
            batch_size: 批量处理大小，如果为None则从配置读取
        """
        # 加载配置
        self.config = get_config()
        
        # 使用配置或传入参数
        self.llm_provider = llm_provider or self.config.get("llm_extractor", "provider", "mock")
        self.llm_config = llm_config
        self.batch_size = batch_size or self.config.get("data_pipeline", "batch_size", 20)
        
        # 初始化三阶段组件
        logger.info("初始化AI作业处理器...")
        
        try:
            # 共享数据库实例
            self.ai_db = AIDatabaseExtension()
            
            # 阶段1：数据准备
            self.data_pipeline = DataPipeline(self.ai_db.db_v2)
            
            # 阶段2：智能提取
            self.llm_extractor = LLMExtractor(self.llm_provider, self.llm_config)
            
            # 阶段3：结果输出
            self.result_processor = ResultProcessor(self.ai_db)
            
            # 处理统计
            self.total_sessions = 0
            self.total_processed_messages = 0
            self.total_extracted_jobs = 0
            
            # 设置日志级别
            log_level = self.config.get("system", "log_level", "INFO")
            logging.getLogger().setLevel(getattr(logging, log_level))
            
            logger.info(f"✅ AI作业处理器初始化完成: provider={self.llm_provider}, batch_size={self.batch_size}")
            
        except Exception as e:
            logger.error(f"❌ AI作业处理器初始化失败: {e}")
            raise
    
    def setup_system(self) -> bool:
        """
        设置系统环境，创建必要的数据库表
        
        Returns:
            设置成功返回True
        """
        try:
            logger.info("设置AI处理系统...")
            
            # 创建AI专用数据库表
            success = self.ai_db.setup_ai_tables()
            
            if success:
                logger.info("✅ AI处理系统设置完成")
                return True
            else:
                logger.error("❌ AI处理系统设置失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 设置AI处理系统时出错: {e}")
            return False
    
    def process_single_batch(self, batch_size: Optional[int] = None) -> Dict:
        """
        处理单个批次
        
        Args:
            batch_size: 批次大小，如果为None则使用默认值
            
        Returns:
            处理结果统计
        """
        batch_size = batch_size or self.batch_size
        batch_id = f"ai_batch_{int(time.time())}_{self.total_sessions}"
        start_time = time.time()
        
        logger.info(f"🚀 开始处理批次: {batch_id} (大小={batch_size})")
        
        try:
            # === 阶段1: 数据准备 ===
            logger.info("📋 阶段1: 数据准备...")
            stage1_start = time.time()
            
            batch_data = self.data_pipeline.prepare_batch_data(batch_size)
            jd_candidates = batch_data['jd_candidates']
            
            stage1_time = (time.time() - stage1_start) * 1000
            logger.info(f"✅ 阶段1完成: {len(jd_candidates)} 条候选消息, 耗时={stage1_time:.0f}ms")
            
            if not jd_candidates:
                logger.info("无待处理的JD候选消息")
                return self._create_empty_result(batch_id, "无待处理消息")
            
            # === 阶段2: 智能提取 ===
            logger.info("🧠 阶段2: 智能提取...")
            stage2_start = time.time()
            
            # 使用智能批处理方法
            extraction_results = self.llm_extractor.process_batch(jd_candidates)
            
            stage2_time = (time.time() - stage2_start) * 1000
            successful_extractions = len([r for _, r in extraction_results if r is not None])
            
            # 获取详细统计
            stats = self.llm_extractor.get_extraction_stats()
            cache_info = f", 缓存命中={stats['cache_hits']}/{stats['total_processed']}" if stats['use_cache'] else ""
            parallel_info = f", 并行处理={stats['parallel_extraction']}" if stats['parallel_extraction'] else ""
            
            log_message = f"✅ 阶段2完成: {successful_extractions}/{len(extraction_results)} 条成功提取, "
            log_message += f"耗时={stage2_time:.0f}ms{cache_info}{parallel_info}"
            logger.info(log_message)
            
            # === 阶段3: 结果输出 ===
            logger.info("💾 阶段3: 结果输出...")
            stage3_start = time.time()
            
            processing_summary = self.result_processor.process_batch_results(extraction_results)
            
            stage3_time = (time.time() - stage3_start) * 1000
            logger.info(f"✅ 阶段3完成: {processing_summary['saved_count']} 条结果保存, 耗时={stage3_time:.0f}ms")
            
            # === 生成综合统计 ===
            total_time = (time.time() - start_time) * 1000
            
            # 更新全局统计
            self.total_sessions += 1
            self.total_processed_messages += len(batch_data['raw_messages'])
            self.total_extracted_jobs += processing_summary['saved_count']
            
            result = {
                'batch_id': batch_id,
                'success': True,
                'message': '批次处理完成',
                'timing': {
                    'stage1_data_preparation_ms': int(stage1_time),
                    'stage2_llm_extraction_ms': int(stage2_time),
                    'stage3_result_processing_ms': int(stage3_time),
                    'total_processing_ms': int(total_time)
                },
                'data_flow': {
                    'input_messages': len(batch_data['raw_messages']),
                    'jd_candidates': len(jd_candidates),
                    'extraction_attempts': len(extraction_results),
                    'successful_extractions': successful_extractions,
                    'validated_results': processing_summary['validated_count'],
                    'saved_results': processing_summary['saved_count']
                },
                'quality_metrics': {
                    'filter_ratio': batch_data['filter_ratio'],
                    'extraction_success_rate': successful_extractions / max(len(extraction_results), 1),
                    'validation_success_rate': processing_summary['success_rate'],
                    'average_confidence': processing_summary['average_confidence']
                }
            }
            
            logger.info(f"🎉 批次 {batch_id} 处理完成: "
                       f"输入={result['data_flow']['input_messages']}, "
                       f"输出={result['data_flow']['saved_results']}, "
                       f"耗时={result['timing']['total_processing_ms']}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 批次 {batch_id} 处理失败: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'batch_id': batch_id,
                'success': False,
                'message': f'批次处理失败: {str(e)}',
                'error': str(e)
            }
    
    def _create_empty_result(self, batch_id: str, message: str) -> Dict:
        """创建空结果"""
        return {
            'batch_id': batch_id,
            'success': True,
            'message': message,
            'timing': {'total_processing_ms': 0},
            'data_flow': {
                'input_messages': 0,
                'jd_candidates': 0,
                'saved_results': 0
            },
            'quality_metrics': {
                'filter_ratio': 0.0,
                'extraction_success_rate': 0.0,
                'validation_success_rate': 0.0
            }
        }

# 测试工具
def test_ai_job_processor():
    """测试AI-JD处理器"""
    print("=== 测试AI-JD处理器 ===")
    
    try:
        # 测试初始化
        print("\n1. 测试初始化:")
        # 使用配置文件中的设置
        processor = AIJobProcessor()
        print("   ✅ AI-JD处理器初始化成功")
        
        # 测试系统设置
        print("\n2. 测试系统设置:")
        setup_success = processor.setup_system()
        if setup_success:
            print("   ✅ 系统设置成功")
        else:
            print("   ❌ 系统设置失败")
            return False
        
        # 测试单批次处理
        print("\n3. 测试单批次处理:")
        batch_result = processor.process_single_batch(batch_size=20)  # 增加批次大小以包含JD消息
        
        if batch_result['success']:
            print("   ✅ 单批次处理成功:")
            print(f"   - 批次ID: {batch_result['batch_id']}")
            print(f"   - 输入消息: {batch_result['data_flow']['input_messages']}")
            print(f"   - JD候选: {batch_result['data_flow']['jd_candidates']}")
            print(f"   - 保存结果: {batch_result['data_flow']['saved_results']}")
            print(f"   - 总耗时: {batch_result['timing']['total_processing_ms']}ms")
            
            # 显示阶段耗时
            timing = batch_result['timing']
            if 'stage1_data_preparation_ms' in timing:
                print(f"   - 阶段1耗时: {timing['stage1_data_preparation_ms']}ms")
                print(f"   - 阶段2耗时: {timing['stage2_llm_extraction_ms']}ms")
                print(f"   - 阶段3耗时: {timing['stage3_result_processing_ms']}ms")
            
            # 显示质量指标
            quality = batch_result['quality_metrics']
            print(f"   - 过滤比例: {quality.get('filter_ratio', 0.0):.2%}")
            print(f"   - 提取成功率: {quality.get('extraction_success_rate', 0.0):.2%}")
            print(f"   - 验证成功率: {quality.get('validation_success_rate', 0.0):.2%}")
            print(f"   - 平均置信度: {quality.get('average_confidence', 0.0):.2f}")
        else:
            print(f"   ❌ 单批次处理失败: {batch_result['message']}")
        
        print("\n✅ AI作业处理器测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ AI作业处理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ai_job_processor()
 