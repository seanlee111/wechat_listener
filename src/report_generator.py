import pandas as pd
import sqlite3
import os
from datetime import datetime
from database import DB_FILE #直接从我们统一的配置中导入DB_FILE

# -- 路径配置 --
# 输出目录仍然可以基于脚本位置计算，或者直接使用database.py中的BASE_DIR
SCRIPT_PATH = os.path.abspath(__file__)
SRC_DIR = os.path.dirname(SCRIPT_PATH)
BASE_DIR = os.path.dirname(SRC_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, 'reports')

def generate_report():
    """
    连接数据库，读取处理后的JD数据，并生成一份Excel报告。
    报告将包含处理后的结构化数据以及原始消息内容。
    """
    # 确保数据库文件存在
    if not os.path.exists(DB_FILE):
        print(f"[!] 错误: 数据库文件 '{DB_FILE}' 不存在。")
        print("[!] 请先运行 'start.bat' 和 'process_jds.bat'。")
        return

    # 确保输出目录存在
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"[*] 已创建报告目录: '{OUTPUT_DIR}'")

    try:
        # 使用 sqlite3 连接数据库
        conn = sqlite3.connect(DB_FILE)
        
        # 构建 SQL 查询，使用 LEFT JOIN 将 jobs 和 messages 表连接起来
        # 查询所有我们关心的、在新版数据库中存在的字段
        query = """
        SELECT
            j.id,
            j.company,
            j.position,
            j.location,
            j.contact_email,
            j.resume_format,
            j.email_subject_format,
            j.full_text AS extracted_jd_text,
            m.content AS original_message_text,
            j.message_id
        FROM
            jobs j
        LEFT JOIN
            messages m ON j.message_id = m.id
        ORDER BY
            j.id DESC;
        """
        
        # 使用 pandas 直接从 SQL 查询读取数据到 DataFrame
        df = pd.read_sql_query(query, conn)
        
        # 关闭数据库连接
        conn.close()

        # 检查是否有数据
        if df.empty:
            print("[*] 'jobs' 表中没有找到任何数据可供生成报告。")
            return
            
        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(OUTPUT_DIR, f'JD_Report_{timestamp}.xlsx')
        
        # 使用 pandas 将 DataFrame 保存为 Excel 文件
        # index=False 表示不将 DataFrame 的索引写入 Excel
        df.to_excel(report_filename, index=False, engine='openpyxl')
        
        print("\n=======================================================")
        print(f"\n[SUCCESS] 报告生成成功！")
        print(f"[*] 已保存至: {report_filename}")
        print(f"[*] 共导出 {len(df)} 条JD信息。")
        print("\n=======================================================")

    except Exception as e:
        print(f"\n[!] 生成报告时发生错误: {e}")


if __name__ == "__main__":
    generate_report() 