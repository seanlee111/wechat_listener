"""
AI模块配置文件
集中管理所有AI处理管线的配置参数
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "ai_config.json"

# 默认配置
DEFAULT_CONFIG = {
    # 数据管道配置
    "data_pipeline": {
        "batch_size": 20,
        "jd_detection_threshold": 0.4,
        "min_content_length": 30
    },
    
    # LLM提取器配置
    "llm_extractor": {
        "provider": "volcano",  # 'mock', 'volcano', 'qwen'
        "api_config": {
            "volcano": {
                "api_key": "61d9c899-c2eb-44b6-b8bf-7c260482a1cd",  # 请替换为环境变量
                "endpoint": "ep-20250701172601-hjn5s",
                "timeout": 60
            },
            "qwen": {
                "api_key": "",
                "model_name": "qwen-max"
            }
        },
        "max_retries": 2,
        "parallel_extraction": False
    },
    
    # 结果处理器配置
    "result_processor": {
        "min_confidence_threshold": 0.5,
        "required_fields": ["company_name"],
        "quality_score_threshold": 0.5
    },
    
    # 系统配置
    "system": {
        "debug_mode": False,
        "log_level": "INFO",
        "save_extraction_history": True
    }
}

class AIConfig:
    """AI模块配置管理器"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(AIConfig, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置"""
        try:
            # 确保配置目录存在
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            # 如果配置文件不存在，创建默认配置
            if not CONFIG_FILE.exists():
                logger.info(f"配置文件不存在，创建默认配置: {CONFIG_FILE}")
                self._config = DEFAULT_CONFIG
                self._save_config()
            else:
                # 读取配置文件
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info(f"成功加载配置文件: {CONFIG_FILE}")
                
                # 检查并补充缺失的配置项
                self._update_missing_config()
        except Exception as e:
            logger.error(f"加载配置失败，使用默认配置: {e}")
            self._config = DEFAULT_CONFIG
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            logger.info(f"配置已保存到: {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def _update_missing_config(self):
        """更新缺失的配置项"""
        updated = False
        
        def update_dict(target, source):
            nonlocal updated
            for key, value in source.items():
                if key not in target:
                    target[key] = value
                    updated = True
                elif isinstance(value, dict) and isinstance(target[key], dict):
                    update_dict(target[key], value)
        
        update_dict(self._config, DEFAULT_CONFIG)
        
        if updated:
            logger.info("配置已更新，添加了缺失的配置项")
            self._save_config()
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            section: 配置部分名称
            key: 配置键名，如果为None则返回整个部分
            default: 默认值，如果配置不存在则返回此值
            
        Returns:
            配置值
        """
        try:
            if section not in self._config:
                return default
            
            if key is None:
                return self._config[section]
            
            return self._config[section].get(key, default)
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return default
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """
        设置配置项
        
        Args:
            section: 配置部分名称
            key: 配置键名
            value: 配置值
            
        Returns:
            是否设置成功
        """
        try:
            if section not in self._config:
                self._config[section] = {}
            
            self._config[section][key] = value
            self._save_config()
            return True
        except Exception as e:
            logger.error(f"设置配置失败: {e}")
            return False
    
    def get_all(self) -> Dict:
        """获取所有配置"""
        return self._config.copy()
    
    def reload(self) -> bool:
        """重新加载配置"""
        try:
            self._load_config()
            return True
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            return False

# 全局配置实例
config = AIConfig()

def get_config() -> AIConfig:
    """获取配置实例"""
    return config

# 测试函数
def test_config():
    """测试配置功能"""
    print("=== 测试AI配置管理 ===")
    
    # 获取配置实例
    config = get_config()
    
    # 测试读取配置
    print("\n1. 读取配置:")
    batch_size = config.get("data_pipeline", "batch_size")
    provider = config.get("llm_extractor", "provider")
    confidence = config.get("result_processor", "min_confidence_threshold")
    
    print(f"   - 批处理大小: {batch_size}")
    print(f"   - LLM提供商: {provider}")
    print(f"   - 最小置信度阈值: {confidence}")
    
    # 测试修改配置
    print("\n2. 修改配置:")
    old_value = config.get("system", "debug_mode")
    success = config.set("system", "debug_mode", not old_value)
    new_value = config.get("system", "debug_mode")
    
    print(f"   - 修改前: debug_mode = {old_value}")
    print(f"   - 修改后: debug_mode = {new_value}")
    print(f"   - 修改状态: {'成功' if success else '失败'}")
    
    # 测试添加新配置
    print("\n3. 添加新配置:")
    success = config.set("custom", "test_value", "这是测试值")
    value = config.get("custom", "test_value")
    
    print(f"   - 新配置值: {value}")
    print(f"   - 添加状态: {'成功' if success else '失败'}")
    
    # 恢复原始配置
    config.set("system", "debug_mode", old_value)
    config.set("custom", "test_value", None)
    
    print("\n✅ 配置测试完成!")

if __name__ == "__main__":
    test_config() 