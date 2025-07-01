"""
AI模块配置管理系统
统一管理AI模块的所有配置项
"""

import json
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum


class ProviderType(str, Enum):
    """大模型提供商类型"""
    OPENAI = "openai"
    CLAUDE = "claude"
    TONGYI = "tongyi"
    CUSTOM = "custom"


class QualityLevel(str, Enum):
    """质量等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"


@dataclass
class ProviderConfig:
    """大模型提供商配置"""
    
    # 基本信息
    name: str
    provider_type: ProviderType
    model: str
    api_key: str
    base_url: Optional[str] = None
    
    # API配置
    max_tokens: int = 4000
    temperature: float = 0.1
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # 限制配置
    rate_limit_rpm: int = 60  # 每分钟请求数
    rate_limit_tpm: int = 100000  # 每分钟token数
    timeout_seconds: int = 30
    max_retries: int = 3
    
    # 成本控制
    cost_per_1k_prompt_tokens: float = 0.01
    cost_per_1k_completion_tokens: float = 0.03
    daily_budget_cents: int = 1000  # 日预算(分)
    
    # 负载均衡配置
    weight: float = 1.0  # 权重，用于负载均衡
    priority: int = 1    # 优先级，数字越小优先级越高
    enabled: bool = True
    
    def get_daily_budget_dollars(self) -> float:
        """获取日预算(美元)"""
        return self.daily_budget_cents / 100.0
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> int:
        """计算API调用成本(分)"""
        prompt_cost = (prompt_tokens / 1000) * self.cost_per_1k_prompt_tokens
        completion_cost = (completion_tokens / 1000) * self.cost_per_1k_completion_tokens
        return int((prompt_cost + completion_cost) * 100)
    
    def is_available(self) -> bool:
        """检查提供商是否可用"""
        return self.enabled and bool(self.api_key)


@dataclass 
class ProcessingConfig:
    """处理配置"""
    
    # 批处理配置
    batch_size: int = 50
    max_concurrent: int = 10
    processing_timeout_seconds: int = 300
    
    # 重试配置
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0
    
    # 消息过滤
    min_content_length: int = 20
    max_content_length: int = 10000
    skip_system_messages: bool = True
    skip_duplicate_content: bool = True
    
    # 性能配置
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    enable_compression: bool = False


@dataclass
class QualityConfig:
    """质量控制配置"""
    
    # 置信度阈值
    min_jd_detection_confidence: float = 0.6
    min_extraction_confidence: float = 0.7
    min_overall_confidence: float = 0.7
    
    # 质量等级配置
    quality_level: QualityLevel = QualityLevel.MEDIUM
    
    # 验证配置
    enable_field_validation: bool = True
    enable_duplicate_detection: bool = True
    enable_business_logic_validation: bool = True
    
    # 人工验证
    enable_human_feedback: bool = False
    human_verification_threshold: float = 0.9
    auto_approve_threshold: float = 0.95
    
    def get_thresholds_by_level(self) -> Dict[str, float]:
        """根据质量等级获取阈值配置"""
        thresholds = {
            QualityLevel.LOW: {
                "jd_detection": 0.5,
                "extraction": 0.6,
                "overall": 0.6
            },
            QualityLevel.MEDIUM: {
                "jd_detection": 0.6,
                "extraction": 0.7,
                "overall": 0.7
            },
            QualityLevel.HIGH: {
                "jd_detection": 0.7,
                "extraction": 0.8,
                "overall": 0.8
            },
            QualityLevel.STRICT: {
                "jd_detection": 0.8,
                "extraction": 0.9,
                "overall": 0.85
            }
        }
        return thresholds.get(self.quality_level, thresholds[QualityLevel.MEDIUM])


@dataclass
class MonitoringConfig:
    """监控配置"""
    
    # 基础监控
    enable_performance_monitoring: bool = True
    enable_cost_tracking: bool = True
    enable_accuracy_monitoring: bool = True
    
    # 告警配置
    enable_alerts: bool = False
    alert_email: Optional[str] = None
    alert_webhook: Optional[str] = None
    
    # 告警阈值
    low_success_rate_threshold: float = 0.8
    high_cost_threshold_cents: int = 500  # 单批次成本告警阈值
    high_latency_threshold_ms: int = 10000
    
    # 日志配置
    log_level: str = "INFO"
    log_to_file: bool = True
    log_retention_days: int = 30
    
    # 指标收集
    metrics_collection_interval_seconds: int = 300
    enable_detailed_metrics: bool = False


@dataclass
class AIConfig:
    """AI模块主配置"""
    
    # 提供商配置
    providers: List[ProviderConfig] = field(default_factory=list)
    default_provider: str = "openai"
    fallback_providers: List[str] = field(default_factory=lambda: ["claude"])
    
    # 子配置模块
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    quality: QualityConfig = field(default_factory=QualityConfig) 
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # 数据库配置
    database_path: Optional[str] = None
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    
    # 环境配置
    environment: str = "development"  # development, testing, production
    debug_mode: bool = False
    
    def get_provider_by_name(self, name: str) -> Optional[ProviderConfig]:
        """根据名称获取提供商配置"""
        for provider in self.providers:
            if provider.name == name:
                return provider
        return None
    
    def get_available_providers(self) -> List[ProviderConfig]:
        """获取可用的提供商列表"""
        return [p for p in self.providers if p.is_available()]
    
    def get_default_provider(self) -> Optional[ProviderConfig]:
        """获取默认提供商配置"""
        return self.get_provider_by_name(self.default_provider)
    
    def get_fallback_providers(self) -> List[ProviderConfig]:
        """获取备用提供商配置列表"""
        return [p for name in self.fallback_providers 
                for p in self.providers if p.name == name and p.is_available()]
    
    def validate(self) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        # 检查提供商配置
        if not self.providers:
            errors.append("至少需要配置一个提供商")
        
        if not self.get_default_provider():
            errors.append(f"默认提供商 '{self.default_provider}' 不存在或不可用")
        
        # 检查质量配置
        if not (0.0 <= self.quality.min_overall_confidence <= 1.0):
            errors.append("总体置信度阈值必须在0.0-1.0之间")
        
        # 检查处理配置
        if self.processing.batch_size <= 0:
            errors.append("批处理大小必须大于0")
        
        if self.processing.max_concurrent <= 0:
            errors.append("最大并发数必须大于0")
        
        return errors
    
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.environment == "production"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIConfig':
        """从字典创建配置"""
        # 处理providers
        providers_data = data.get('providers', [])
        providers = [ProviderConfig(**p) for p in providers_data]
        
        # 处理子配置
        processing_data = data.get('processing', {})
        processing = ProcessingConfig(**processing_data)
        
        quality_data = data.get('quality', {})
        quality = QualityConfig(**quality_data)
        
        monitoring_data = data.get('monitoring', {})
        monitoring = MonitoringConfig(**monitoring_data)
        
        # 移除已处理的字段
        config_data = {k: v for k, v in data.items() 
                      if k not in ['providers', 'processing', 'quality', 'monitoring']}
        
        return cls(
            providers=providers,
            processing=processing,
            quality=quality,
            monitoring=monitoring,
            **config_data
        )
    
    @classmethod
    def load_from_file(cls, config_path: Union[str, Path]) -> 'AIConfig':
        """从文件加载配置"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件JSON格式错误: {e}")
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {e}")
    
    def save_to_file(self, config_path: Union[str, Path]):
        """保存配置到文件"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"保存配置文件失败: {e}")


def create_default_config() -> AIConfig:
    """创建默认配置"""
    
    # 默认OpenAI提供商配置
    openai_provider = ProviderConfig(
        name="openai",
        provider_type=ProviderType.OPENAI,
        model="gpt-4",
        api_key=os.getenv("OPENAI_API_KEY", ""),
        max_tokens=4000,
        temperature=0.1,
        rate_limit_rpm=60,
        daily_budget_cents=1000,
        weight=1.0,
        priority=1
    )
    
    # 默认Claude提供商配置
    claude_provider = ProviderConfig(
        name="claude",
        provider_type=ProviderType.CLAUDE,
        model="claude-3-sonnet-20240229",
        api_key=os.getenv("CLAUDE_API_KEY", ""),
        max_tokens=4000,
        temperature=0.1,
        rate_limit_rpm=30,
        daily_budget_cents=800,
        weight=0.8,
        priority=2,
        enabled=False  # 默认禁用，需要手动配置
    )
    
    return AIConfig(
        providers=[openai_provider, claude_provider],
        default_provider="openai",
        fallback_providers=["claude"],
        environment="development",
        debug_mode=True
    )


def load_config_from_env() -> AIConfig:
    """从环境变量加载配置"""
    # 获取配置文件路径
    config_file = os.getenv("AI_CONFIG_FILE", "config/ai_config.json")
    
    # 如果配置文件存在，从文件加载
    if os.path.exists(config_file):
        try:
            return AIConfig.load_from_file(config_file)
        except Exception as e:
            print(f"警告：加载配置文件失败，使用默认配置: {e}")
    
    # 否则创建默认配置
    config = create_default_config()
    
    # 从环境变量覆盖关键配置
    if os.getenv("AI_ENVIRONMENT"):
        config.environment = os.getenv("AI_ENVIRONMENT")
    
    if os.getenv("AI_DEBUG_MODE"):
        config.debug_mode = os.getenv("AI_DEBUG_MODE").lower() == "true"
    
    return config


# 测试代码
if __name__ == "__main__":
    # 创建默认配置
    config = create_default_config()
    
    # 验证配置
    errors = config.validate()
    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("配置验证通过")
    
    # 保存配置到文件
    config.save_to_file("config/ai_config.json")
    print("默认配置已保存到 config/ai_config.json")
    
    # 测试从文件加载
    loaded_config = AIConfig.load_from_file("config/ai_config.json")
    print(f"加载的配置包含 {len(loaded_config.providers)} 个提供商")
    
    print("AI配置模块测试完成") 