import sqlite3
import random
from pathlib import Path

# --- 配置 ---
BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "data" / "test_db.db"  # 明确指向测试数据库
NUM_DUPLICATES = 3  # 我们要制造多少条重复记录

def inject_duplicates():
    """
    连接到测试数据库，随机选择几条记录，然后将它们重新插入以制造重复。
    """
    if not DB_FILE.exists():
        print(f"[!] 测试数据库文件不存在: {DB_FILE}")
        return

    try:
        conn = sqlite3.connect(str(DB_FILE))
        # 使用 Row factory 可以让我们像访问字典一样访问列数据，更方便
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        # 1. 随机选择几条现有的消息
        cursor.execute(f"SELECT * FROM messages ORDER BY RANDOM() LIMIT {NUM_DUPLICATES}")
        messages_to_duplicate = cursor.fetchall()

        if not messages_to_duplicate:
            print("[!] messages 表中没有足够的数据来制造重复，请先运行监听器。")
            return

        print(f"[*] 已随机选定 {len(messages_to_duplicate)} 条消息用于制造重复。")

        # 2. 将这些消息重新插入到表中
        insert_query = "INSERT INTO messages (group_name, sender, content, msg_type, timestamp, processed) VALUES (?, ?, ?, ?, ?, ?)"
        
        for msg in messages_to_duplicate:
            # 我们只需要提取原始数据列，id 会自动生成
            cursor.execute(insert_query, (
                msg['group_name'],
                msg['sender'],
                msg['content'],
                msg['msg_type'],
                "2099-12-31T23:59:59", # 使用一个固定的、未来的时间戳以示区别
                msg['processed']
            ))
        
        conn.commit()
        print(f"[SUCCESS] 成功向 test_db.db 注入 {len(messages_to_duplicate)} 条重复记录！")

    except Exception as e:
        print(f"[!] 注入重复数据时发生错误: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    inject_duplicates() 