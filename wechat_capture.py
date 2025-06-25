# wechat_capture.py – GUI capture layer for JD listener (Windows only)
import time
import pyautogui
import pyperclip

def capture_chat(
    group_coords: tuple[int, int],
    chat_center: tuple[int, int],
    scroll_times: int = 10,
    scroll_amount: int = 500,
    pause: float = 0.5
) -> str:
    """Capture chat text from WeChat window by GUI automation."""
    xg, yg = group_coords
    xc, yc = chat_center

    # 1. Click group to open chat
    pyautogui.click(xg, yg)
    time.sleep(pause)

    # 2. Scroll up to load history and copy each time
    all_text = []
    for _ in range(scroll_times):
        pyautogui.moveTo(xc, yc)
        pyautogui.scroll(scroll_amount)
        time.sleep(pause)
        # 先左键点击激活聊天区域
        pyautogui.moveTo(xc, yc)
        pyautogui.click()
        time.sleep(0.2)
        # 再右键聊天区域并复制
        pyautogui.click(button='right')
        time.sleep(0.3)
        pyautogui.press('enter')
        time.sleep(0.3)
        text = pyperclip.paste()
        print(f"[DEBUG] 第{_+1}次复制内容前100字: {text[:100]}")
        all_text.append(text)

    # 合并所有复制到的内容，按行去重
    merged_lines = []
    seen = set()
    for block in all_text:
        for line in block.splitlines():
            if line.strip() and line not in seen:
                merged_lines.append(line)
                seen.add(line)
    merged_text = '\n'.join(merged_lines)
    return merged_text
