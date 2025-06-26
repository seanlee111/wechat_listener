import sqlite_utils
import sqlite3
from pathlib import Path
import datetime

# --- 配置 ---
# 获取项目根目录 (version2.0)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True) # 确保data目录存在
DB_FILE = DATA_DIR / "wechat_jds.db" # 统一数据库名称

# --- 数据库操作 (最终修复版) ---
def get_db():
    """
    获取数据库连接实例。
    使用原生 sqlite3 创建连接以确保 timeout 参数可用，
    然后用 sqlite-utils 包装它以方便使用。
    """
    conn = sqlite3.connect(str(DB_FILE), timeout=15.0) # 关键修复
    return sqlite_utils.Database(conn)

def setup_database():
    """
    初始化数据库和表结构。
    如果表或列不存在，会自动创建或添加，实现简单的数据库迁移。
    """
    db = get_db()
    messages_table = db["messages"]

    # 1. 确保 messages 表存在
    messages_table.create({
        "id": int,
        "group_name": str,
        "sender": str,
        "content": str,
        "msg_type": str,
        "timestamp": str
    }, pk="id", if_not_exists=True)

    # 2. 检查并添加 processed 列 (使用原生SQL，保证兼容性)
    if "processed" not in messages_table.columns_dict:
        try:
            # 直接执行SQL语句，这是最健壮的方式
            db.execute("ALTER TABLE [messages] ADD COLUMN [processed] INTEGER DEFAULT 0;")
            print("[*] 成功为 'messages' 表添加 'processed' 列。")
        except Exception as e:
            print(f"[!] 添加 'processed' 列时出错: {e}")

    # 3. 创建索引
    messages_table.create_index(["group_name"], if_not_exists=True)
    messages_table.create_index(["sender"], if_not_exists=True)
    messages_table.create_index(["timestamp"], if_not_exists=True)
    messages_table.create_index(["processed"], if_not_exists=True)
    
    # 4. 确保 jobs 表存在 (恢复到包含邮件功能的版本)
    db["jobs"].create({
        "id": int,
        "message_id": int, # 关联到原始消息的ID
        "company": str,
        "position": str,
        "location": str,
        "contact_email": str, # 统一命名为 contact_email
        "resume_format": str,
        "email_subject_format": str,
        "full_text": str, # 存储JD全文
        "parsed_at": str
    }, pk="id", if_not_exists=True, foreign_keys=[("message_id", "messages", "id")])

    # 检查并添加缺失的列，实现自动化的数据库迁移
    jobs_table = db["jobs"]
    required_columns = {
        "contact_email": str,
        "resume_format": str,
        "email_subject_format": str
    }

    for col, col_type in required_columns.items():
        if col not in jobs_table.columns_dict:
            try:
                jobs_table.add_column(col, col_type)
                print(f"[*] 成功为 'jobs' 表添加 '{col}' 列。")
            except Exception as e:
                print(f"[!] 添加 '{col}' 列时出错: {e}")

    # 为了保持整洁，移除当前版本不再使用的列
    columns_to_remove = ["salary", "experience", "education", "email"]
    for col in columns_to_remove:
        if col in jobs_table.columns_dict:
            try:
                jobs_table.transform(drop={col})
                print(f"[*] 已从 'jobs' 表中移除不再使用的 '{col}' 列。")
            except Exception:
                pass # 忽略错误

    print(f"[*] 数据库结构检查完毕，已准备就绪。")

def save_message(group_name: str, sender: str, content: str, msg_type: str):
    """
    保存单条消息到数据库。
    """
    db = get_db()
    table = db["messages"]
    
    # 准备要插入的数据
    to_insert = {
        "group_name": group_name,
        "sender": sender,
        "content": content,
        "msg_type": str(msg_type), # 确保类型是字符串
        "timestamp": datetime.datetime.now().isoformat(),
        "processed": 0 # 新消息默认为未处理
    }
    
    try:
        table.insert(to_insert, pk="id")
        # print(f"[*] 消息已存入数据库: [{group_name}] {sender}") # 可以取消注释用于调试
    except Exception as e:
        print(f"[!] 数据库存储失败: {e}")

def save_job(db, job_data: dict):
    """
    保存提取出的JD信息到 jobs 表。
    """
    table = db["jobs"]
    job_data["parsed_at"] = datetime.datetime.now().isoformat()
    try:
        table.insert(job_data, pk="id")
    except Exception as e:
        print(f"[!] JD信息存储失败: {e}")

def mark_message_as_processed(db, message_id: int):
    """
    将消息标记为已处理。
    """
    table = db["messages"]
    try:
        table.update(message_id, {"processed": 1})
    except Exception as e:
        print(f"[!] 标记消息为已处理时失败: {e}")

if __name__ == '__main__':
    # 作为脚本运行时，执行初始化
    setup_database()
    # 测试保存一条消息
    save_message("测试群", "测试用户", "这是一条测试消息", "Text")
    print("[*] 数据库模块自检完成。") 