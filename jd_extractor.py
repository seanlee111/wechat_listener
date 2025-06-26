# jd_extractor.py – enhanced JD extractor (v2.1)
"""Enhanced command-line utility that parses raw JD text (e.g. copied from a
WeChat chat window) and extracts **structured recruiting info**:

* **email** – destination mailbox (first match)
* **location** – internship / work base (from first match in text)
* **resume_rule** – the line(s) that tell candidates how to name / format the resume
* **subject_rule** – the line(s) that define email subject naming
* **snippet** – trimmed JD paragraph for context

This version addresses missing location when it's in a separate paragraph.

Usage – same as before::

    python jd_extractor.py -i test_input.txt -o jd_YYYY-MM-DD.json --json

Output JSON lines, one JD object per match.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import re
from typing import List, Dict, Pattern

# ---------------------------------------------------------------------------
# Configurable patterns / keywords
# ---------------------------------------------------------------------------
DEFAULT_KEYWORDS = [  # presence marks a paragraph as JD-like
    "JD", "岗位", "岗位职责", "职位", "招聘", "实习", "投递", "简历", "邮箱", "日常实习",
]
EMAIL_PATTERN: Pattern[str] = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
)
LOCATION_PATTERN: Pattern[str] = re.compile(
    r"(?:地点|Base|工作地点)[:：]\s*([\u4e00-\u9fa5A-Za-z]+)"
)
RESUME_RULE_PATTERN: Pattern[str] = re.compile(r"简历(?:命名|要求)[^\n]*")
SUBJECT_RULE_PATTERN: Pattern[str] = re.compile(r"邮件主题[^\n]*")
PARA_SPLIT_PATTERN = re.compile(r"(?:\n{2,}|^.+?[：:])")

# ---------------------------------------------------------------------------
# Core extraction logic
# ---------------------------------------------------------------------------

def extract_jd(raw_text: str,
               keywords: List[str] | None = None) -> List[Dict[str, str]]:
    """Return list of structured JD dicts (see module docstring)."""
    keywords = keywords or DEFAULT_KEYWORDS

    # normalize full-width colon
    text = raw_text.replace("：", ":")

    # find global location if in separate paragraph
    global_loc = ""
    match_loc = LOCATION_PATTERN.search(text)
    if match_loc:
        global_loc = match_loc.group(1)

    # split into paragraphs
    paragraphs = [p.strip() for p in PARA_SPLIT_PATTERN.split(text) if p.strip()]

    results: List[Dict[str, str]] = []
    for para in paragraphs:
        if not any(k.lower() in para.lower() for k in keywords):
            continue
        emails = EMAIL_PATTERN.findall(para)
        if not emails:
            continue  # email required

        # attempt location in same para, fallback to global
        loc_m = LOCATION_PATTERN.search(para)
        location = loc_m.group(1) if loc_m else global_loc

        resume_match = RESUME_RULE_PATTERN.search(para)
        subject_match = SUBJECT_RULE_PATTERN.search(para)

        results.append({
            "email": emails[0],
            "location": location,
            "resume_rule": resume_match.group(0) if resume_match else "",
            "subject_rule": subject_match.group(0) if subject_match else "",
            "snippet": para[:600],
            "raw": para
        })

    return results

# ---------------------------------------------------------------------------
# CLI – output options
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Extract structured JD info from raw text."
    )
    parser.add_argument(
        "--input", "-i", type=str,
        help="Path to txt file (defaults STDIN)."
    )
    parser.add_argument(
        "--output", "-o", type=str,
        help="Write to file (JSONL if .json or --json)."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Force JSONL output to STDOUT / file."
    )
    args = parser.parse_args()

    if args.input:
        raw_text = pathlib.Path(args.input).read_text(encoding="utf-8")
    else:
        raw_text = "".join(iter(lambda: input(), ""))

    items = extract_jd(raw_text)

    def to_txt(blocks: List[Dict[str, str]]) -> str:
        lines: List[str] = [f"# JD extract {_dt.date.today()}\n\n"]
        for i, b in enumerate(blocks, 1):
            lines.append(f"[{i}] 邮箱: {b['email']}  地点: {b['location']}\n")
            if b['resume_rule']:
                lines.append(f"    简历规则: {b['resume_rule']}\n")
            if b['subject_rule']:
                lines.append(f"    主题规则: {b['subject_rule']}\n")
            lines.append(b['snippet'] + "\n\n")
        return "".join(lines)

    if args.output:
        path = pathlib.Path(args.output)
        if args.json or path.suffix.lower() == ".json":
            content = "\n".join(
                json.dumps(x, ensure_ascii=False) for x in items
            )
        else:
            content = to_txt(items)
        path.write_text(content, encoding="utf-8")
        print(f"[OK] Wrote {len(items)} JD(s) to {path}")
    else:
        if args.json:
            print("\n".join(json.dumps(x, ensure_ascii=False) for x in items))
        else:
            print(to_txt(items))


if __name__ == "__main__":
    _cli()
