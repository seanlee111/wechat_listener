"""
数据模式定义
包含所有Pydantic数据模型
"""

from .message_schema import MessageSchema, MessageType, ProcessedMessage
from .jd_schema import (
    JDSchema,
    ExtractionResult, 
    ProcessingBatch,
    WorkType,
    WorkMode,
    EducationLevel
)

__all__ = [
    # 消息模式
    "MessageSchema",
    "MessageType",
    "ProcessedMessage",
    
    # JD模式  
    "JDSchema",
    "ExtractionResult",
    "ProcessingBatch",
    
    # 枚举类型
    "WorkType",
    "WorkMode", 
    "EducationLevel"
] 