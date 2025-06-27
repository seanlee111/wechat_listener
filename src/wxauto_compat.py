"""
wxauto兼容性包装器
处理版本差异和兼容性问题
"""

import warnings
import logging
from typing import Optional

# 抑制wxauto版本警告
warnings.filterwarnings("ignore", category=UserWarning, module="wxauto")

logger = logging.getLogger(__name__)

class WeChatCompat:
    """微信自动化兼容性包装器"""
    
    def __init__(self):
        """初始化兼容性包装器"""
        self.wx = None
        self._initialize_wxauto()
    
    def _initialize_wxauto(self):
        """初始化wxauto，处理版本兼容性"""
        try:
            # 抑制所有wxauto相关警告
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from wxauto import WeChat
                self.wx = WeChat()
                
            logger.info("wxauto初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"wxauto导入失败: {e}")
            return False
        except Exception as e:
            logger.warning(f"wxauto初始化时出现警告: {e}")
            # 即使有警告，仍然尝试继续
            try:
                from wxauto import WeChat
                self.wx = WeChat()
                logger.info("尽管有警告，wxauto仍然初始化成功")
                return True
            except Exception as e2:
                logger.error(f"wxauto初始化完全失败: {e2}")
                return False
    
    def ChatWith(self, group_name: str):
        """切换到指定群聊，增加错误处理"""
        if not self.wx:
            logger.error("微信实例未初始化")
            return None
        
        try:
            result = self.wx.ChatWith(group_name)
            return result
        except Exception as e:
            logger.error(f"切换群聊失败 {group_name}: {e}")
            return None
    
    def GetAllMessage(self):
        """获取所有消息，增加错误处理"""
        if not self.wx:
            logger.error("微信实例未初始化")
            return []
        
        try:
            messages = self.wx.GetAllMessage()
            return messages if messages else []
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return []
    
    def is_available(self) -> bool:
        """检查wxauto是否可用"""
        return self.wx is not None

def create_wechat_instance() -> Optional[WeChatCompat]:
    """创建兼容的微信实例"""
    try:
        compat = WeChatCompat()
        if compat.is_available():
            return compat
        else:
            logger.error("无法创建可用的微信实例")
            return None
    except Exception as e:
        logger.error(f"创建微信实例失败: {e}")
        return None 