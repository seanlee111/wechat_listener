"""
微信监听器测试配置
提供测试夹具和共享配置
"""

import pytest
import tempfile
import shutil
import sqlite3
from pathlib import Path
import sys

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database_v2 import DatabaseV2
from backup_manager import BackupManager

@pytest.fixture(scope="function")
def temp_database():
    """创建临时测试数据库"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_wechat.db"
    
    # 创建测试数据库
    db_v2 = DatabaseV2(db_path)
    db_v2.setup_database_v2()
    
    yield db_v2
    
    # 清理
    db_v2.close()
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="function")
def sample_messages():
    """提供测试消息数据"""
    return [
        {
            "group_name": "测试群1",
            "sender": "用户A",
            "content": "这是一条测试消息",
            "msg_type": "Text"
        },
        {
            "group_name": "测试群1",
            "sender": "用户B",
            "content": "这是另一条测试消息",
            "msg_type": "Text"
        },
        {
            "group_name": "测试群2",
            "sender": "用户A",
            "content": "这是一条测试消息",  # 故意重复内容
            "msg_type": "Text"
        }
    ]

@pytest.fixture(scope="function")
def duplicate_messages():
    """提供包含重复的测试消息"""
    return [
        {
            "group_name": "测试群",
            "sender": "用户A",
            "content": "重复消息测试",
            "msg_type": "Text"
        },
        {
            "group_name": "测试群",
            "sender": "用户A",
            "content": "重复消息测试",  # 完全重复
            "msg_type": "Text"
        },
        {
            "group_name": "测试群",
            "sender": "用户A",
            "content": "重复消息测试",  # 再次重复
            "msg_type": "Text"
        }
    ]

@pytest.fixture(scope="session")
def performance_baseline():
    """性能基准数据"""
    return {
        "dedup_time_per_1000_messages": 2.0,  # 秒
        "memory_usage_mb": 50,
        "database_growth_factor": 1.3
    } 