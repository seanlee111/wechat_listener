"""
LLM接口模块
支持火山引擎和qwen模型的统一调用接口
"""

import json
import logging
import time
from typing import Dict, Optional, List
from abc import ABC, abstractmethod
import requests

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMInterface(ABC):
    """LLM统一接口基类"""
    
    @abstractmethod
    def extract_jd_info(self, message: str) -> Dict:
        """提取JD信息的抽象方法"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """测试连接的抽象方法"""
        pass

class MockLLMInterface(LLMInterface):
    """
    模拟LLM接口 - 用于开发和测试
    模拟真实LLM的行为，返回解析后的JD信息
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.call_count = 0
        logger.info("模拟LLM接口初始化完成")
    
    def extract_jd_info(self, message: str) -> Dict:
        """
        模拟LLM提取JD信息
        
        Args:
            message: 消息内容
            
        Returns:
            提取的JD信息字典
        """
        self.call_count += 1
        
        # 模拟API调用延迟
        time.sleep(0.1)
        
        # 简单的规则提取逻辑 (模拟LLM行为)
        result = {
            "company_name": self._extract_company(message),
            "position_title": self._extract_position(message),
            "work_location": self._extract_location(message),
            "contact_email": self._extract_email(message),
            "email_subject_format": self._extract_email_format(message),
            "resume_naming_format": self._extract_resume_format(message),
            "education_requirement": self._extract_education(message),
            "major_requirement": self._extract_major(message),
            "internship_duration": self._extract_duration(message),
            "skills_required": self._extract_skills(message),
            "work_description": self._extract_work_desc(message),
            "special_requirements": self._extract_special_req(message),
            "llm_confidence": self._calculate_confidence(message),
            "extraction_timestamp": time.time(),
            "model_used": "mock_llm_v1.0"
        }
        
        logger.debug(f"模拟LLM提取完成，置信度: {result['llm_confidence']:.2f}")
        return result
    
    def test_connection(self) -> bool:
        """测试连接"""
        logger.info("模拟LLM连接测试成功")
        return True
    
    def _extract_company(self, text: str) -> Optional[str]:
        """提取公司名称"""
        import re
        patterns = [
            r'【.*?】(.*?)(?:招聘|实习)',
            r'(.*?)(?:证券|银行|科技|公司|集团|有限|股份)',
            r'(.*?)(?:总部|研究所|分公司)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                company = match.group(1).strip()
                if len(company) > 1 and len(company) < 20:
                    return company
        
        return None
    
    def _extract_position(self, text: str) -> Optional[str]:
        """提取职位名称"""
        import re
        patterns = [
            r'招聘.*?】(.*?)(?:\s|$|工作)',
            r'(?:职位|岗位|招聘)[:：\s]*(.*?)(?:\s|$)',
            r'(.*?)(?:实习生|助理|专员|经理)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                position = match.group(1).strip()
                if len(position) > 1 and len(position) < 30:
                    return position
        
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """提取工作地点"""
        import re
        patterns = [
            r'工作地点[:：\s]*(.*?)(?:\s|$|/)',
            r'地点[:：\s]*(.*?)(?:\s|$)',
            r'(北京|上海|广州|深圳|杭州|南京|成都|武汉|重庆|天津|苏州|西安|青岛|宁波|厦门|济南|大连|沈阳|长春|哈尔滨|石家庄|郑州|太原|呼和浩特|兰州|西宁|银川|乌鲁木齐|拉萨|昆明|贵阳|南宁|海口|香港|澳门|台北)(?:市|自治区|特别行政区)?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                if len(location) > 0:
                    return location
        
        return "未指定"
    
    def _extract_email(self, text: str) -> Optional[str]:
        """提取联系邮箱"""
        import re
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    def _extract_email_format(self, text: str) -> Optional[str]:
        """提取邮件主题格式"""
        import re
        patterns = [
            r'邮件主题[:：\s]*(.*?)(?:\s|$)',
            r'主题.*?[:：\s]*(.*?)(?:\s|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                format_str = match.group(1).strip()
                if len(format_str) > 5:
                    return format_str
        
        return None
    
    def _extract_resume_format(self, text: str) -> Optional[str]:
        """提取简历命名格式"""
        import re
        patterns = [
            r'简历命名[:：\s]*(.*?)(?:\s|$)',
            r'简历.*?命名.*?[:：\s]*(.*?)(?:\s|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                format_str = match.group(1).strip()
                if len(format_str) > 5:
                    return format_str
        
        return None
    
    def _extract_education(self, text: str) -> Optional[str]:
        """提取学历要求"""
        if '硕士' in text:
            return '硕士'
        elif '本科' in text:
            return '本科'
        elif '博士' in text:
            return '博士'
        elif '专科' in text:
            return '专科'
        return None
    
    def _extract_major(self, text: str) -> Optional[str]:
        """提取专业要求"""
        majors = ['金融', '计算机', '数学', '经济', '管理', '工程', '机械', '电气', '化学', '物理', '生物']
        found_majors = [major for major in majors if major in text]
        return '、'.join(found_majors) if found_majors else None
    
    def _extract_duration(self, text: str) -> Optional[str]:
        """提取实习时长要求"""
        import re
        patterns = [
            r'(\d+个月|\d+月)',
            r'(\d+个月以上|\d+月以上)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_skills(self, text: str) -> Optional[str]:
        """提取技能要求"""
        skills = ['Python', 'Java', 'C++', 'Excel', 'Office', 'Wind', 'Bloomberg', 'SQL', '编程']
        found_skills = [skill for skill in skills if skill in text]
        return '、'.join(found_skills) if found_skills else None
    
    def _extract_work_desc(self, text: str) -> Optional[str]:
        """提取工作描述"""
        import re
        # 查找工作内容/工作描述部分
        patterns = [
            r'工作(?:内容|描述)[:：\s]*(.*?)(?:任职要求|职位要求|要求|投递)',
            r'实习内容[:：\s]*(.*?)(?:任职要求|职位要求|要求|投递)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                desc = match.group(1).strip()[:200]  # 限制长度
                return desc
        
        return None
    
    def _extract_special_req(self, text: str) -> Optional[str]:
        """提取特殊要求"""
        special_keywords = ['长期实习', '全职', '保证时间', '优先']
        found_special = [kw for kw in special_keywords if kw in text]
        return '、'.join(found_special) if found_special else None
    
    def _calculate_confidence(self, text: str) -> float:
        """计算提取置信度"""
        confidence_factors = 0
        
        # 包含邮箱 +0.3
        if '@' in text:
            confidence_factors += 0.3
        
        # 包含明确的职位信息 +0.2
        if any(kw in text for kw in ['招聘', '实习', '职位']):
            confidence_factors += 0.2
        
        # 包含联系方式 +0.2
        if any(kw in text for kw in ['邮箱', '投递', '简历']):
            confidence_factors += 0.2
        
        # 包含要求信息 +0.2
        if any(kw in text for kw in ['要求', '学历', '专业', '经验']):
            confidence_factors += 0.2
        
        # 文本长度合理 +0.1
        if 100 < len(text) < 2000:
            confidence_factors += 0.1
        
        return min(confidence_factors, 1.0)

class VolcanoLLMInterface(LLMInterface):
    """火山引擎LLM接口"""
    
    def __init__(self, config: Dict):
        """
        初始化火山引擎LLM接口
        
        Args:
            config: 配置字典，应包含 api_key 和 endpoint
        """
        self.config = config
        self.api_key = config.get('api_key')
        self.endpoint_id = config.get('endpoint')
        
        if not self.api_key or not self.endpoint_id:
            raise ValueError("火山引擎LLM接口需要有效的 'api_key' 和 'endpoint'")
            
        self.api_url = f"https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        logger.info(f"火山引擎LLM接口初始化完成，Endpoint: {self.endpoint_id}")
    
    def _construct_prompt(self, message: str) -> str:
        """构建详细的提取提示词"""
        return f"""
        请从以下招聘信息文本中提取关键信息，并严格按照指定的JSON格式返回。
        如果某个字段在文本中没有明确提到，请将其值设为 null。

        **招聘文本:**
        ---
        {message}
        ---

        **JSON格式要求:**
        {{
            "company_name": "公司名称",
            "position_title": "职位名称",
            "work_location": "工作地点",
            "contact_email": "联系邮箱",
            "email_subject_format": "邮件主题格式",
            "resume_naming_format": "简历命名格式",
            "education_requirement": "学历要求",
            "major_requirement": "专业要求",
            "internship_duration": "实习时长要求",
            "skills_required": "技能要求",
            "work_description": "工作内容描述",
            "special_requirements": "其他特殊要求"
        }}
        """

    def extract_jd_info(self, message: str) -> Optional[Dict]:
        """
        使用火山引擎API提取JD信息
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        system_prompt = self._construct_prompt(message)
        
        payload = {
            "model": self.endpoint_id,
            "messages": [
                {"role": "user", "content": system_prompt}
            ],
            "temperature": 0.1,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            logger.info(f"向火山引擎发送提取请求: Model={self.endpoint_id}")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            response_data = response.json()
            
            # 提取返回内容中的JSON字符串
            llm_output_str = response_data.get('choices', [{}])[0].get('message', {}).get('content', '{}')
            
            # 解析JSON字符串
            extracted_data = json.loads(llm_output_str)
            
            # 添加AI元数据
            extracted_data['llm_confidence'] = response_data.get('usage', {}).get('prompt_tokens', 0) / 1000.0 # 简单示例
            extracted_data['model_used'] = self.endpoint_id
            extracted_data['extraction_timestamp'] = time.time()
            
            logger.info(f"火山引擎提取成功: Model={self.endpoint_id}")
            return extracted_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"火山引擎API请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"解析火山引擎返回的JSON失败: {e}")
            return None
        except Exception as e:
            logger.error(f"处理火山引擎响应时发生未知错误: {e}")
            return None
    
    def test_connection(self) -> bool:
        """测试与火山引擎API的连接"""
        try:
            test_message = "你好"
            result = self.extract_jd_info(test_message)
            is_connected = result is not None
            
            if is_connected:
                logger.info("✅ 火山引擎连接测试成功")
            else:
                logger.error("❌ 火山引擎连接测试失败")
                
            return is_connected
            
        except Exception as e:
            logger.error(f"火山引擎连接测试时出错: {e}")
            return False

class QwenLLMInterface(LLMInterface):
    """Qwen LLM接口 (预留)"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config.get('api_key')
        self.model_name = config.get('model_name', 'qwen-max')
        logger.info("Qwen LLM接口初始化完成")
        # TODO: 实现真实的Qwen API调用
    
    def extract_jd_info(self, message: str) -> Dict:
        # TODO: 实现Qwen API调用
        logger.warning("Qwen LLM接口尚未实现，使用模拟接口")
        mock_interface = MockLLMInterface()
        result = mock_interface.extract_jd_info(message)
        result['model_used'] = 'qwen_placeholder'
        return result
    
    def test_connection(self) -> bool:
        # TODO: 实现连接测试
        logger.warning("Qwen连接测试尚未实现")
        return False

class LLMFactory:
    """LLM工厂类"""
    
    @staticmethod
    def create_llm(provider: str, config: Dict) -> LLMInterface:
        """
        创建LLM接口实例
        
        Args:
            provider: 提供商 ('mock', 'volcano', 'qwen')
            config: 配置字典
            
        Returns:
            LLM接口实例
        """
        if provider == 'mock':
            return MockLLMInterface(config)
        elif provider == 'volcano':
            return VolcanoLLMInterface(config)
        elif provider == 'qwen':
            return QwenLLMInterface(config)
        else:
            logger.warning(f"未知的LLM提供商: {provider}，使用模拟接口")
            return MockLLMInterface(config)

# 测试工具
def test_llm_interface():
    """测试LLM接口"""
    print("=== 测试LLM接口 ===")
    
    # 测试用的JD消息
    test_message = """
    【实习生招聘】银河证券研究所机械行业日常实习生
    工作地点：上海市浦东新区/线上

    【实习内容】
    1、协助进行机器人/工程机械等行业及公司研究，撰写深度报告，估值建模
    2、协助展开课题研究，学习行研投资分析逻辑
    3、数据库更新，数据资料整理，及团队其他研究支持工作

    【任职要求】
    1、对证券研究有浓厚兴趣的重点高校本科/硕士在校学生，自驱力强，勤奋踏实，长期实习优先
    2、机械、电气、金融等相关专业优先考虑
    3、能够熟练运用Office/Wind/Bloomberg等 
    4、3个月及以上的连续实习(时间不能保证者勿投)，长期实习优先

    简历请发送至：yhzq_yj_jx@163.com
    邮件主题及简历命名规则：姓名+硕士学校和专业+本科学校和专业+最早入职时间+实习时长+手机号
    """
    
    try:
        # 测试模拟LLM接口
        print("\n1. 测试模拟LLM接口:")
        mock_llm = LLMFactory.create_llm('mock', {})
        
        # 测试连接
        if mock_llm.test_connection():
            print("   ✅ 连接测试成功")
        
        # 测试提取
        result = mock_llm.extract_jd_info(test_message)
        print(f"   ✅ 提取完成，置信度: {result.get('llm_confidence', 0):.2f}")
        
        # 显示提取结果
        key_fields = ['company_name', 'position_title', 'work_location', 'contact_email']
        for field in key_fields:
            value = result.get(field, 'N/A')
            print(f"   - {field}: {value}")
        
        # 测试工厂模式
        print("\n2. 测试LLM工厂:")
        providers = ['mock', 'volcano', 'qwen']
        for provider in providers:
            llm = LLMFactory.create_llm(provider, {})
            print(f"   ✅ {provider} 接口创建成功: {type(llm).__name__}")
        
        print("\n✅ LLM接口测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ LLM接口测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_llm_interface() 