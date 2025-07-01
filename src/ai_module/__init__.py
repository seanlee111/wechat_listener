"""
AI模块 - 人工智能功能模块
基于Core模块的数据库内容，提供AI增强功能
"""

from .jd_extractor import JDExtractor
from .message_analyzer import MessageAnalyzer

__version__ = "1.0.0"
__author__ = "AI Team"

# 导入核心组件
from .database.ai_database import AIDatabase, get_ai_database
from .config.ai_config import AIConfig, create_default_config, load_config_from_env
from .models.schemas.message_schema import MessageSchema, MessageType
from .models.schemas.jd_schema import JDSchema, ExtractionResult, ProcessingBatch

# 导入枚举类型
from .models.schemas.jd_schema import WorkType, WorkMode, EducationLevel

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    
    # 数据库
    "AIDatabase",
    "get_ai_database",
    
    # 配置
    "AIConfig", 
    "create_default_config",
    "load_config_from_env",
    
    # 数据模型
    "MessageSchema",
    "MessageType",
    "JDSchema",
    "ExtractionResult", 
    "ProcessingBatch",
    
    # 枚举类型
    "WorkType",
    "WorkMode", 
    "EducationLevel",

    "JDExtractor",
    "MessageAnalyzer"
]

# AI模块依赖core模块的数据库
try:
    from ..core_module import CoreListener
    print("AI模块成功加载Core模块依赖")
except ImportError:
    print("警告：未找到Core模块，AI模块功能可能受限") 