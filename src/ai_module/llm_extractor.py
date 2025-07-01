"""
智能提取阶段 - 阶段2
使用LLM批量提取JD信息
"""

import asyncio
import logging
import time
import hashlib
import json
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from collections import OrderedDict
import sys
from pathlib import Path

# 添加项目根目录到路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.ai_module.llm_interface import LLMFactory, LLMInterface
from src.ai_module.config import get_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        if key not in self.cache:
            return None
        # 移到最近使用
        value = self.cache.pop(key)
        self.cache[key] = value
        return value
    
    def put(self, key: str, value: Any) -> None:
        """添加缓存项"""
        if key in self.cache:
            # 移除旧值
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            # 移除最久未使用的项
            self.cache.popitem(last=False)
        # 添加新值
        self.cache[key] = value
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
    
    def __len__(self) -> int:
        """缓存大小"""
        return len(self.cache)

class LLMExtractor:
    """
    LLM智能提取器
    负责批量调用LLM进行JD信息提取
    """
    
    def __init__(self, llm_provider: Optional[str] = None, llm_config: Optional[Dict] = None):
        """
        初始化LLM提取器
        
        Args:
            llm_provider: LLM提供商 ('mock', 'volcano', 'qwen')，如果为None则从配置读取
            llm_config: LLM配置字典，如果为None则从配置读取
        """
        # 加载配置
        self.config = get_config()
        
        # 使用配置或传入参数
        self.llm_provider = llm_provider or self.config.get("llm_extractor", "provider", "mock")
        
        if llm_config is None:
            # 从配置加载API配置
            provider_config = self.config.get("llm_extractor", "api_config", {})
            self.llm_config = provider_config.get(self.llm_provider, {})
        else:
            self.llm_config = llm_config
        
        # 创建LLM接口
        self.llm_interface = LLMFactory.create_llm(self.llm_provider, self.llm_config)
        
        # 提取统计
        self.total_processed = 0
        self.total_success = 0
        self.total_failed = 0
        self.retry_count = 0
        self.cache_hits = 0
        
        # 重试配置
        self.max_retries = self.config.get("llm_extractor", "max_retries", 2)
        self.retry_delay = self.config.get("llm_extractor", "retry_delay", 2.0)  # 秒
        
        # 并行处理设置
        self.parallel_extraction = self.config.get("llm_extractor", "parallel_extraction", False)
        self.max_workers = self.config.get("llm_extractor", "max_workers", 3)
        
        # 缓存设置
        self.use_cache = self.config.get("llm_extractor", "use_cache", True)
        cache_size = self.config.get("llm_extractor", "cache_size", 1000)
        self.result_cache = LRUCache(cache_size)
        
        # 自适应超时
        self.adaptive_timeout = self.config.get("llm_extractor", "adaptive_timeout", True)
        
        logger.info(f"LLM提取器初始化完成: provider={self.llm_provider}, 并行={self.parallel_extraction}, 缓存={self.use_cache}")
    
    def _generate_cache_key(self, content: str) -> str:
        """生成缓存键"""
        # 使用内容的哈希作为缓存键
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def extract_single(self, message: Dict, retry_count: int = 0) -> Tuple[Dict, Optional[Dict]]:
        """
        提取单条消息的JD信息
        
        Args:
            message: 消息字典
            retry_count: 当前重试次数
            
        Returns:
            (原始消息, 提取结果或None)
        """
        try:
            content = message.get('content', '')
            if not content.strip():
                logger.warning(f"消息ID {message.get('id')} 内容为空")
                return message, None
            
            # 检查缓存
            if self.use_cache:
                cache_key = self._generate_cache_key(content)
                cached_result = self.result_cache.get(cache_key)
                if cached_result:
                    # 缓存命中
                    self.cache_hits += 1
                    logger.info(f"消息ID {message.get('id')} 缓存命中")
                    
                    # 复制结果并添加追溯信息
                    extraction_result = cached_result.copy()
                    extraction_result['source_message_id'] = message.get('id')
                    extraction_result['raw_message_id'] = message.get('raw_message_id')
                    extraction_result['from_cache'] = True
                    
                    self.total_success += 1
                    self.total_processed += 1
                    return message, extraction_result
            
            # 调用LLM提取
            extraction_result = self.llm_interface.extract_jd_info(content)
            
            if extraction_result:
                # 添加追溯信息
                extraction_result['source_message_id'] = message.get('id')
                extraction_result['raw_message_id'] = message.get('raw_message_id')
                extraction_result['original_content'] = content[:500]  # 保留部分原文
                extraction_result['from_cache'] = False
                
                # 保存到缓存
                if self.use_cache:
                    cache_key = self._generate_cache_key(content)
                    # 存储不带追溯信息的版本
                    cache_version = extraction_result.copy()
                    for key in ['source_message_id', 'raw_message_id', 'from_cache']:
                        cache_version.pop(key, None)
                    self.result_cache.put(cache_key, cache_version)
                
                self.total_success += 1
                logger.debug(f"消息ID {message.get('id')} 提取成功")
                return message, extraction_result
            else:
                # 尝试重试
                if retry_count < self.max_retries:
                    logger.warning(f"消息ID {message.get('id')} 提取失败，准备重试 ({retry_count+1}/{self.max_retries})")
                    self.retry_count += 1
                    # 指数退避
                    retry_delay = self.retry_delay * (2 ** retry_count)
                    time.sleep(retry_delay)
                    return self.extract_single(message, retry_count + 1)
                
                logger.warning(f"消息ID {message.get('id')} 提取失败：LLM返回空结果，已重试 {retry_count} 次")
                return message, None
                
        except Exception as e:
            logger.error(f"提取消息ID {message.get('id')} 时出错: {e}")
            
            # 尝试重试
            if retry_count < self.max_retries:
                logger.warning(f"消息ID {message.get('id')} 提取出错，准备重试 ({retry_count+1}/{self.max_retries})")
                self.retry_count += 1
                # 指数退避
                retry_delay = self.retry_delay * (2 ** retry_count)
                time.sleep(retry_delay)
                return self.extract_single(message, retry_count + 1)
            
            self.total_failed += 1
            return message, None
        finally:
            if retry_count == 0:  # 只在初始调用时计数
                self.total_processed += 1
    
    def extract_batch_sequential(self, messages: List[Dict]) -> List[Tuple[Dict, Optional[Dict]]]:
        """
        顺序批量提取 (同步)
        
        Args:
            messages: 消息列表
            
        Returns:
            [(原始消息, 提取结果)] 列表
        """
        logger.info(f"开始顺序批量提取 {len(messages)} 条消息")
        
        results = []
        start_time = time.time()
        
        for i, message in enumerate(messages):
            logger.info(f"处理进度: {i+1}/{len(messages)}")
            result = self.extract_single(message)
            results.append(result)
        
        duration = time.time() - start_time
        logger.info(f"顺序批量提取完成: 耗时={duration:.2f}秒, 成功={self.total_success}, 失败={self.total_failed}, 缓存命中={self.cache_hits}")
        
        return results
        
    def extract_batch_parallel(self, messages: List[Dict]) -> List[Tuple[Dict, Optional[Dict]]]:
        """
        并行批量提取 (使用线程池)
        
        Args:
            messages: 消息列表
            
        Returns:
            [(原始消息, 提取结果)] 列表
        """
        logger.info(f"开始并行批量提取 {len(messages)} 条消息 (最大并行数: {self.max_workers})")
        
        results = []
        start_time = time.time()
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_message = {
                executor.submit(self.extract_single, message): message 
                for message in messages
            }
            
            # 处理完成的任务
            for i, future in enumerate(as_completed(future_to_message)):
                message = future_to_message[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"并行处理进度: {i+1}/{len(messages)}")
                except Exception as e:
                    logger.error(f"并行处理消息ID {message.get('id')} 时出错: {e}")
                    results.append((message, None))
        
        # 按原始顺序排序结果
        message_id_to_result = {msg.get('id'): result for msg, result in results}
        ordered_results = [(msg, message_id_to_result.get(msg.get('id'))) for msg in messages]
        
        duration = time.time() - start_time
        logger.info(f"并行批量提取完成: 耗时={duration:.2f}秒, 成功={self.total_success}, 失败={self.total_failed}, 缓存命中={self.cache_hits}")
        
        return ordered_results
    
    async def extract_single_async(self, message: Dict) -> Tuple[Dict, Optional[Dict]]:
        """
        异步提取单条消息 (使用线程池包装同步方法)
        
        Args:
            message: 消息字典
            
        Returns:
            (原始消息, 提取结果)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.extract_single, message)
    
    async def extract_batch_async(self, messages: List[Dict]) -> List[Tuple[Dict, Optional[Dict]]]:
        """
        异步批量提取
        
        Args:
            messages: 消息列表
            
        Returns:
            [(原始消息, 提取结果)] 列表
        """
        logger.info(f"开始异步批量提取 {len(messages)} 条消息")
        
        start_time = time.time()
        
        # 创建所有任务
        tasks = [self.extract_single_async(message) for message in messages]
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"异步处理消息 #{i} 时出错: {result}")
                processed_results.append((messages[i], None))
            else:
                processed_results.append(result)
        
        duration = time.time() - start_time
        logger.info(f"异步批量提取完成: 耗时={duration:.2f}秒, 成功={self.total_success}, 失败={self.total_failed}, 缓存命中={self.cache_hits}")
        
        return processed_results
    
    def process_batch(self, messages: List[Dict]) -> List[Tuple[Dict, Optional[Dict]]]:
        """
        智能批处理 - 根据配置选择最佳处理方式
        
        Args:
            messages: 消息列表
            
        Returns:
            [(原始消息, 提取结果)] 列表
        """
        if not messages:
            logger.info("没有消息需要处理")
            return []
        
        # 重置统计
        self.reset_stats()
        
        # 根据配置选择处理方式
        if self.parallel_extraction:
            return self.extract_batch_parallel(messages)
        else:
            return self.extract_batch_sequential(messages)
    
    async def process_batch_async(self, messages: List[Dict]) -> List[Tuple[Dict, Optional[Dict]]]:
        """
        异步智能批处理
        
        Args:
            messages: 消息列表
            
        Returns:
            [(原始消息, 提取结果)] 列表
        """
        if not messages:
            logger.info("没有消息需要处理")
            return []
        
        # 重置统计
        self.reset_stats()
        
        # 使用异步处理
        return await self.extract_batch_async(messages)
    
    def get_extraction_stats(self) -> Dict:
        """获取提取统计信息"""
        return {
            'total_processed': self.total_processed,
            'total_success': self.total_success,
            'total_failed': self.total_failed,
            'success_rate': self.total_success / max(self.total_processed, 1),
            'retry_count': self.retry_count,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': self.cache_hits / max(self.total_processed, 1),
            'llm_provider': self.llm_provider,
            'parallel_extraction': self.parallel_extraction,
            'use_cache': self.use_cache
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.total_processed = 0
        self.total_success = 0
        self.total_failed = 0
        self.retry_count = 0
        self.cache_hits = 0
        logger.info("提取统计信息已重置")

# 测试工具
def test_llm_extractor():
    """测试LLM提取器"""
    print("=== 测试LLM提取器 ===")
    
    # 准备测试数据
    test_messages = [
        {
            'id': 1,
            'raw_message_id': 101,
            'content': """【实习生招聘】银河证券研究所机械行业日常实习生
工作地点：上海市浦东新区/线上

【任职要求】
1、重点高校本科/硕士在校学生
2、机械、电气、金融等相关专业优先考虑
3、3个月及以上的连续实习

简历请发送至：yhzq_yj_jx@163.com"""
        },
        {
            'id': 2,
            'raw_message_id': 102,
            'content': """【实习招聘】华泰证券总部 金融衍生品研发助理
工作地点：南京

职位要求:
1、国内外重点院校硕士，金融学相关专业优先
2、实习时间3个月以上

投递邮箱：derivatives_intern@163.com"""
        },
        # 添加重复消息测试缓存
        {
            'id': 3,
            'raw_message_id': 103,
            'content': """【实习生招聘】银河证券研究所机械行业日常实习生
工作地点：上海市浦东新区/线上

【任职要求】
1、重点高校本科/硕士在校学生
2、机械、电气、金融等相关专业优先考虑
3、3个月及以上的连续实习

简历请发送至：yhzq_yj_jx@163.com"""
        }
    ]
    
    try:
        # 测试初始化
        print("\n1. 测试初始化:")
        extractor = LLMExtractor(llm_provider='mock')
        print(f"   ✅ 提取器初始化成功: {extractor.llm_provider}")
        print(f"   - 并行处理: {extractor.parallel_extraction}")
        print(f"   - 缓存启用: {extractor.use_cache}")
        print(f"   - 最大并行数: {extractor.max_workers}")
        
        # 测试单条提取
        print("\n2. 测试单条提取:")
        msg, result = extractor.extract_single(test_messages[0])
        if result:
            print(f"   ✅ 单条提取成功")
            print(f"   - 公司: {result.get('company_name')}")
            print(f"   - 职位: {result.get('position_title')}")
            print(f"   - 邮箱: {result.get('contact_email')}")
            print(f"   - 置信度: {result.get('llm_confidence', 0):.2f}")
            print(f"   - 来自缓存: {result.get('from_cache', False)}")
        else:
            print("   ❌ 单条提取失败")
        
        # 测试智能批处理
        print("\n3. 测试智能批处理:")
        extractor.reset_stats()
        results = extractor.process_batch(test_messages)
        print(f"   ✅ 批量处理完成: {len(results)} 条结果")
        
        # 显示统计
        stats = extractor.get_extraction_stats()
        print(f"   - 成功率: {stats['success_rate']:.2%}")
        print(f"   - 处理总数: {stats['total_processed']}")
        print(f"   - 缓存命中: {stats['cache_hits']}")
        print(f"   - 缓存命中率: {stats['cache_hit_rate']:.2%}")
        
        # 测试缓存效果
        print("\n4. 测试缓存效果:")
        # 重新处理相同消息，应该命中缓存
        extractor.reset_stats()
        msg, result = extractor.extract_single(test_messages[0])
        if result and result.get('from_cache'):
            print(f"   ✅ 缓存命中成功")
        else:
            print(f"   ❌ 缓存未命中")
        
        # 测试并行处理
        print("\n5. 测试并行处理:")
        # 临时启用并行处理
        old_parallel = extractor.parallel_extraction
        extractor.parallel_extraction = True
        extractor.reset_stats()
        results = extractor.process_batch(test_messages)
        print(f"   ✅ 并行处理完成: {len(results)} 条结果")
        stats = extractor.get_extraction_stats()
        print(f"   - 成功率: {stats['success_rate']:.2%}")
        print(f"   - 缓存命中: {stats['cache_hits']}")
        # 恢复设置
        extractor.parallel_extraction = old_parallel
        
        print("\n✅ LLM提取器测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ LLM提取器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_llm_extractor() 