"""
阶段3功能演示 - 安全去重架构v2.0
展示安全去重器、数据验证器、工作流管理器的完整功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import time
from datetime import datetime
from database_v2 import DatabaseV2
from safe_deduplicator import SafeDeduplicator, DedupConfig
from data_validator import DataValidator
from workflow_manager import WorkflowManager, WorkflowConfig
from backup_manager import BackupManager

def print_section_header(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_step(step_num, description):
    """打印步骤信息"""
    print(f"\n🔹 步骤 {step_num}: {description}")

def demo_database_v2():
    """演示数据库v2.0功能"""
    print_section_header("数据库架构 v2.0 演示")
    
    # 初始化数据库
    db_v2 = DatabaseV2()
    
    print_step(1, "数据库初始化与版本检查")
    print(f"   数据库版本: {db_v2.get_db_version()}")
    print(f"   存在的表: {db_v2.db.table_names()}")
    
    print_step(2, "数据统计")
    try:
        raw_count = db_v2.db["messages_raw"].count
        clean_count = db_v2.db["messages_clean"].count
        logs_count = db_v2.db["processing_logs"].count
        
        print(f"   原始消息: {raw_count} 条")
        print(f"   清洁消息: {clean_count} 条")
        print(f"   处理日志: {logs_count} 条")
        
        # 获取未处理消息
        unprocessed = db_v2.get_unprocessed_raw_messages(limit=5)
        print(f"   未处理消息样例: {len(unprocessed)} 条")
        
    except Exception as e:
        print(f"   数据统计出错: {e}")
    
    db_v2.close()
    print("   ✓ 数据库v2.0功能正常")

def demo_backup_manager():
    """演示备份管理器"""
    print_section_header("备份管理器演示")
    
    backup_manager = BackupManager()
    
    print_step(1, "创建自动备份")
    backup_path = backup_manager.create_automatic_backup("demo_test")
    if backup_path:
        print(f"   ✓ 备份创建成功: {backup_path}")
    else:
        print("   ❌ 备份创建失败")
    
    print_step(2, "备份统计")
    stats = backup_manager.get_backup_statistics()
    print(f"   备份总数: {stats.get('total_backups', 0)}")
    print(f"   总大小: {stats.get('total_size_mb', 0):.2f} MB")

def demo_safe_deduplicator():
    """演示安全去重器"""
    print_section_header("安全去重器演示")
    
    # 配置去重器
    config = DedupConfig(
        batch_size=100,
        create_backup_before_dedup=False,  # 演示时跳过备份
        validation_enabled=True
    )
    
    deduplicator = SafeDeduplicator(config=config)
    
    print_step(1, "获取去重前状态")
    db = deduplicator.db_v2
    
    try:
        initial_raw = db.db["messages_raw"].count
        initial_clean = db.db["messages_clean"].count
        
        print(f"   原始消息: {initial_raw} 条")
        print(f"   清洁消息: {initial_clean} 条")
        
        print_step(2, "执行安全去重")
        start_time = time.time()
        success = deduplicator.execute_safe_deduplication()
        execution_time = time.time() - start_time
        
        if success:
            print("   ✓ 去重执行成功")
            
            # 显示统计
            stats = deduplicator.stats
            print(f"   处理消息: {stats.processed_messages} 条")
            print(f"   清洁消息: {stats.clean_messages} 条")
            print(f"   重复消息: {stats.duplicate_messages} 条")
            print(f"   去重比例: {stats.get_dedup_ratio():.2%}")
            print(f"   执行时间: {execution_time:.2f} 秒")
            
        else:
            print("   ❌ 去重执行失败")
            
    except Exception as e:
        print(f"   去重演示出错: {e}")
    
    deduplicator.db_v2.close()

def demo_data_validator():
    """演示数据验证器"""
    print_section_header("数据验证器演示")
    
    validator = DataValidator()
    
    print_step(1, "执行数据库完整性验证")
    result = validator.validate_database_integrity()
    
    print(f"   验证结果: {'通过' if result.is_valid else '失败'}")
    print(f"   错误数量: {result.error_count}")
    print(f"   警告数量: {result.warning_count}")
    
    if result.errors:
        print("   主要错误:")
        for error in result.errors[:3]:
            print(f"     - {error}")
    
    if result.warnings:
        print("   主要警告:")
        for warning in result.warnings[:3]:
            print(f"     - {warning}")
    
    print_step(2, "数据库统计信息")
    stats = result.statistics
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    validator.db_v2.close()

def demo_workflow_manager():
    """演示工作流管理器"""
    print_section_header("工作流管理器演示")
    
    # 配置工作流
    config = WorkflowConfig(
        auto_dedup_enabled=True,
        dedup_threshold=1,  # 低阈值确保演示
        auto_backup_enabled=False,  # 演示时跳过备份
        validation_enabled=True
    )
    
    workflow_manager = WorkflowManager(config)
    
    print_step(1, "获取系统状态")
    status = workflow_manager.get_system_status()
    
    db_status = status.get("database", {})
    print(f"   原始消息: {db_status.get('raw_messages', 0)}")
    print(f"   清洁消息: {db_status.get('clean_messages', 0)}")
    print(f"   未处理消息: {db_status.get('unprocessed_messages', 0)}")
    print(f"   去重比例: {db_status.get('dedup_ratio', 0):.2%}")
    
    system_status = status.get("system", {})
    print(f"   数据库版本: {system_status.get('database_version', 'N/A')}")
    print(f"   需要去重: {system_status.get('needs_deduplication', False)}")
    
    print_step(2, "执行完整工作流")
    start_time = time.time()
    success = workflow_manager.execute_complete_workflow()
    execution_time = time.time() - start_time
    
    if success:
        print(f"   ✓ 工作流执行成功，耗时 {execution_time:.2f} 秒")
        
        # 显示最终状态
        final_status = workflow_manager.get_system_status()
        workflow_stats = final_status.get("workflow_stats", {})
        print(f"   执行去重: {workflow_stats.get('total_dedups_executed', 0)} 次")
        print(f"   执行验证: {workflow_stats.get('total_validations_performed', 0)} 次")
        
    else:
        print("   ❌ 工作流执行失败")
    
    workflow_manager.close()

def demo_integration():
    """演示组件集成"""
    print_section_header("组件集成演示")
    
    print_step(1, "初始化所有组件")
    
    # 初始化组件
    db_v2 = DatabaseV2()
    backup_manager = BackupManager()
    validator = DataValidator(db_v2)
    
    dedup_config = DedupConfig(
        batch_size=50,
        create_backup_before_dedup=True,
        validation_enabled=True
    )
    deduplicator = SafeDeduplicator(db_v2, dedup_config)
    
    workflow_config = WorkflowConfig(
        auto_dedup_enabled=True,
        dedup_threshold=1,
        auto_backup_enabled=True,
        validation_enabled=True
    )
    workflow_manager = WorkflowManager(workflow_config)
    workflow_manager.db_v2 = db_v2  # 使用同一个数据库实例
    
    print("   ✓ 所有组件初始化完成")
    
    print_step(2, "执行集成工作流")
    
    try:
        # 1. 创建备份
        print("   - 创建系统备份...")
        backup_path = backup_manager.create_manual_backup("integration_demo")
        
        # 2. 验证数据
        print("   - 执行数据验证...")
        validation_result = validator.validate_database_integrity()
        print(f"     验证结果: {'通过' if validation_result.is_valid else '失败'}")
        
        # 3. 执行去重
        print("   - 执行安全去重...")
        dedup_success = deduplicator.execute_safe_deduplication()
        print(f"     去重结果: {'成功' if dedup_success else '失败'}")
        
        # 4. 再次验证
        print("   - 去重后验证...")
        post_validation = validator.validate_database_integrity()
        print(f"     验证结果: {'通过' if post_validation.is_valid else '失败'}")
        
        # 5. 生成报告
        print("   - 生成最终报告...")
        final_stats = {
            "原始消息": db_v2.db["messages_raw"].count,
            "清洁消息": db_v2.db["messages_clean"].count,
            "备份创建": "成功" if backup_path else "失败",
            "去重处理": deduplicator.stats.processed_messages,
            "去重比例": f"{deduplicator.stats.get_dedup_ratio():.2%}",
            "验证通过": validation_result.is_valid and post_validation.is_valid
        }
        
        print("\n   📊 集成演示结果:")
        for key, value in final_stats.items():
            print(f"     {key}: {value}")
            
    except Exception as e:
        print(f"   ❌ 集成演示出错: {e}")
    
    finally:
        # 清理资源
        db_v2.close()
        workflow_manager.close()

def main():
    """主演示函数"""
    print("🚀 微信监听器安全去重架构 v2.0 功能演示")
    print(f"演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 演示各个组件
        demo_database_v2()
        demo_backup_manager()
        demo_safe_deduplicator()
        demo_data_validator()
        demo_workflow_manager()
        demo_integration()
        
        print_section_header("演示完成")
        print("🎉 所有组件功能演示完成！")
        print("\n✨ 主要成果:")
        print("   ✓ 数据库架构v2.0 - 分层存储，安全可靠")
        print("   ✓ 安全去重器 - 原始数据永不删除")
        print("   ✓ 数据验证器 - 完整性检查和质量监控")
        print("   ✓ 工作流管理器 - 自动化处理和监控")
        print("   ✓ 备份管理器 - 多层备份机制")
        print("   ✓ 组件集成 - 完整的端到端解决方案")
        
    except KeyboardInterrupt:
        print("\n\n演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示过程中出现错误: {e}")
        raise

if __name__ == "__main__":
    main() 