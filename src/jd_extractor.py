import re
import json
from database import get_db, save_job, mark_message_as_processed, setup_database

# --- 正则表达式定义 (精准版) ---
RE_EMAIL = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# 正则表达式模式库
#  - (模式, 默认值)
# 模式应该包含一个捕获组 ( ... )
EXTRACTION_PATTERNS = {
    "company": [
        (r"(?:公司|company)\s*[:：\s]*\s*(.+)", "未知公司"),
        (r"(.+?)\s*(?:正在招聘|is hiring)", "未知公司")
    ],
    "position": [
        (r"(?:职位|岗位|position)\s*[:：\s]*\s*(.+)", "未知职位"),
        (r"招(?:聘)?\s*[:：\s]?\s*([^\s,，]+)", "未知职位")
    ],
    "salary": [
        (r"(?:薪资|salary|待遇)\s*[:：\s]*\s*(\d+k-\d+k|\d+-\d+k|\d+-\d+K|\d+K-\d+K|[\d.]+[wW]?\s*-\s*[\d.]+[wW]?|面议)", "面议"),
        (r"(\d+k-\d+k|\d+-\d+k|\d+-\d+K|\d+K-\d+K)", "面议")
    ],
    "location": [
        (r"(?:地点|城市|location|坐标)\s*[:：\s]*\s*(\w+)", "远程"),
        (r"工作地点\s*[:：\s]*\s*(\w+)", "远程")
    ],
    "experience": [
        (r"(?:经验|experience|年限)\s*[:：\s]*\s*(.+)", "不限"),
        (r"(\d-\d年|\d+年)", "不限")
    ],
    "education": [
        (r"(?:学历|education)\s*[:：\s]*\s*(.+)", "不限"),
        (r"(本科|硕士|博士)", "不限")
    ],
    "contact_email": [
        (r"(?:邮箱|投递邮箱|email)\s*[:：\s]*\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", "无"),
        (r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", "无")
    ],
    "resume_format": [
        (r"(?:简历命名|简历文件名|简历文件命名|简历命名为)\s*[:：]?\s*(.+)", "【简历】姓名-学校-岗位"),
    ],
    "email_subject_format": [
        (r"(?:邮件主题|主题)\s*[:：]?\s*(.+)", "【应聘】姓名-学校-岗位"),
    ]
}

# --- 提取逻辑 (精准版) ---
def extract_field(text, field_name):
    """
    根据字段名从文本中提取信息。
    """
    patterns = EXTRACTION_PATTERNS.get(field_name, [])
    for pattern, default_value in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            # 清理提取到的字符串
            return match.group(1).strip().replace('"', '').replace("'", "").replace("“", "").replace("”", "")
    return default_value

def extract_jd_info(text):
    """
    从给定的文本中提取结构化的JD信息。
    """
    return {
        "company": extract_field(text, "company"),
        "position": extract_field(text, "position"),
        "location": extract_field(text, "location"),
        "contact_email": extract_field(text, "contact_email"),
        "resume_format": extract_field(text, "resume_format"),
        "email_subject_format": extract_field(text, "email_subject_format"),
        "full_text": text
    }

def reprocess_all_messages():
    """
    重新处理数据库中的所有消息，用于测试和迭代正则表达式。
    - 首先清空 jobs 表。
    - 然后重新扫描 messages 表中的每一条消息。
    - 不再修改 messages 表的 'processed' 状态。
    """
    db = get_db()
    
    # 检查数据库结构
    if "messages" not in db.table_names() or "jobs" not in db.table_names():
        print("\n[!] 错误：数据库或表结构不正确。")
        print("[!] 请先运行 'initialize_database.bat' 来创建或修复数据库。")
        return

    # 1. 清空旧的提取结果
    print("[*] 正在清空旧的JD提取结果 (jobs table)...")
    db["jobs"].delete_where()

    print("[*] 开始重新处理所有消息...")
    all_messages = db["messages"].rows
    count = 0
    total = db["messages"].count
    
    for i, message in enumerate(all_messages):
        # 打印进度
        print(f"\r -> 正在处理: {i+1}/{total}", end="")

        jd_data = extract_jd_info(message["content"])
        
        if jd_data:
            jd_data["message_id"] = message["id"]
            save_job(db, jd_data)
            count += 1
            
    print(f"\n\n[*] 处理完成！从 {total} 条消息中，共提取到 {count} 条新的JD信息。")


if __name__ == "__main__":
    reprocess_all_messages() 