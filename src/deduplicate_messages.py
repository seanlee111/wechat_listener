import sqlite3
from pathlib import Path

# --- 数据库路径配置 ---
# 和项目其他脚本保持一致，确保能找到正确的数据库文件
BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "data" / "wechat_jds.db"

def deduplicate_messages():
    """
    清理 messages 表中的重复记录。
    判断标准：group_name, sender, content 三个字段完全相同。
    保留策略：保留具有最小 id 的记录（即最早插入的记录）。
    """
    if not DB_FILE.exists():
        print(f"[!] 数据库文件不存在: {DB_FILE}")
        print("[!] 请先运行监听脚本生成数据库。")
        return

    try:
        # 使用原生 sqlite3 连接，方便执行原生 SQL
        conn = sqlite3.connect(str(DB_FILE), timeout=10)
        cursor = conn.cursor()

        # 1. 查询执行前的总行数
        cursor.execute("SELECT COUNT(*) FROM messages")
        initial_count = cursor.fetchone()[0]
        print(f"[*] 去重前，messages 表共有 {initial_count} 条记录。")

        # 2. 构建去重SQL语句
        # 这条语句会删除每个重复组中id不是最小的那些记录
        query = """
        DELETE FROM messages
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM messages
            GROUP BY group_name, sender, content
        );
        """

        # 3. 执行删除操作
        cursor.execute(query)
        conn.commit() # 提交事务，让删除生效

        # 4. 获取被删除的行数
        deleted_count = conn.total_changes
        
        # 5. 查询执行后的总行数
        cursor.execute("SELECT COUNT(*) FROM messages")
        final_count = cursor.fetchone()[0]

        if deleted_count > 0:
            print(f"\n[SUCCESS] 成功清理了 {deleted_count} 条重复记录！")
        else:
            print(f"\n[*] 未发现重复记录，无需清理。")
        
        print(f"[*] 去重后，messages 表剩余 {final_count} 条记录。")

    except Exception as e:
        print(f"\n[!] 执行去重操作时发生错误: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    print("--- 开始执行数据库消息去重任务 ---")
    deduplicate_messages()
    print("---------------------------------") 