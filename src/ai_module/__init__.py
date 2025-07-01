"""
AI模块 - 人工智能功能模块
基于Core模块的数据库内容，提供AI增强功能
"""

__version__ = "1.0.0"
__author__ = "AI Team"

# 尝试导入可能存在的旧模块
try:
    from .jd_extractor import JDExtractor
except ImportError:
    pass

try:
    from .message_analyzer import MessageAnalyzer
except ImportError:
    pass

__all__ = [
    # 版本信息
    "__version__",
    "__author__"
]

# 添加可能存在的旧模块到__all__
try:
    from .jd_extractor import JDExtractor
    __all__.append("JDExtractor")
except ImportError:
    pass

try:
    from .message_analyzer import MessageAnalyzer
    __all__.append("MessageAnalyzer")
except ImportError:
    pass

# AI模块依赖core模块的数据库
try:
    from ..core_module import CoreListener
    print("AI模块成功加载Core模块依赖")
except ImportError:
    print("警告：未找到Core模块，AI模块功能可能受限") 