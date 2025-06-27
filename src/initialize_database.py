from database import setup_database
from wxauto import WeChat

if __name__ == "__main__":
    print("--- 开始初始化/更新数据库结构 ---")
    setup_database()
    print("\n--- 数据库已是最新状态 ---") 