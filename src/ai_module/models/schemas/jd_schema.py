"""
JD信息数据模型
定义招聘信息的结构化数据格式
"""

from pydantic import BaseModel, Field, validator, EmailStr
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import re


class WorkType(str, Enum):
    """工作类型枚举"""
    FULL_TIME = "全职"
    PART_TIME = "兼职"
    INTERNSHIP = "实习"
    CONTRACT = "合同工"
    FREELANCE = "自由职业"
    OTHER = "其他"


class WorkMode(str, Enum):
    """工作模式枚举"""
    ONSITE = "现场"
    REMOTE = "远程"
    HYBRID = "混合"
    FLEXIBLE = "灵活"


class EducationLevel(str, Enum):
    """学历要求枚举"""
    HIGH_SCHOOL = "高中"
    COLLEGE = "大专"
    BACHELOR = "本科"
    MASTER = "硕士"
    DOCTORATE = "博士"
    UNLIMITED = "不限"


class JDSchema(BaseModel):
    """JD信息核心数据模型"""
    
    # 基本信息
    company_name: Optional[str] = Field(None, description="公司名称", max_length=255)
    position_title: Optional[str] = Field(None, description="职位名称", max_length=255)
    work_location: Optional[str] = Field(None, description="工作地点", max_length=255)
    
    # 薪资信息
    salary_range: Optional[str] = Field(None, description="薪资范围", max_length=100)
    salary_min: Optional[float] = Field(None, description="最低薪资", ge=0)
    salary_max: Optional[float] = Field(None, description="最高薪资", ge=0)
    salary_unit: Optional[str] = Field(None, description="薪资单位", max_length=10)
    
    # 联系方式
    contact_email: Optional[str] = Field(None, description="联系邮箱")
    contact_phone: Optional[str] = Field(None, description="联系电话", max_length=20)
    contact_wechat: Optional[str] = Field(None, description="微信号", max_length=100)
    contact_person: Optional[str] = Field(None, description="联系人", max_length=50)
    
    # 详细要求
    job_requirements: Optional[str] = Field(None, description="岗位要求")
    education_requirement: Optional[EducationLevel] = Field(None, description="学历要求")
    experience_requirement: Optional[str] = Field(None, description="经验要求", max_length=100)
    skill_requirements: Optional[List[str]] = Field(None, description="技能要求")
    
    # 工作属性
    work_type: Optional[WorkType] = Field(None, description="工作类型")
    work_mode: Optional[WorkMode] = Field(None, description="工作模式")
    department: Optional[str] = Field(None, description="部门", max_length=100)
    
    # 福利待遇
    benefits: Optional[List[str]] = Field(None, description="福利待遇")
    working_hours: Optional[str] = Field(None, description="工作时间", max_length=100)
    
    class Config:
        """模型配置"""
        use_enum_values = True
        schema_extra = {
            "example": {
                "company_name": "阿里巴巴",
                "position_title": "Java高级开发工程师",
                "work_location": "杭州",
                "salary_range": "20-30K",
                "contact_email": "hr@alibaba.com",
                "job_requirements": "熟练掌握Java、Spring等技术栈",
                "education_requirement": "本科",
                "experience_requirement": "3-5年",
                "work_type": "全职",
                "work_mode": "现场"
            }
        }
    
    @validator('contact_email')
    def validate_email(cls, v):
        """验证邮箱格式"""
        if v is None:
            return v
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("邮箱格式无效")
        return v
    
    @validator('contact_phone')
    def validate_phone(cls, v):
        """验证电话格式"""
        if v is None:
            return v
        
        # 简单的电话格式验证
        phone_pattern = r'^[\d\-\+\(\)\s]{7,20}$'
        if not re.match(phone_pattern, v):
            raise ValueError("电话格式无效")
        return v
    
    @validator('salary_min', 'salary_max')
    def validate_salary(cls, v):
        """验证薪资范围"""
        if v is not None and (v < 0 or v > 1000000):
            raise ValueError("薪资范围无效")
        return v
    
    def is_complete(self) -> bool:
        """检查JD信息是否完整"""
        required_fields = ['company_name', 'position_title']
        return all(getattr(self, field) is not None for field in required_fields)
    
    def has_contact_info(self) -> bool:
        """检查是否有联系方式"""
        return any([
            self.contact_email,
            self.contact_phone,
            self.contact_wechat
        ])
    
    def get_salary_info(self) -> Dict[str, Any]:
        """获取薪资信息汇总"""
        return {
            "range": self.salary_range,
            "min": self.salary_min,
            "max": self.salary_max,
            "unit": self.salary_unit,
            "avg": (self.salary_min + self.salary_max) / 2 if self.salary_min and self.salary_max else None
        }


class ExtractionResult(BaseModel):
    """AI提取结果模型"""
    
    # 关联信息
    message_id: int = Field(..., description="原始消息ID")
    extraction_method: str = Field(..., description="提取方法", max_length=50)
    model_version: str = Field(..., description="模型版本", max_length=50)
    
    # 处理元数据
    processed_at: datetime = Field(default_factory=datetime.now, description="处理时间")
    processing_time_ms: Optional[int] = Field(None, description="处理耗时(毫秒)", ge=0)
    api_cost_cents: Optional[int] = Field(None, description="API成本(分)", ge=0)
    
    # 检测结果
    is_job_posting: bool = Field(..., description="是否为招聘信息")
    jd_detection_confidence: float = Field(..., description="JD检测置信度", ge=0.0, le=1.0)
    
    # 提取的JD信息
    jd_info: Optional[JDSchema] = Field(None, description="提取的JD信息")
    
    # 字段级置信度
    field_confidences: Optional[Dict[str, float]] = Field(None, description="字段置信度")
    
    # 总体置信度和质量
    confidence_score: float = Field(..., description="总体置信度", ge=0.0, le=1.0)
    quality_score: Optional[float] = Field(None, description="质量评分", ge=0.0, le=1.0)
    
    # 原始数据
    raw_ai_response: Optional[str] = Field(None, description="原始AI响应")
    extraction_prompt: Optional[str] = Field(None, description="提取提示词")
    prompt_tokens: Optional[int] = Field(None, description="提示词token数", ge=0)
    completion_tokens: Optional[int] = Field(None, description="回复token数", ge=0)
    
    # 验证和状态
    validation_status: str = Field(default="pending", description="验证状态")
    validation_notes: Optional[str] = Field(None, description="验证备注")
    status: str = Field(default="extracted", description="处理状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        """模型配置"""
        use_enum_values = True
    
    @validator('confidence_score', 'jd_detection_confidence', 'quality_score')
    def validate_score_range(cls, v):
        """验证评分范围"""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("评分必须在0.0-1.0之间")
        return v
    
    def is_high_quality(self, threshold: float = 0.8) -> bool:
        """判断是否为高质量提取结果"""
        return (
            self.confidence_score >= threshold and
            self.is_job_posting and
            self.jd_info is not None and
            self.jd_info.is_complete()
        )
    
    def is_successful(self) -> bool:
        """判断提取是否成功"""
        return (
            self.error_message is None and
            self.confidence_score > 0.5 and
            (not self.is_job_posting or self.jd_info is not None)
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """获取提取结果摘要"""
        return {
            "message_id": self.message_id,
            "is_job_posting": self.is_job_posting,
            "confidence": self.confidence_score,
            "quality": self.quality_score,
            "company": self.jd_info.company_name if self.jd_info else None,
            "position": self.jd_info.position_title if self.jd_info else None,
            "status": self.status,
            "processed_at": self.processed_at.isoformat()
        }
    
    def to_database_dict(self) -> Dict[str, Any]:
        """转换为数据库存储格式"""
        data = {
            "message_id": self.message_id,
            "processed_at": self.processed_at.isoformat(),
            "extraction_method": self.extraction_method,
            "model_version": self.model_version,
            "confidence_score": self.confidence_score,
            "processing_time_ms": self.processing_time_ms,
            "api_cost_cents": self.api_cost_cents,
            "is_job_posting": self.is_job_posting,
            "jd_detection_confidence": self.jd_detection_confidence,
            "raw_ai_response": self.raw_ai_response,
            "extraction_prompt": self.extraction_prompt,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "quality_score": self.quality_score,
            "validation_status": self.validation_status,
            "validation_notes": self.validation_notes,
            "status": self.status,
            "error_message": self.error_message
        }
        
        # 添加JD信息字段
        if self.jd_info:
            jd_data = self.jd_info.dict()
            for field, value in jd_data.items():
                data[field] = value
                
        # 添加字段置信度
        if self.field_confidences:
            for field, confidence in self.field_confidences.items():
                data[f"{field}_confidence"] = confidence
        
        return data


class ProcessingBatch(BaseModel):
    """处理批次模型"""
    
    batch_id: str = Field(..., description="批次ID")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    status: str = Field(default="running", description="批次状态")
    
    # 统计信息
    total_messages: int = Field(default=0, description="总消息数", ge=0)
    processed_messages: int = Field(default=0, description="已处理消息数", ge=0)
    successful_extractions: int = Field(default=0, description="成功提取数", ge=0)
    failed_extractions: int = Field(default=0, description="失败提取数", ge=0)
    jd_found_count: int = Field(default=0, description="发现JD数", ge=0)
    
    # 性能指标
    total_processing_time_ms: int = Field(default=0, description="总处理时间", ge=0)
    avg_confidence_score: float = Field(default=0.0, description="平均置信度", ge=0.0, le=1.0)
    total_api_cost_cents: int = Field(default=0, description="总API成本", ge=0)
    
    # 配置信息
    provider_used: Optional[str] = Field(None, description="使用的提供商")
    model_version: Optional[str] = Field(None, description="模型版本")
    batch_size: Optional[int] = Field(None, description="批次大小", ge=1)
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.processed_messages == 0:
            return 0.0
        return self.successful_extractions / self.processed_messages
    
    def get_jd_detection_rate(self) -> float:
        """获取JD检测率"""
        if self.processed_messages == 0:
            return 0.0
        return self.jd_found_count / self.processed_messages
    
    def is_completed(self) -> bool:
        """判断批次是否完成"""
        return self.status in ["completed", "failed", "cancelled"] 