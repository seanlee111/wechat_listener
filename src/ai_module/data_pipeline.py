"""
数据准备阶段 - 阶段1 (修复版本)
从现有数据库读取消息并进行JD预筛选
"""

import logging
import sys
import os
from typing import List, Dict, Optional
from pathlib import Path

# 添加项目根目录到路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.database_v2 import DatabaseV2
from src.ai_module.config import get_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataPipeline:
    """
    数据准备阶段处理器 (修复版本)
    负责从messages_clean获取待处理消息并进行JD预筛选
    """
    
    def __init__(self, db_v2: Optional[DatabaseV2] = None):
        """初始化数据管道"""
        self.db_v2 = db_v2 or DatabaseV2()
        
        # 加载配置
        self.config = get_config()
        self.batch_size = self.config.get("data_pipeline", "batch_size", 20)
        self.jd_detection_threshold = self.config.get("data_pipeline", "jd_detection_threshold", 0.4)
        self.min_content_length = self.config.get("data_pipeline", "min_content_length", 30)
        
        # JD关键词列表 - 按重要性分组
        # 核心关键词（强指示词）
        self.jd_core_keywords = [
            '招聘', '实习生', '招募', '诚聘', '校招', '社招', '岗位职责', '任职要求', 
            '投递简历', '简历投递', '简历命名', '邮件命名', '投递邮箱'
        ]
        
        # 职位类关键词
        self.jd_position_keywords = [
            '岗位', '职位', '实习', '工作地点', '工作职责', '工作内容',
            '全职', '兼职', '日常实习', '暑期实习', '长期实习', '补贴', '薪资'
        ]
        
        # 要求类关键词
        self.jd_requirement_keywords = [
            '要求', '条件', '经验', '学历', '专业', '技能', '能力',
            '本科', '硕士', '博士', '985', '211', '学校', '年级',
            '出勤', '天数', '可实习', '月'
        ]
        
        # 联系类关键词
        self.jd_contact_keywords = [
            '邮箱', 'email', '@', '投递', '发送', '命名规则', '格式命名'
        ]
        
        # 公司类关键词
        self.jd_company_keywords = [
            '公司', '集团', '企业', '证券', '银行', '基金', '总部', '部门'
        ]
        
        # 合并所有关键词用于简单检查
        self.jd_keywords = (self.jd_core_keywords + self.jd_position_keywords + 
                           self.jd_requirement_keywords + self.jd_contact_keywords + 
                           self.jd_company_keywords)
        
        logger.info("数据准备阶段初始化完成")
    
    def get_pending_messages(self, batch_size: Optional[int] = None) -> List[Dict]:
        """
        从messages_clean表获取所有未被AI处理的消息
        
        Args:
            batch_size: (可选) 限制处理数量，为None则处理所有
            
        Returns:
            待处理消息列表
        """
        try:
            # 方案1: 排除已处理的消息
            # 任务1: 添加 WHERE id NOT IN (...) 子查询
            sql_query = """
                SELECT id, content, sender, group_name, created_at,
                       id as source_id, id as raw_message_id
                FROM messages_clean 
                WHERE id NOT IN (
                    SELECT clean_message_id 
                    FROM ai_extracted_jobs 
                    WHERE clean_message_id IS NOT NULL
                )
                ORDER BY id
            """
            params = []
            
            # 任务2: 移除批次大小限制 (除非明确指定)
            if batch_size is not None:
                sql_query += " LIMIT ?"
                params.append(batch_size)
            
            messages = list(self.db_v2.db.execute(sql_query, params))
            
            # 手动转换为字典格式
            column_names = ['id', 'content', 'sender', 'group_name', 'created_at', 'source_id', 'raw_message_id']
            dict_messages = [dict(zip(column_names, row)) for row in messages]
            
            logger.info(f"获取到 {len(dict_messages)} 条未处理消息 (来源表: messages_clean)")
            return dict_messages
            
        except Exception as e:
            logger.error(f"获取待处理消息失败: {e}")
            return []
    
    def filter_jd_candidates(self, messages: List[Dict]) -> List[Dict]:
        """
        JD预筛选：过滤可能包含招聘信息的消息
        使用多维度评分机制识别JD
        
        Args:
            messages: 原始消息列表
            
        Returns:
            疑似JD消息列表
        """
        jd_candidates = []
        
        for msg in messages:
            content = msg.get('content', '')
            if not content:
                continue
                
            content_lower = content.lower()
            
            # 1. 基础过滤 - 排除明显太短的消息
            if len(content) < self.min_content_length:
                continue
                
            # 2. 多维度评分
            score = self._calculate_jd_score(content_lower)
            
            # 3. 设置阈值 - 分数>=阈值才认为是疑似JD
            if score >= self.jd_detection_threshold:
                msg_copy = msg.copy()
                msg_copy['jd_score'] = score
                msg_copy['jd_confidence'] = min(score, 1.0)
                jd_candidates.append(msg_copy)
        
        logger.info(f"预筛选完成: {len(messages)} -> {len(jd_candidates)} 条疑似JD消息")
        return jd_candidates
        
    def _calculate_jd_score(self, content: str) -> float:
        """
        计算文本的JD可能性评分
        使用多维度评分机制
        
        Args:
            content: 消息内容（小写）
            
        Returns:
            JD可能性评分 (0.0-1.0)
        """
        score = 0.0
        
        # 1. 核心关键词检查（高权重）- 每个命中+0.25，最多0.5分
        core_hits = sum(1 for kw in self.jd_core_keywords if kw in content)
        score += min(core_hits * 0.25, 0.5)
        
        # 2. 多类别关键词覆盖（广度）- 每个类别命中至少一个关键词+0.1，最多0.3分
        category_scores = [
            any(kw in content for kw in self.jd_position_keywords),
            any(kw in content for kw in self.jd_requirement_keywords),
            any(kw in content for kw in self.jd_contact_keywords)
        ]
        score += sum(category_scores) * 0.1
        
        # 3. 结构特征检查 - 0.2分
        structure_indicators = [
            '：' in content or ':' in content,  # 含有冒号（表示结构化内容）
            any(str(i) + '、' in content or str(i) + '.' in content for i in range(1, 6)),  # 含有序号
            content.count('\n') >= 3  # 含有多个换行（表示段落结构）
        ]
        if sum(structure_indicators) >= 2:
            score += 0.2
            
        # 4. 长度奖励 - 最多0.1分
        # JD通常较长，给长文本加分
        length_score = min(len(content) / 1000, 0.1)
        score += length_score
        
        # 5. 特殊减分项 - 排除明显非JD
        # 如果包含明显的非JD特征词，降低分数
        non_jd_indicators = [
            'http://' in content or 'https://' in content,  # 含有链接可能是广告
            '点击' in content and '下载' in content,  # 可能是APP推广
            '加群' in content or '拉群' in content  # 可能是群聊邀请
        ]
        score -= sum(non_jd_indicators) * 0.15
        
        return max(0.0, min(score, 1.0))  # 确保分数在0-1之间
    
    def prepare_batch_data(self, batch_size: Optional[int] = None) -> Dict:
        """
        准备一个批次的数据
        
        Args:
            batch_size: 批次大小，如果为None则使用配置中的值
            
        Returns:
            包含原始消息和筛选后消息的字典
        """
        # 获取待处理消息
        batch_size = batch_size or self.batch_size
        pending_messages = self.get_pending_messages(batch_size)
        
        if not pending_messages:
            logger.info("没有待处理的消息")
            return {
                'total_messages': 0,
                'raw_messages': [],
                'jd_candidates': [],
                'filter_ratio': 0.0
            }
        
        # JD预筛选
        jd_candidates = self.filter_jd_candidates(pending_messages)
        
        filter_ratio = len(jd_candidates) / len(pending_messages) if pending_messages else 0
        
        result = {
            'total_messages': len(pending_messages),
            'raw_messages': pending_messages,
            'jd_candidates': jd_candidates,
            'filter_ratio': filter_ratio
        }
        
        logger.info(f"批次数据准备完成: 总数={len(pending_messages)}, JD候选={len(jd_candidates)}, 过滤比例={filter_ratio:.2%}")
        
        return result 
        
    def test_jd_detection(self, text: str) -> Dict:
        """
        测试JD检测功能
        
        Args:
            text: 要测试的文本
            
        Returns:
            包含检测结果的字典
        """
        content_lower = text.lower()
        score = self._calculate_jd_score(content_lower)
        is_jd = score >= 0.4
        
        # 详细分析得分构成
        core_hits = sum(1 for kw in self.jd_core_keywords if kw in content_lower)
        core_score = min(core_hits * 0.25, 0.5)
        
        category_scores = [
            any(kw in content_lower for kw in self.jd_position_keywords),
            any(kw in content_lower for kw in self.jd_requirement_keywords),
            any(kw in content_lower for kw in self.jd_contact_keywords)
        ]
        category_score = sum(category_scores) * 0.1
        
        structure_indicators = [
            '：' in content_lower or ':' in content_lower,
            any(str(i) + '、' in content_lower or str(i) + '.' in content_lower for i in range(1, 6)),
            content_lower.count('\n') >= 3
        ]
        structure_score = 0.2 if sum(structure_indicators) >= 2 else 0
        
        length_score = min(len(content_lower) / 1000, 0.1)
        
        non_jd_indicators = [
            'http://' in content_lower or 'https://' in content_lower,
            '点击' in content_lower and '下载' in content_lower,
            '加群' in content_lower or '拉群' in content_lower
        ]
        penalty_score = sum(non_jd_indicators) * 0.15
        
        # 关键词匹配详情
        matched_keywords = {
            '核心关键词': [kw for kw in self.jd_core_keywords if kw in content_lower],
            '职位关键词': [kw for kw in self.jd_position_keywords if kw in content_lower],
            '要求关键词': [kw for kw in self.jd_requirement_keywords if kw in content_lower],
            '联系关键词': [kw for kw in self.jd_contact_keywords if kw in content_lower],
            '公司关键词': [kw for kw in self.jd_company_keywords if kw in content_lower]
        }
        
        return {
                    'is_jd': is_jd,
        'score': score,
        'threshold': self.jd_detection_threshold,
            'score_breakdown': {
                'core_keywords': core_score,
                'category_coverage': category_score,
                'structure': structure_score,
                'length': length_score,
                'penalties': -penalty_score
            },
            'matched_keywords': matched_keywords,
            'text_length': len(text)
        }


# 测试函数
def test_jd_detection():
    """测试JD检测功能"""
    pipeline = DataPipeline()
    
    # 测试用例
    test_cases = [
        {
            "name": "华泰证券JD",
            "text": """【华泰联合证券】实习生招聘
实习地点：安徽合肥（项目地）

岗位职责：
1. 参与A股IPO/再融资/并购项目的相关工作，包括但不限于项目建议书制作、项目底稿整理及核查、备忘录撰写、估值模型搭建、财务分析等；
2. 协助完成投资银行业务相关的数据统计、行业研究、案例分析及监管法规整理等相关工作；
3. 协助项目团队成员完成其他工作。

岗位要求：
1. 重点院校在读全日制研究生或准研究生，金融、会计、财务、法律等相关专业；
2. 对投资银行业务有一定了解，具备较高的主动性、快速学习能力及抗压能力，做事踏实严谨，可适应加班及较长的工作时间，可适应经常出差；
3. 具有扎实的财务基础、较强的沟通能力和逻辑分析能力，掌握MS Powerpoint、Excel、Wind等软件操作，对数字及行业动态敏感；
4. 通过CPA、CFA及国家法律职业资格等相关资格考试者优先；
5. 有投资银行相关实习经历者优先。

投递方式：
简历及邮件名称请按照"GF-深圳-当前所在地-姓名-学校-专业年级-每周出勤天数-可开始实习时间及时长"格式命名，投递至：htlhhr_internsz@htsc.com"""
        },
        {
            "name": "腾讯JD",
            "text": """腾讯

【招聘岗位】
战略发展部商业分析实习生-互娱方向

【岗位职责】
1、协助腾讯集团战略部团队进行各类商业分析，分析海外游戏领域(端游，手游，主机)商业模式和探索产品机会；
2、监测海外游戏行业数据、新闻及竞争对手动态，对重点公司/业务情况进行深入分析；
3、收集，整理数据，撰写专题报告。

【任职要求】
1、商业分析有敏感性且兴趣浓厚，有互联网或咨询公司实习经历；
2、快速学习能力，擅长数据查找与分析，信息收集与提炼；
3、英语读写流利，出色的hardskill；
4、每周可工作4天及以上，持续3个月，6个月为佳。
加分项：
1、对游戏行业有较深理解者；
2、时间上可以commit较久者。

【薪资福利】
实习工资200元/天。

【工作地点】
深圳市科兴科学园。

【简历投递】
1、投递邮箱：sd_ieg_intern@tencent.com
2、邮件&简历命名：姓名_学校_专业_年级_每周X天_可实习X月，形式命名。"""
        },
        {
            "name": "麦当劳JD",
            "text": """麦当劳中国总部一市场部（会员营销）实习生招募  Membership Marketing Intern
【岗位职责】
1.创意策划&执行：参与策划和执行麦当劳会员营销活动，包括creative plan、social plan提报和campaign落地执行，撰写创意文案，跟进公私域传播规划，全过程支持项目落地，共同驱动业务增长
2.沟通协调：对外协助完成日常Agency对接沟通brief，对内进行跨部门沟通，进行活动物料日常的维护与更新，保障活动顺利落地
3.数据洞察：协助收集整理生意数据，追踪业务表现，搜集分析行业信息并输出基础洞察
4.Support团队其他事务
 
【知识技能和经验要求】
1.熟练使用MS office，如PPT/Excel，审美佳，掌握基础设计技能加分
2.善于沟通，细心敏捷，能与其他部门及合作方保持协同沟通，主动管理和推进工作事项，detail-driven，具备ownership意识
3.熟悉各品牌与各平台的会员玩法与优惠机制，了解社媒热点
4.每周出勤 4-5天，实习5个月以上
 
【福利待遇】
1.实习补贴150/天，麦当劳七五折员工优惠，每月300麦当劳餐补（根据出勤天数）
2.世界500强，工作弹性不打卡
3.项目参与度高，exposure大

【地址】
上海市徐汇区众腾大厦麦当劳中国总部（11号线龙耀路站2号口）

有意者请投递此邮箱：1204860721@qq.com"""
        },
        {
            "name": "闲聊消息1",
            "text": """安卓用户点击 dpurl.cn/hAjBBkzz 可直接下载；
苹果用户点击 dpurl.cn/XlElWo1z 可直接下载；
下载完成后，进入app可申请公测码"""
        },
        {
            "name": "闲聊消息2",
            "text": "加入星球的朋友请dd我，我拉你进专属星球群，方便添加进免分享白名单"
        },
        {
            "name": "闲聊消息3-带链接",
            "text": """周末快乐，今天分享一个好用的工具
https://www.example.com/tools
大家可以试试看，挺好用的"""
        },
        {
            "name": "闲聊消息4-较长",
            "text": """今天我们讨论一下关于学习方法的问题。
学习是一个持续的过程，需要不断地积累和实践。
首先，要有明确的目标。
其次，要有良好的学习习惯。
最后，要不断地复习和实践。
希望大家能够找到适合自己的学习方法，取得好成绩。"""
        },
        {
            "name": "边缘情况-简短JD",
            "text": """急招实习生！
金融相关专业，本科及以上学历
简历发送至：hr@example.com"""
        }
    ]
    
    print("=== JD检测测试 ===\n")
    
    for case in test_cases:
        print(f"测试: {case['name']}")
        result = pipeline.test_jd_detection(case['text'])
        
        print(f"  是否JD: {'✓' if result['is_jd'] else '✗'}")
        print(f"  总分: {result['score']:.2f} (阈值: {result['threshold']})")
        
        # 打印得分明细
        print("  得分明细:")
        for name, score in result['score_breakdown'].items():
            print(f"    - {name}: {score:.2f}")
        
        # 打印匹配的关键词
        print("  匹配关键词:")
        for category, keywords in result['matched_keywords'].items():
            if keywords:
                print(f"    - {category}: {', '.join(keywords)}")
        
        print()
    
    print("测试完成!")

if __name__ == "__main__":
    test_jd_detection() 