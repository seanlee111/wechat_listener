"""
AI模块数据模型
定义所有数据结构和验证规则
"""

from .schemas.message_schema import MessageSchema, MessageType, ProcessedMessage
from .schemas.jd_schema import (
    JDSchema, 
    ExtractionResult, 
    ProcessingBatch,
    WorkType, 
    WorkMode, 
    EducationLevel
)

__all__ = [
    # 消息模型
    "MessageSchema",
    "MessageType", 
    "ProcessedMessage",
    
    # JD模型
    "JDSchema",
    "ExtractionResult",
    "ProcessingBatch",
    
    # 枚举类型
    "WorkType",
    "WorkMode",
    "EducationLevel"
] 