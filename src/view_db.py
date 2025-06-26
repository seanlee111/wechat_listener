import sqlite_utils
from pathlib import Path
from tabulate import tabulate

# --- 配置 ---
BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "data" / "wechat_messages.db"

def view_latest_messages(limit=20):
    """
    连接数据库并以表格形式显示最新的消息。
    """
    if not DB_FILE.exists():
        print(f"[!] 错误：数据库文件不存在于 '{DB_FILE}'")
        print("[!] 请先运行 start.bat 并让它抓取一些消息。")
        return

    db = sqlite_utils.Database(DB_FILE)
    
    if "messages" not in db.table_names():
        print("[!] 错误：数据库中找不到 'messages' 表。")
        return

    # 查询最新的消息，按时间戳降序排列
    messages = db["messages"].rows_where(order_by="-timestamp", limit=limit)
    
    headers = ["ID", "时间戳", "群聊", "发送人", "消息类型", "内容"]
    rows = []
    
    for msg in messages:
        # 截断过长的内容以便显示
        content = (msg['content'][:80] + '...') if len(msg['content']) > 80 else msg['content']
        rows.append([
            msg['id'],
            msg['timestamp'],
            msg['group_name'],
            msg['sender'],
            msg['msg_type'],
            content.replace('\n', ' ') # 将换行符替换为空格，避免破坏表格
        ])

    if not rows:
        print("[*] 数据库中还没有任何消息。")
        return

    print(f"--- 显示数据库中最新的 {len(rows)} 条消息 ---")
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print("--------------------------------------")


if __name__ == "__main__":
    view_latest_messages() 