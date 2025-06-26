import re
import json
import argparse
from typing import List, Dict


def extract_jd(text: str) -> List[Dict[str, str]]:
    """
    从聊天文本中提取JD信息，返回JD列表。
    """
    # 这里假设JD以"【JD】"开头，后面跟着内容
    pattern = r"【JD】(.+?)($|\n)"
    matches = re.findall(pattern, text, re.DOTALL)
    jds = []
    for match in matches:
        jd_content = match[0].strip()
        jds.append({"jd": jd_content})
    return jds


def main():
    parser = argparse.ArgumentParser(description="Extract JD from chat text.")
    parser.add_argument("-i", "--input", required=True, help="输入txt文件路径")
    parser.add_argument("-o", "--output", required=True, help="输出jsonl文件路径")
    parser.add_argument("--json", action="store_true", help="输出为jsonl格式")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()
    jds = extract_jd(text)

    if args.json:
        with open(args.output, "w", encoding="utf-8") as f:
            for jd in jds:
                f.write(json.dumps(jd, ensure_ascii=False) + "\n")
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            for jd in jds:
                f.write(jd["jd"] + "\n")


if __name__ == "__main__":
    main() 