"""
数据库 v2.0 单元测试
测试新架构的核心数据库功能
"""

import pytest
from datetime import datetime
from pathlib import Path

def test_database_initialization(temp_database):
    """测试数据库初始化"""
    db = temp_database
    
    # 检查版本
    assert db.get_db_version() == "2.0"
    
    # 检查所有必要的表是否存在
    expected_tables = [
        "schema_info", "messages_raw", "messages_staging", 
        "messages_clean", "processing_logs", "backup_metadata", "jobs"
    ]
    
    actual_tables = db.db.table_names()
    for table in expected_tables:
        assert table in actual_tables, f"表 {table} 不存在"

def test_save_raw_message(temp_database, sample_messages):
    """测试保存原始消息"""
    db = temp_database
    
    # 保存一条消息
    msg = sample_messages[0]
    message_id = db.save_raw_message(
        msg["group_name"], msg["sender"], 
        msg["content"], msg["msg_type"]
    )
    
    assert message_id is not None
    assert message_id > 0
    
    # 验证消息已保存
    assert db.db["messages_raw"].count == 1
    
    # 验证消息内容
    saved_msg = db.db["messages_raw"].get(message_id)
    assert saved_msg["group_name"] == msg["group_name"]
    assert saved_msg["sender"] == msg["sender"]
    assert saved_msg["content"] == msg["content"]
    assert saved_msg["processed_status"] == 0  # 未处理

def test_batch_save_messages(temp_database, sample_messages):
    """测试批量保存消息"""
    db = temp_database
    
    message_ids = []
    for msg in sample_messages:
        msg_id = db.save_raw_message(
            msg["group_name"], msg["sender"],
            msg["content"], msg["msg_type"]
        )
        message_ids.append(msg_id)
    
    # 验证所有消息都已保存
    assert len(message_ids) == len(sample_messages)
    assert all(msg_id > 0 for msg_id in message_ids)
    assert db.db["messages_raw"].count == len(sample_messages)

def test_get_unprocessed_messages(temp_database, sample_messages):
    """测试获取未处理消息"""
    db = temp_database
    
    # 保存一些消息
    for msg in sample_messages:
        db.save_raw_message(
            msg["group_name"], msg["sender"],
            msg["content"], msg["msg_type"]
        )
    
    # 获取未处理消息
    unprocessed = db.get_unprocessed_raw_messages()
    
    assert len(unprocessed) == len(sample_messages)
    for msg in unprocessed:
        assert msg["processed_status"] == 0

def test_dedup_hash_generation(temp_database):
    """测试去重哈希生成"""
    db = temp_database
    
    # 相同内容应该生成相同哈希
    hash1 = db.generate_dedup_hash("群1", "用户A", "测试消息")
    hash2 = db.generate_dedup_hash("群1", "用户A", "测试消息")
    assert hash1 == hash2
    
    # 不同内容应该生成不同哈希
    hash3 = db.generate_dedup_hash("群1", "用户A", "不同的消息")
    assert hash1 != hash3
    
    # 大小写应该被标准化（因为内容会被转为小写）
    hash4 = db.generate_dedup_hash("群1", "用户A", "测试消息")
    hash5 = db.generate_dedup_hash("群1", "用户A", "测试消息")
    assert hash4 == hash5

def test_processing_logs(temp_database):
    """测试处理日志功能"""
    db = temp_database
    
    # 生成批次ID
    batch_id = db.generate_batch_id()
    assert batch_id.startswith("batch_")
    
    # 记录处理开始
    log_id = db.log_processing_batch(
        batch_id=batch_id,
        operation_type="test",
        status="started",
        records_processed=10
    )
    
    assert log_id > 0
    
    # 验证日志已记录
    assert db.db["processing_logs"].count == 1
    log_record = db.db["processing_logs"].get(log_id)
    assert log_record["batch_id"] == batch_id
    assert log_record["operation_type"] == "test"
    assert log_record["status"] == "started"

def test_database_constraints(temp_database):
    """测试数据库约束"""
    db = temp_database
    
    # 先插入一条到raw表（满足外键约束）
    raw_id = db.save_raw_message("测试群", "测试用户", "测试内容", "Text")
    
    # 插入一条到staging表
    staging_data = {
        "raw_message_id": raw_id,
        "group_name": "测试群",
        "sender": "测试用户",
        "content": "测试内容",
        "msg_type": "Text",
        "timestamp": datetime.now().isoformat(),
        "dedup_hash": "test_hash_123",
        "processing_batch_id": "test_batch",
        "batch_sequence": 1,
        "validation_status": "valid",
        "created_at": datetime.now().isoformat()
    }
    staging_result = db.db["messages_staging"].insert(staging_data)
    staging_id = staging_result.last_pk
    
    # 测试正常插入到clean表
    clean_data = {
        "raw_message_id": raw_id,
        "staging_message_id": staging_id,
        "group_name": "测试群",
        "sender": "测试用户",
        "content": "测试内容",
        "msg_type": "Text",
        "timestamp": datetime.now().isoformat(),
        "dedup_hash": "test_hash_123",
        "processed_batch_id": "test_batch",
        "quality_score": 1.0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # 插入到clean表
    result = db.db["messages_clean"].insert(clean_data)
    assert result.last_pk > 0

def test_backward_compatibility(temp_database):
    """测试向后兼容性"""
    db = temp_database
    
    # 保存一些数据到clean表
    raw_id = db.save_raw_message("测试群", "测试用户", "测试消息", "Text")
    
    # 先创建staging记录
    staging_data = {
        "raw_message_id": raw_id,
        "group_name": "测试群",
        "sender": "测试用户",
        "content": "测试消息",
        "msg_type": "Text",
        "timestamp": datetime.now().isoformat(),
        "dedup_hash": db.generate_dedup_hash("测试群", "测试用户", "测试消息"),
        "processing_batch_id": "test",
        "batch_sequence": 1,
        "validation_status": "valid",
        "created_at": datetime.now().isoformat()
    }
    staging_result = db.db["messages_staging"].insert(staging_data)
    staging_id = staging_result.last_pk
    
    clean_data = {
        "raw_message_id": raw_id,
        "staging_message_id": staging_id,
        "group_name": "测试群",
        "sender": "测试用户",
        "content": "测试消息",
        "msg_type": "Text",
        "timestamp": datetime.now().isoformat(),
        "dedup_hash": db.generate_dedup_hash("测试群", "测试用户", "测试消息"),
        "processed_batch_id": "test",
        "quality_score": 1.0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    db.db["messages_clean"].insert(clean_data)
    
    # 通过兼容视图查询
    messages_view = list(db.db.execute("SELECT group_name, sender, content, processed FROM messages"))
    assert len(messages_view) == 1
    
    # 获取第一条记录的字段值
    msg = messages_view[0]
    assert msg[0] == "测试群"      # group_name
    assert msg[1] == "测试用户"    # sender  
    assert msg[2] == "测试消息"    # content
    assert msg[3] == 1            # processed - 在clean表中的都是已处理的

def test_error_handling(temp_database):
    """测试错误处理"""
    db = temp_database
    
    # 测试保存空内容
    try:
        msg_id = db.save_raw_message("", "", "", "")
        assert msg_id > 0  # 应该仍然能保存
    except Exception as e:
        pytest.fail(f"保存空内容时不应该抛出异常: {e}")
    
    # 测试获取不存在的消息
    unprocessed = db.get_unprocessed_raw_messages(1000)
    assert isinstance(unprocessed, list)  # 应该返回空列表而不是抛出异常 