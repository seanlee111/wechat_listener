import subprocess
import sys
from pathlib import Path

def run_script(script_path: Path):
    """
    使用与当前脚本相同的 Python 解释器来运行指定的脚本。
    这能确保子进程也在同一个虚拟环境中运行。
    """
    # 获取当前正在运行的 Python 解释器的路径 (确保使用的是 venv 中的 python)
    python_executable = sys.executable
    
    print(f"\\n--- 正在执行脚本: {script_path.name} ---")
    try:
        # subprocess.run 会阻塞，直到子进程完成，这正是我们需要的
        subprocess.run(
            [python_executable, str(script_path)],
            check=True  # 如果脚本返回非零退出码（即出错），则会引发异常
        )
        print(f"--- 脚本执行完毕: {script_path.name} ---\\n")
        return True
    except FileNotFoundError:
        print(f"[!] 错误: 找不到 Python 解释器 '{python_executable}'")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[!] 运行 {script_path.name} 时出错，返回码: {e.returncode}")
        return False
    except Exception as e:
        print(f"[!] 运行 {script_path.name} 时发生未知错误: {e}")
        return False

def main_workflow():
    """
    定义并执行主工作流：
    1. 运行微信监听脚本。
    2. 监听结束后，运行数据库去重脚本。
    """
    base_dir = Path(__file__).resolve().parent.parent  # 上级目录
    src_dir = base_dir / "src"
    
    listener_script = src_dir / "wechat_listener.py"
    deduplicator_script = src_dir / "deduplicate_messages.py"
    
    print("=======================================================")
    print("          启动微信监听与数据清洗工作流")
    print("=======================================================")
    
    # --- 步骤 1: 运行监听器 ---
    print("\\n>>> 步骤 1: 启动微信监听器。")
    print(">>> 当需要停止时，请在监听器窗口按下 [Esc] 键。")
    listener_success = run_script(listener_script)
    
    if not listener_success:
        print("\\n[!] 监听脚本运行失败，工作流中止。")
        return

    # --- 步骤 2: 运行去重脚本 ---
    print("\\n>>> 步骤 2: 监听已停止，开始执行数据库消息去重。")
    deduplicator_success = run_script(deduplicator_script)
    
    if not deduplicator_success:
         print("\\n[!] 数据库去重脚本运行失败。")

    print("\\n=======================================================")
    print("          所有任务执行完毕！")
    print("=======================================================")

if __name__ == "__main__":
    main_workflow() 