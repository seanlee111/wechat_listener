"""
消息数据模型
定义AI模块处理的消息数据结构
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "Text"
    IMAGE = "Image"
    FILE = "File"
    SYSTEM = "System"
    OTHER = "Other"


class MessageSchema(BaseModel):
    """原始消息数据模型"""
    
    id: int = Field(..., description="消息ID")
    group_name: str = Field(..., description="群聊名称", min_length=1)
    sender: str = Field(..., description="发送者", min_length=1)
    content: str = Field(..., description="消息内容")
    msg_type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    timestamp: str = Field(..., description="时间戳")
    
    class Config:
        """模型配置"""
        use_enum_values = True
        schema_extra = {
            "example": {
                "id": 123,
                "group_name": "NFC金融实习分享群（一）",
                "sender": "张三",
                "content": "阿里巴巴招聘Java工程师，薪资20-30K，联系邮箱hr@alibaba.com",
                "msg_type": "Text",
                "timestamp": "2024-12-20T14:30:00"
            }
        }
    
    @validator('content')
    def validate_content(cls, v):
        """验证消息内容"""
        if not v or not v.strip():
            raise ValueError("消息内容不能为空")
        if len(v) > 10000:
            raise ValueError("消息内容过长")
        return v.strip()
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """验证时间戳格式"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("时间戳格式无效")
        return v
    
    def is_potential_jd(self) -> bool:
        """简单判断是否可能是JD信息"""
        jd_keywords = [
            "招聘", "招人", "急招", "诚招", "岗位", "职位", "工作", "实习",
            "薪资", "待遇", "工资", "月薪", "年薪", "K", "万", "元",
            "邮箱", "email", "微信", "联系", "投递", "简历",
            "要求", "技能", "经验", "学历", "本科", "研究生"
        ]
        
        content_lower = self.content.lower()
        return any(keyword in content_lower for keyword in jd_keywords)
    
    def get_content_length(self) -> int:
        """获取内容长度"""
        return len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()


class ProcessedMessage(MessageSchema):
    """已处理的消息模型"""
    
    processed_at: Optional[datetime] = Field(default=None, description="处理时间")
    processing_status: str = Field(default="pending", description="处理状态")
    processing_notes: Optional[str] = Field(default=None, description="处理备注")
    
    class Config:
        """模型配置"""
        use_enum_values = True 