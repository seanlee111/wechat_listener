"""
AI模块
微信群聊智能监听与JD信息提取AI模块

主要功能:
- 基于大模型的JD信息智能识别与结构化提取
- 多提供商支持 (OpenAI, Claude, 通义千问)
- 完整的质量控制和验证系统
- 企业级监控和告警系统
"""

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
    "EducationLevel"
] 