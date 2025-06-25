# main.py – End‑to‑end runner: capture WeChat → extract JD → save JSON
"""Usage (Windows only, WeChat 必须已登录并置顶目标群/联系人):

1. 打开微信主界面，并把目标聊天置顶到左侧栏可见。
2. 将下方 CONFIG 的 group_coords & chat_center 改成你机器的坐标。
   ‑ 在 Python 交互或者 cmd 中运行: >>> import pyautogui; pyautogui.position()
     把鼠标移动到群聊条目中心处，记坐标 (x, y) → group_coords
     再移动鼠标到真正聊天内容区域中央，记坐标 → chat_center
3. pip install pyautogui pyperclip
4. python main.py
   -> 会生成 output/yyyymmdd_HHMM_jd.jsonl

后续：可把 send_to_api(result) 连到云端投递服务。
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import List, Dict

import pyautogui
import pyperclip
import subprocess

from wechat_capture import capture_chat
from jd_extractor import extract_jd

# -------------------------- USER CONFIG ------------------------------------
CONFIG = {
    "group_coords": (880, 830),   # ← 修改为你的群聊列表坐标
    "chat_center":  (1280, 1070),   # ← 修改为聊天面板中心坐标
    "scroll_times":  15,          # 向上滚 15 屏
    "scroll_amount": 500,         # 每次滚动量
    "pause":        0.5,          # 每步延时 (秒)
    "output_dir":   "output"      # 结果文件夹
}
# ---------------------------------------------------------------------------


def save_results(jds: List[Dict[str, str]]) -> Path:
    out_dir = Path(CONFIG["output_dir"])
    out_dir.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    out_path = out_dir / f"jd_{stamp}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for item in jds:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return out_path


def save_raw_text(raw_text: str) -> Path:
    out_dir = Path(CONFIG["output_dir"])
    out_dir.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    out_path = out_dir / f"chat_{stamp}.txt"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(raw_text)
    return out_path


def main() -> None:
    raw_text = capture_chat(
        group_coords=CONFIG["group_coords"],
        chat_center=CONFIG["chat_center"],
        scroll_times=CONFIG["scroll_times"],
        scroll_amount=CONFIG["scroll_amount"],
        pause=CONFIG["pause"],
    )

    chat_file = save_raw_text(raw_text)
    print(f"[✓] 聊天记录已保存到 {chat_file}")

    # 自动调用jd_extractor.py处理txt，生成jsonl
    stamp = chat_file.stem.split('_', 1)[-1]
    jd_file = chat_file.parent / f"jd_{stamp}.jsonl"
    cmd = [
        "python", "jd_extractor.py",
        "-i", str(chat_file),
        "-o", str(jd_file),
        "--json"
    ]
    print(f"[INFO] 正在提取JD信息...（命令：{' '.join(cmd)}）")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[✓] JD信息已提取到 {jd_file}")
    else:
        print("[!] JD提取失败：", result.stderr)


if __name__ == "__main__":
    pyautogui.FAILSAFE = True  # 移动到屏幕角可紧急停止脚本
    main()
