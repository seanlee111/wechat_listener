"""
阶段3简化演示 - 安全去重架构v2.0 (编码兼容版)
展示核心功能：安全去重器、数据验证器、工作流管理器
修复Windows编码兼容性问题
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

def print_header(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def demo_core_features():
    """演示核心功能"""
    print_header("微信监听器安全去重架构 v2.0 - 核心功能演示")
    print(f"演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 数据库v2.0演示
    print_header("1. 数据库架构 v2.0")
    db_v2 = DatabaseV2()
    print(f"[OK] 数据库版本: {db_v2.get_db_version()}")
    print(f"[OK] 数据表: {db_v2.db.table_names()}")
    
    try:
        raw_count = db_v2.db["messages_raw"].count
        clean_count = db_v2.db["messages_clean"].count
        print(f"[OK] 原始消息: {raw_count} 条")
        print(f"[OK] 清洁消息: {clean_count} 条")
        
        unprocessed = db_v2.get_unprocessed_raw_messages(limit=1)
        print(f"[OK] 待处理消息: {len(unprocessed)} 条（样例）")
    except Exception as e:
        print(f"[ERROR] 数据统计错误: {e}")
    
    # 2. 数据验证器演示
    print_header("2. 数据验证器")
    validator = DataValidator(db_v2)
    
    print("执行数据库完整性验证...")
    result = validator.validate_database_integrity()
    
    print(f"[OK] 验证结果: {'通过' if result.is_valid else '失败'}")
    print(f"[OK] 错误数量: {result.error_count}")
    print(f"[OK] 警告数量: {result.warning_count}")
    
    if result.warnings:
        print("主要警告:")
        for warning in result.warnings[:2]:
            print(f"  - {warning}")
    
    # 3. 安全去重器演示  
    print_header("3. 安全去重器")
    
    config = DedupConfig(
        batch_size=100,
        create_backup_before_dedup=False,  # 简化演示
        validation_enabled=True
    )
    
    deduplicator = SafeDeduplicator(db_v2, config)
    
    print("执行安全去重...")
    start_time = time.time()
    success = deduplicator.execute_safe_deduplication()
    execution_time = time.time() - start_time
    
    if success:
        print("[OK] 去重执行成功")
        stats = deduplicator.stats
        print(f"[OK] 处理消息: {stats.processed_messages} 条")
        print(f"[OK] 清洁消息: {stats.clean_messages} 条") 
        print(f"[OK] 重复消息: {stats.duplicate_messages} 条")
        print(f"[OK] 去重比例: {stats.get_dedup_ratio():.2%}")
        print(f"[OK] 执行时间: {execution_time:.2f} 秒")
    else:
        print("[ERROR] 去重执行失败")
    
    # 4. 工作流管理器演示
    print_header("4. 工作流管理器")
    
    workflow_config = WorkflowConfig(
        auto_dedup_enabled=True,
        dedup_threshold=1,
        auto_backup_enabled=False,  # 简化演示
        validation_enabled=True
    )
    
    workflow_manager = WorkflowManager(workflow_config)
    workflow_manager.db_v2 = db_v2
    
    print("获取系统状态...")
    status = workflow_manager.get_system_status()
    
    db_status = status.get("database", {})
    print(f"[OK] 原始消息: {db_status.get('raw_messages', 0)}")
    print(f"[OK] 清洁消息: {db_status.get('clean_messages', 0)}")
    print(f"[OK] 去重比例: {db_status.get('dedup_ratio', 0):.2%}")
    
    print("执行完整工作流...")
    workflow_success = workflow_manager.execute_complete_workflow()
    
    if workflow_success:
        print("[OK] 工作流执行成功")
        final_status = workflow_manager.get_system_status()
        workflow_stats = final_status.get("workflow_stats", {})
        print(f"[OK] 去重执行次数: {workflow_stats.get('total_dedups_executed', 0)}")
        print(f"[OK] 验证执行次数: {workflow_stats.get('total_validations_performed', 0)}")
    else:
        print("[ERROR] 工作流执行失败")
    
    # 5. 最终统计
    print_header("5. 最终结果统计")
    
    try:
        final_raw = db_v2.db["messages_raw"].count
        final_clean = db_v2.db["messages_clean"].count
        final_logs = db_v2.db["processing_logs"].count
        
        print(f"[OK] 最终原始消息: {final_raw} 条")
        print(f"[OK] 最终清洁消息: {final_clean} 条")
        print(f"[OK] 处理日志记录: {final_logs} 条")
        print(f"[OK] 整体去重比例: {(final_clean/final_raw*100):.1f}%" if final_raw > 0 else "[OK] 无数据")
        
        # 检查数据完整性
        processed_raw = list(db_v2.db.execute(
            "SELECT COUNT(*) FROM messages_raw WHERE processed_status = 1"
        ))[0][0]
        print(f"[OK] 已处理原始消息: {processed_raw} 条")
        
    except Exception as e:
        print(f"[ERROR] 最终统计出错: {e}")
    
    # 清理资源
    workflow_manager.close()
    db_v2.close()
    
    # 6. 总结
    print_header("演示完成")
    print("阶段3安全去重架构演示成功完成！")
    print("\n主要成果:")
    print("   [+] 数据库架构v2.0 - 分层存储，保护原始数据")
    print("   [+] 安全去重器 - 高效去重，不删除原始数据")
    print("   [+] 数据验证器 - 完整性检查和质量监控")
    print("   [+] 工作流管理器 - 自动化处理和状态监控")
    print("   [+] 系统集成 - 各组件协同工作")
    
    print("\n安全特性:")
    print("   [+] 原始数据永不删除")
    print("   [+] 分层处理架构")
    print("   [+] 完整的日志追踪")
    print("   [+] 数据完整性验证")
    print("   [+] 错误恢复机制")

if __name__ == "__main__":
    try:
        demo_core_features()
    except KeyboardInterrupt:
        print("\n\n演示被用户中断")
    except Exception as e:
        print(f"\n\n[ERROR] 演示失败: {e}")
        import traceback
        traceback.print_exc() 