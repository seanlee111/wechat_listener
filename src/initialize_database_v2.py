"""
微信监听器数据库初始化脚本 v2.0
初始化和更新数据库到最新架构
"""

from database_v2 import DatabaseV2, setup_database
from backup_manager import BackupManager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_database_v2():
    """初始化数据库到v2.0架构"""
    print("=== 微信监听器数据库初始化 v2.0 ===")
    
    try:
        # 1. 创建备份管理器
        backup_manager = BackupManager()
        
        # 2. 初始化数据库v2.0架构
        print("\n正在初始化数据库架构...")
        db_v2 = DatabaseV2()
        
        # 检查当前版本
        current_version = db_v2.get_db_version()
        print(f"当前数据库版本: {current_version}")
        
        # 如果需要升级，先创建备份
        if current_version != "2.0":
            print("检测到需要升级，正在创建备份...")
            backup_path = backup_manager.create_automatic_backup("database_upgrade")
            if backup_path:
                print(f"✓ 升级前备份创建成功: {backup_path}")
            else:
                print("⚠ 备份创建失败，但继续执行升级")
        
        # 设置数据库架构
        success = db_v2.setup_database_v2()
        
        if success:
            print("✓ 数据库架构初始化成功!")
            
            # 显示架构信息
            print("\n数据库架构信息:")
            tables = db_v2.db.table_names()
            for table in sorted(tables):
                count = db_v2.db[table].count
                print(f"  {table}: {count} 条记录")
            
            print(f"\n当前数据库版本: {db_v2.get_db_version()}")
            
        else:
            print("❌ 数据库架构初始化失败!")
            return False
            
        db_v2.close()
        
        print("\n=== 数据库初始化完成 ===")
        return True
        
    except Exception as e:
        print(f"❌ 初始化过程中发生错误: {e}")
        logger.error(f"数据库初始化失败: {e}")
        return False

def test_database_functionality():
    """测试数据库基本功能"""
    print("\n=== 测试数据库功能 ===")
    
    try:
        db_v2 = DatabaseV2()
        
        # 测试保存消息
        print("测试保存消息...")
        msg_id = db_v2.save_raw_message(
            "测试群", "测试用户", "这是一条初始化测试消息", "Text"
        )
        if msg_id:
            print(f"✓ 消息保存成功，ID: {msg_id}")
        
        # 测试获取未处理消息
        print("测试获取未处理消息...")
        unprocessed = db_v2.get_unprocessed_raw_messages(5)
        print(f"✓ 找到 {len(unprocessed)} 条未处理消息")
        
        # 测试批次日志
        print("测试批次日志...")
        batch_id = db_v2.generate_batch_id()
        log_id = db_v2.log_processing_batch(
            batch_id, "test", "completed", 
            records_processed=1
        )
        if log_id:
            print(f"✓ 批次日志记录成功")
        
        db_v2.close()
        print("✓ 数据库功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 数据库功能测试失败: {e}")
        return False

if __name__ == "__main__":
    # 执行初始化
    success = initialize_database_v2()
    
    if success:
        # 执行功能测试
        test_success = test_database_functionality()
        
        if test_success:
            print("\n🎉 数据库v2.0初始化和测试全部完成!")
        else:
            print("\n⚠ 数据库初始化成功，但功能测试失败")
    else:
        print("\n❌ 数据库初始化失败!") 