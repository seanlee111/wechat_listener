from jd_extractor import extract_jd_info
from pathlib import Path
from tabulate import tabulate

# --- 配置 ---
BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_FILE = BASE_DIR / "data" / "sample_jds.txt"

def test_extractor_with_file():
    """
    从 sample_jds.txt 文件读取内容，并测试JD提取逻辑。
    """
    if not SAMPLE_FILE.exists():
        print(f"[!] 测试文件不存在: {SAMPLE_FILE}")
        return
        
    print(f"--- 开始从 '{SAMPLE_FILE.name}' 测试JD提取逻辑 ---")
    
    with open(SAMPLE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    jds = content.split('---<SEPARATOR>---')
    
    results = []
    headers = ["邮箱", "职位", "地点", "简历格式", "提取成功?"]

    for i, jd_text in enumerate(jds):
        if not jd_text.strip():
            continue
            
        print(f"\n--- 正在处理第 {i+1} 个样本 ---")
        extracted_data = extract_jd_info(jd_text)
        
        if extracted_data:
            print("[+] 提取成功!")
            results.append([
                extracted_data.get('email', 'N/A'),
                (extracted_data.get('position', 'N/A')[:20] + '...') if len(extracted_data.get('position', 'N/A')) > 20 else extracted_data.get('position', 'N/A'),
                extracted_data.get('location', 'N/A'),
                (extracted_data.get('resume_format', 'N/A')[:30] + '...') if len(extracted_data.get('resume_format', 'N/A')) > 30 else extracted_data.get('resume_format', 'N/A'),
                "是"
            ])
        else:
            print("[-] 提取失败 (可能是因为没有邮箱，这符合预期)。")
            results.append(["N/A", "N/A", "N/A", "N/A", "否"])

    print("\n\n--- 提取结果汇总 ---")
    print(tabulate(results, headers=headers, tablefmt="grid"))
    print("----------------------")


if __name__ == "__main__":
    test_extractor_with_file() 