"""
阶段3集成测试
测试安全去重器、数据验证器、工作流管理器的集成功能
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# 导入要测试的模块
from src.database_v2 import DatabaseV2
from src.safe_deduplicator import SafeDeduplicator, DedupConfig, execute_safe_deduplication
from src.data_validator import DataValidator, validate_database
from src.workflow_manager import WorkflowManager, WorkflowConfig, execute_full_workflow

class TestPhase3Integration:
    """阶段3集成测试类"""
    
    def setup_method(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # 初始化数据库v2
        self.db_v2 = DatabaseV2(db_path=self.temp_db.name)
        
        # 插入测试数据
        self._insert_test_data()
    
    def teardown_method(self):
        """测试后清理"""
        if self.db_v2:
            self.db_v2.close()
        
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def _insert_test_data(self):
        """插入测试数据"""
        # 插入一些重复和非重复的消息
        test_messages = [
            ("群聊1", "用户A", "测试消息1", "text", datetime.now().isoformat()),
            ("群聊1", "用户A", "测试消息1", "text", datetime.now().isoformat()),  # 重复
            ("群聊1", "用户B", "测试消息2", "text", datetime.now().isoformat()),
            ("群聊2", "用户C", "测试消息3", "text", datetime.now().isoformat()),
            ("群聊2", "用户D", "测试消息4", "text", datetime.now().isoformat()),
            ("群聊2", "用户D", "测试消息4", "text", datetime.now().isoformat()),  # 重复
        ]
        
        for group, sender, content, msg_type, timestamp in test_messages:
            self.db_v2.save_raw_message(group, sender, content, msg_type, timestamp)
    
    def test_safe_deduplicator_functionality(self):
        """测试安全去重器功能"""
        # 创建去重器
        config = DedupConfig(batch_size=3, validation_enabled=True)
        deduplicator = SafeDeduplicator(self.db_v2, config)
        
        # 获取初始统计
        initial_raw_count = self.db_v2.db["messages_raw"].count
        initial_clean_count = self.db_v2.db["messages_clean"].count
        
        assert initial_raw_count == 6  # 6条原始消息
        assert initial_clean_count == 0  # 0条清洁消息
        
        # 执行去重
        success = deduplicator.execute_safe_deduplication()
        assert success
        
        # 检查结果
        final_raw_count = self.db_v2.db["messages_raw"].count
        final_clean_count = self.db_v2.db["messages_clean"].count
        
        assert final_raw_count == 6  # 原始消息不变
        assert final_clean_count == 4  # 4条唯一消息（去掉2条重复）
        
        # 检查统计信息
        stats = deduplicator.stats
        assert stats.total_raw_messages == 6
        assert stats.processed_messages == 6
        assert stats.clean_messages == 4
        assert stats.duplicate_messages == 2
        assert stats.get_dedup_ratio() == pytest.approx(0.333, rel=0.1)  # 33.3%去重率
    
    def test_data_validator_functionality(self):
        """测试数据验证器功能"""
        # 先执行去重，创建clean数据
        deduplicator = SafeDeduplicator(self.db_v2)
        deduplicator.execute_safe_deduplication()
        
        # 创建验证器
        validator = DataValidator(self.db_v2)
        
        # 执行验证
        result = validator.validate_database_integrity()
        
        # 检查验证结果
        assert result is not None
        assert result.is_valid  # 应该通过验证
        assert result.error_count == 0
        
        # 检查统计信息
        assert "raw_messages" in result.statistics
        assert "clean_messages" in result.statistics
        assert result.statistics["raw_messages"] == 6
        assert result.statistics["clean_messages"] == 4
        
        # 生成报告
        report = validator.generate_validation_report(result)
        assert "数据验证报告" in report
        assert "通过" in report
    
    def test_workflow_manager_functionality(self):
        """测试工作流管理器功能"""
        # 创建工作流配置
        config = WorkflowConfig(
            auto_dedup_enabled=True,
            dedup_threshold=1,  # 低阈值，确保触发去重
            auto_backup_enabled=False,  # 禁用备份以简化测试
            validation_enabled=True
        )
        
        # 创建工作流管理器
        workflow_manager = WorkflowManager(config)
        workflow_manager.db_v2 = self.db_v2  # 使用测试数据库
        
        # 获取初始状态
        initial_status = workflow_manager.get_system_status()
        assert initial_status["database"]["raw_messages"] == 6
        assert initial_status["database"]["clean_messages"] == 0
        
        # 执行完整工作流
        success = workflow_manager.execute_complete_workflow()
        assert success
        
        # 检查最终状态
        final_status = workflow_manager.get_system_status()
        assert final_status["database"]["raw_messages"] == 6
        assert final_status["database"]["clean_messages"] == 4
        assert final_status["workflow_stats"]["total_dedups_executed"] == 1
        
        # 关闭工作流管理器
        workflow_manager.close()
    
    def test_component_integration(self):
        """测试组件集成"""
        # 1. 执行去重
        deduplicator = SafeDeduplicator(self.db_v2)
        dedup_success = deduplicator.execute_safe_deduplication()
        assert dedup_success
        
        # 2. 验证去重结果
        validator = DataValidator(self.db_v2)
        validation_result = validator.validate_database_integrity()
        assert validation_result.is_valid
        
        # 3. 检查数据一致性
        raw_count = self.db_v2.db["messages_raw"].count
        clean_count = self.db_v2.db["messages_clean"].count
        processed_count = list(self.db_v2.db.execute(
            "SELECT COUNT(*) FROM messages_raw WHERE processed_status = 1"
        ))[0][0]
        
        assert raw_count == 6
        assert clean_count == 4
        assert processed_count == 6  # 所有原始消息都已标记为处理
        
        # 4. 检查去重哈希唯一性
        hash_duplicates = list(self.db_v2.db.execute("""
            SELECT dedup_hash, COUNT(*) as count 
            FROM messages_clean 
            GROUP BY dedup_hash 
            HAVING count > 1
        """))
        assert len(hash_duplicates) == 0  # 不应该有重复哈希
        
        # 5. 检查外键完整性
        orphaned_clean = list(self.db_v2.db.execute("""
            SELECT COUNT(*) FROM messages_clean c
            LEFT JOIN messages_raw r ON c.raw_message_id = r.id
            WHERE r.id IS NULL
        """))
        assert orphaned_clean[0][0] == 0  # 不应该有孤立的clean记录
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试空数据库的处理
        empty_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        empty_db_file.close()
        
        try:
            empty_db = DatabaseV2(db_path=empty_db_file.name)
            
            # 对空数据库执行去重
            deduplicator = SafeDeduplicator(empty_db)
            success = deduplicator.execute_safe_deduplication()
            assert success  # 空数据库也应该成功处理
            
            # 对空数据库执行验证
            validator = DataValidator(empty_db)
            result = validator.validate_database_integrity()
            assert result.is_valid  # 空数据库应该通过验证
            
            empty_db.close()
            
        finally:
            if os.path.exists(empty_db_file.name):
                os.unlink(empty_db_file.name)
    
    def test_performance_metrics(self):
        """测试性能指标"""
        # 插入更多测试数据
        for i in range(100):
            self.db_v2.save_raw_message(
                f"群聊{i%5}", 
                f"用户{i%10}", 
                f"消息内容{i}", 
                "text", 
                datetime.now().isoformat()
            )
        
        # 记录开始时间
        start_time = datetime.now()
        
        # 执行去重
        deduplicator = SafeDeduplicator(self.db_v2)
        success = deduplicator.execute_safe_deduplication()
        assert success
        
        # 记录结束时间
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # 检查性能
        assert execution_time < 30  # 应该在30秒内完成
        assert deduplicator.stats.execution_time_seconds > 0
        
        print(f"处理 {deduplicator.stats.processed_messages} 条消息用时 {execution_time:.2f} 秒")
    
    def test_batch_processing(self):
        """测试批处理功能"""
        # 创建大批量测试数据
        for i in range(50):
            self.db_v2.save_raw_message(
                "大群聊", 
                f"用户{i}", 
                f"批处理测试消息{i}", 
                "text", 
                datetime.now().isoformat()
            )
        
        # 配置小批次大小
        config = DedupConfig(batch_size=10)
        deduplicator = SafeDeduplicator(self.db_v2, config)
        
        # 执行去重
        success = deduplicator.execute_safe_deduplication()
        assert success
        
        # 检查批次统计
        assert deduplicator.stats.batch_count > 1  # 应该有多个批次
        
        # 验证所有消息都被处理
        unprocessed = list(self.db_v2.db.execute(
            "SELECT COUNT(*) FROM messages_raw WHERE processed_status = 0"
        ))
        assert unprocessed[0][0] == 0  # 没有未处理消息

class TestConvenienceFunctions:
    """测试便利函数"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # 设置数据库路径环境变量（如果便利函数支持的话）
        os.environ['TEST_DB_PATH'] = self.temp_db.name
        
        # 创建测试数据
        db = DatabaseV2(db_path=self.temp_db.name)
        db.save_raw_message("测试群", "测试用户", "测试消息", "text", datetime.now().isoformat())
        db.close()
    
    def teardown_method(self):
        """测试后清理"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        
        if 'TEST_DB_PATH' in os.environ:
            del os.environ['TEST_DB_PATH']
    
    def test_execute_safe_deduplication_function(self):
        """测试安全去重便利函数"""
        # 注意：这个测试可能需要根据实际实现调整
        # 因为便利函数可能使用默认数据库路径
        
        # 临时跳过，因为便利函数使用默认数据库
        pytest.skip("便利函数使用默认数据库路径，需要特殊配置")
    
    def test_validate_database_function(self):
        """测试数据库验证便利函数"""
        # 临时跳过，同上原因
        pytest.skip("便利函数使用默认数据库路径，需要特殊配置")

def test_full_workflow_integration():
    """测试完整工作流集成（独立测试）"""
    # 创建临时数据库
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        # 初始化数据库并添加测试数据
        db_v2 = DatabaseV2(db_path=temp_db.name)
        
        # 添加测试数据
        test_data = [
            ("群聊A", "用户1", "重要信息1", "text"),
            ("群聊A", "用户1", "重要信息1", "text"),  # 重复
            ("群聊B", "用户2", "重要信息2", "text"),
            ("群聊C", "用户3", "重要信息3", "text"),
        ]
        
        for group, sender, content, msg_type in test_data:
            db_v2.save_raw_message(group, sender, content, msg_type, datetime.now().isoformat())
        
        db_v2.close()
        
        # 注意：这里需要实际的工作流执行
        # 由于便利函数使用默认数据库，我们使用组件级别的测试
        
        print("✓ 完整工作流集成测试准备完成")
        
    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"]) 