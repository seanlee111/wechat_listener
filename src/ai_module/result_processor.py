"""
结果输出阶段 - 阶段3
处理LLM提取结果，进行质量验证并保存到数据库
"""

import logging
import time
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.ai_module.ai_database_extension import AIDatabaseExtension
from src.ai_module.config import get_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResultProcessor:
    """
    结果处理器
    负责处理LLM提取结果、质量验证和数据保存
    """
    
    def __init__(self, ai_db: Optional[AIDatabaseExtension] = None):
        """
        初始化结果处理器
        
        Args:
            ai_db: AI数据库扩展实例
        """
        self.ai_db = ai_db or AIDatabaseExtension()
        
        # 加载配置
        self.config = get_config()
        
        # 质量验证配置
        self.min_confidence_threshold = self.config.get("result_processor", "min_confidence_threshold", 0.7)
        self.required_fields = self.config.get("result_processor", "required_fields", 
                                              ['company_name', 'position_title', 'contact_email'])
        self.quality_score_threshold = self.config.get("result_processor", "quality_score_threshold", 0.7)
        
        # 处理统计
        self.processed_count = 0
        self.validated_count = 0
        self.rejected_count = 0
        self.saved_count = 0
        
        logger.info("结果处理器初始化完成")
    
    def validate_extraction_quality(self, extraction_result: Dict) -> Tuple[bool, str, float]:
        """
        验证提取结果的质量
        
        Args:
            extraction_result: LLM提取结果
            
        Returns:
            (是否通过验证, 验证反馈, 质量评分)
        """
        try:
            quality_score = 0.0
            feedback_messages = []
            
            # 1. 置信度检查
            confidence = extraction_result.get('llm_confidence', 0.0)
            if confidence >= self.min_confidence_threshold:
                quality_score += 0.3
            else:
                feedback_messages.append(f"置信度过低: {confidence:.2f} < {self.min_confidence_threshold}")
            
            # 2. 必需字段检查
            missing_fields = []
            for field in self.required_fields:
                value = extraction_result.get(field)
                if value and str(value).strip():
                    quality_score += 0.2
                else:
                    missing_fields.append(field)
            
            if missing_fields:
                feedback_messages.append(f"缺少必需字段: {', '.join(missing_fields)}")
            
            # 3. 邮箱格式验证
            email = extraction_result.get('contact_email', '')
            if email and '@' in email and '.' in email:
                quality_score += 0.2
            elif email:
                feedback_messages.append(f"邮箱格式疑似错误: {email}")
            
            # 4. 公司名称合理性检查
            company = extraction_result.get('company_name', '')
            if company and len(company) > 1 and len(company) < 50:
                quality_score += 0.15
            elif company:
                feedback_messages.append(f"公司名称长度异常: {len(company)} 字符")
            
            # 5. 职位名称合理性检查
            position = extraction_result.get('position_title', '')
            if position and len(position) > 1 and len(position) < 100:
                quality_score += 0.15
            elif position:
                feedback_messages.append(f"职位名称长度异常: {len(position)} 字符")
            
            # 判断是否通过验证
            is_valid = quality_score >= self.quality_score_threshold and not missing_fields
            feedback = '; '.join(feedback_messages) if feedback_messages else '质量检查通过'
            
            logger.debug(f"质量验证完成: 评分={quality_score:.2f}, 通过={is_valid}")
            return is_valid, feedback, quality_score
            
        except Exception as e:
            logger.error(f"质量验证失败: {e}")
            return False, f"验证过程出错: {str(e)}", 0.0
    
    def enhance_extraction_result(self, extraction_result: Dict) -> Dict:
        """
        增强提取结果，添加额外的处理信息
        
        Args:
            extraction_result: 原始提取结果
            
        Returns:
            增强后的提取结果
        """
        enhanced_result = extraction_result.copy()
        
        try:
            # 1. 数据清洗
            for field in ['company_name', 'position_title', 'work_location']:
                value = enhanced_result.get(field)
                if value:
                    # 去除多余空白字符和换行符
                    cleaned_value = ' '.join(str(value).split())
                    enhanced_result[field] = cleaned_value
            
            # 2. 邮箱标准化
            email = enhanced_result.get('contact_email')
            if email:
                enhanced_result['contact_email'] = str(email).strip().lower()
            
            # 3. 添加处理时间戳
            enhanced_result['processing_timestamp'] = datetime.now().isoformat()
            
            # 4. 生成投递准备标记
            is_ready = all([
                enhanced_result.get('company_name'),
                enhanced_result.get('position_title'),
                enhanced_result.get('contact_email'),
                enhanced_result.get('llm_confidence', 0) > 0.8
            ])
            enhanced_result['ready_for_delivery'] = is_ready
            
            # 5. 生成唯一标识
            import hashlib
            content_hash = hashlib.md5(
                f"{enhanced_result.get('company_name', '')}"
                f"{enhanced_result.get('position_title', '')}"
                f"{enhanced_result.get('contact_email', '')}".encode()
            ).hexdigest()[:8]
            enhanced_result['content_hash'] = content_hash
            
            logger.debug("提取结果增强完成")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"增强提取结果失败: {e}")
            return extraction_result
    
    def process_single_result(self, message: Dict, extraction_result: Optional[Dict]) -> Dict:
        """
        处理单个提取结果
        
        Args:
            message: 原始消息
            extraction_result: LLM提取结果
            
        Returns:
            处理结果统计
        """
        processing_stats = {
            'processed': False,
            'validated': False,
            'saved': False,
            'feedback': '',
            'quality_score': 0.0
        }
        
        try:
            self.processed_count += 1
            
            # 如果没有提取结果，直接返回
            if not extraction_result:
                processing_stats['feedback'] = '无提取结果'
                return processing_stats
            
            processing_stats['processed'] = True
            
            # 质量验证
            is_valid, feedback, quality_score = self.validate_extraction_quality(extraction_result)
            processing_stats['feedback'] = feedback
            processing_stats['quality_score'] = quality_score
            
            if is_valid:
                self.validated_count += 1
                processing_stats['validated'] = True
                
                # 增强结果
                enhanced_result = self.enhance_extraction_result(extraction_result)
                
                # 保存到数据库
                try:
                    record_id = self.ai_db.save_extraction_result(enhanced_result)
                    if record_id > 0:
                        self.saved_count += 1
                        processing_stats['saved'] = True
                        logger.debug(f"提取结果已保存: 消息ID={message.get('id')}, 记录ID={record_id}")
                    else:
                        processing_stats['feedback'] += '; 数据库保存失败'
                except Exception as e:
                    processing_stats['feedback'] += f'; 保存出错: {str(e)}'
            else:
                self.rejected_count += 1
                logger.debug(f"提取结果质量不达标: 消息ID={message.get('id')}, 反馈={feedback}")
            
            return processing_stats
            
        except Exception as e:
            logger.error(f"处理单个结果失败: {e}")
            processing_stats['feedback'] = f'处理出错: {str(e)}'
            return processing_stats
    
    def process_batch_results(self, batch_results: List[Tuple[Dict, Optional[Dict]]]) -> Dict:
        """
        批量处理提取结果
        
        Args:
            batch_results: [(原始消息, 提取结果)] 列表
            
        Returns:
            处理统计信息
        """
        logger.info(f"开始批量处理 {len(batch_results)} 个提取结果")
        start_time = time.time()
        
        # 重置统计
        self.processed_count = 0
        self.validated_count = 0
        self.rejected_count = 0
        self.saved_count = 0
        
        batch_stats = []
        
        for i, (message, extraction_result) in enumerate(batch_results):
            if i > 0 and i % 10 == 0:
                logger.info(f"处理进度: {i}/{len(batch_results)}")
            
            result_stats = self.process_single_result(message, extraction_result)
            batch_stats.append(result_stats)
        
        processing_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        # 计算成功率和置信度统计
        valid_results = [stats for stats in batch_stats if stats['validated']]
        avg_confidence = sum(stats['quality_score'] for stats in valid_results) / max(len(valid_results), 1)
        
        summary = {
            'total_processed': self.processed_count,
            'validated_count': self.validated_count,
            'rejected_count': self.rejected_count,
            'saved_count': self.saved_count,
            'success_rate': self.validated_count / max(self.processed_count, 1),
            'save_rate': self.saved_count / max(self.validated_count, 1) if self.validated_count > 0 else 0,
            'average_confidence': avg_confidence,
            'processing_time_ms': int(processing_time),
            'batch_stats': batch_stats
        }
        
        logger.info(f"批量处理完成: 成功率={summary['success_rate']:.2%}, "
                   f"保存率={summary['save_rate']:.2%}, 耗时={processing_time:.0f}ms")
        
        return summary
    
    def create_processing_report(self, batch_summary: Dict, batch_id: str = None) -> Dict:
        """
        创建处理报告
        
        Args:
            batch_summary: 批量处理统计
            batch_id: 批次ID
            
        Returns:
            处理报告
        """
        now = datetime.now().isoformat()
        
        report = {
            'batch_id': batch_id or f"batch_{int(time.time())}",
            'report_timestamp': now,
            'summary': batch_summary,
            'quality_analysis': {
                'high_quality_count': len([s for s in batch_summary['batch_stats'] 
                                         if s['quality_score'] >= 0.9]),
                'medium_quality_count': len([s for s in batch_summary['batch_stats'] 
                                           if 0.7 <= s['quality_score'] < 0.9]),
                'low_quality_count': len([s for s in batch_summary['batch_stats'] 
                                        if s['quality_score'] < 0.7]),
            },
            'recommendations': self._generate_recommendations(batch_summary)
        }
        
        return report
    
    def _generate_recommendations(self, batch_summary: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        success_rate = batch_summary['success_rate']
        if success_rate < 0.5:
            recommendations.append("提取成功率较低，建议检查LLM模型配置或消息预筛选逻辑")
        
        save_rate = batch_summary['save_rate']
        if save_rate < 0.9:
            recommendations.append("保存成功率不理想，建议检查数据库连接和表结构")
        
        avg_confidence = batch_summary['average_confidence']
        if avg_confidence < 0.8:
            recommendations.append("平均置信度偏低，建议优化LLM提示词或更换模型")
        
        if not recommendations:
            recommendations.append("处理质量良好，系统运行正常")
        
        return recommendations
    
    def get_processing_stats(self) -> Dict:
        """获取处理统计信息"""
        return {
            'processed_count': self.processed_count,
            'validated_count': self.validated_count,
            'rejected_count': self.rejected_count,
            'saved_count': self.saved_count,
            'success_rate': self.validated_count / max(self.processed_count, 1),
            'save_rate': self.saved_count / max(self.validated_count, 1) if self.validated_count > 0 else 0
        }

# 测试工具
def test_result_processor():
    """测试结果处理器"""
    print("=== 测试结果处理器 ===")
    
    # 准备测试数据
    test_batch_results = [
        # 高质量结果
        (
            {'id': 1, 'raw_message_id': 101},
            {
                'source_message_id': 1,
                'raw_message_id': 101,
                'company_name': '银河证券研究所',
                'position_title': '机械行业日常实习生',
                'work_location': '上海市浦东新区',
                'contact_email': 'yhzq_yj_jx@163.com',
                'llm_confidence': 0.95,
                'model_used': 'test_model'
            }
        ),
        # 中等质量结果
        (
            {'id': 2, 'raw_message_id': 102},
            {
                'source_message_id': 2,
                'raw_message_id': 102,
                'company_name': '华泰证券',
                'position_title': '金融衍生品研发助理',
                'contact_email': 'derivatives_intern@163.com',
                'llm_confidence': 0.75,
                'model_used': 'test_model'
            }
        ),
        # 低质量结果 (缺少必需字段)
        (
            {'id': 3, 'raw_message_id': 103},
            {
                'source_message_id': 3,
                'raw_message_id': 103,
                'company_name': '某公司',
                'llm_confidence': 0.6,
                'model_used': 'test_model'
            }
        ),
        # 无提取结果
        (
            {'id': 4, 'raw_message_id': 104},
            None
        )
    ]
    
    try:
        # 测试初始化
        print("\n1. 测试初始化:")
        processor = ResultProcessor()
        print("   ✅ 结果处理器初始化成功")
        
        # 确保AI表存在
        print("\n2. 设置AI数据库表:")
        processor.ai_db.setup_ai_tables()
        print("   ✅ AI数据库表设置完成")
        
        # 测试单个结果处理
        print("\n3. 测试单个结果处理:")
        message, extraction = test_batch_results[0]
        result_stats = processor.process_single_result(message, extraction)
        print(f"   ✅ 单个结果处理完成:")
        print(f"   - 已处理: {result_stats['processed']}")
        print(f"   - 已验证: {result_stats['validated']}")
        print(f"   - 已保存: {result_stats['saved']}")
        print(f"   - 质量评分: {result_stats['quality_score']:.2f}")
        
        # 测试批量处理
        print("\n4. 测试批量处理:")
        batch_summary = processor.process_batch_results(test_batch_results)
        print(f"   ✅ 批量处理完成:")
        print(f"   - 处理总数: {batch_summary['total_processed']}")
        print(f"   - 验证通过: {batch_summary['validated_count']}")
        print(f"   - 成功保存: {batch_summary['saved_count']}")
        print(f"   - 成功率: {batch_summary['success_rate']:.2%}")
        print(f"   - 平均置信度: {batch_summary['average_confidence']:.2f}")
        
        # 测试处理报告
        print("\n5. 测试处理报告:")
        report = processor.create_processing_report(batch_summary, "test_batch_001")
        print(f"   ✅ 处理报告生成完成:")
        print(f"   - 批次ID: {report['batch_id']}")
        print(f"   - 高质量结果: {report['quality_analysis']['high_quality_count']} 条")
        print(f"   - 建议条数: {len(report['recommendations'])}")
        
        # 显示建议
        for i, recommendation in enumerate(report['recommendations'], 1):
            print(f"   - 建议{i}: {recommendation}")
        
        print("\n✅ 结果处理器测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 结果处理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_result_processor() 