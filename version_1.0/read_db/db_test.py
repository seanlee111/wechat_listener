# db_test.py – quick scanner to list WeChat Message DBs and sample messages
"""Run on a Windows PC where *PC 微信*已登录且保存本地聊天。

It will:
1. Locate all `Msg*.db` files under your `WeChat Files` directory.
2. For each DB, print the chatroom / Talker count and show last 5 messages.
3. Allow you to input a keyword (群名 / 邮箱 / 关键字段) to filter messages.

Dependencies: only stdlib `sqlite3`, `pathlib`, `re`.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

WECHAT_ROOTS = [
    Path.home() / "Documents/WeChat Files",           # old path
    Path.home() / "Documents/WeChat Files/Accounts"   # new path >=3.9.x
]

MESSAGE_TABLE = "Message"


def find_msg_dbs() -> List[Path]:
    dbs: List[Path] = []
    for root in WECHAT_ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("Msg*.db"):
            if p.is_file():
                dbs.append(p)
    return dbs


def print_sample(db: Path, keyword: str | None = None, limit: int = 5) -> None:
    print(f"\n>>> DB: {db}")
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # SQLite schema difference across versions; safe query below
    # New schema: `TableName`, `IsSend`, `CreateTime`, `Talker`, `Content`
    where = "WHERE Content LIKE ?" if keyword else ""
    sql = f"SELECT Talker, CreateTime, substr(Content,1,100) FROM {MESSAGE_TABLE} {where} ORDER BY CreateTime DESC LIMIT {limit}"
    params = (f"%{keyword}%",) if keyword else ()
    try:
        rows = cur.execute(sql, params).fetchall()
    except sqlite3.Error as e:
        print(f"[!] Failed to query: {e}")
        return

    for talker, ts, snippet in rows:
        try:
            ts_readable = datetime.fromtimestamp(ts/1000).strftime("%Y-%m-%d %H:%M")
        except (OSError, OverflowError, ValueError):
            ts_readable = str(ts)
        print(f"[{ts_readable}] {talker}: {snippet}")

    cur.close()
    conn.close()


def main() -> None:
    dbs = find_msg_dbs()
    if not dbs:
        print("[!] 未找到 Msg*.db，请确认微信已安装并保存聊天记录。")
        return

    print(f"[i] Found {len(dbs)} database(s).")
    for idx, db in enumerate(dbs, 1):
        print(f"  {idx}. {db.relative_to(Path.home())}")

    sel = input("Select DB number to inspect (default 1): ").strip() or "1"
    try:
        db_idx = int(sel) - 1
        db_path = dbs[db_idx]
    except (ValueError, IndexError):
        print("[!] invalid selection.")
        return

    kw = input("Keyword to filter message content (press Enter to skip): ").strip()
    print_sample(db_path, keyword=kw or None)


if __name__ == "__main__":
    main()
