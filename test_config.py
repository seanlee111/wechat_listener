#!/usr/bin/env python3
"""
配置文件测试脚本
只测试配置加载和显示，不启动监听器
"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.append('src')

from config_loader import ConfigLoader

def test_config(config_file: str = "config/listener_config.json"):
    """测试配置文件"""
    try:
        print("[INFO] 测试配置文件系统")
        print(f"[FILE] 配置文件: {config_file}")
        print()
        
        # 检查配置文件是否存在
        if not Path(config_file).exists():
            print(f"[ERROR] 配置文件不存在: {config_file}")
            print("[TIP] 请先运行: python start_listener_with_config.py --create-template")
            return False
        
        # 加载配置
        print("[LOAD] 正在加载配置文件...")
        loader = ConfigLoader(config_file)
        config = loader.load_config()
        
        # 显示配置摘要
        print("[OK] 配置文件加载成功！")
        print()
        
        loader.app_config = config
        summary = loader.get_listener_summary()
        print(summary)
        
        print()
        print("[CHECK] 配置验证:")
        
        # 验证群名称
        groups = config.listener.target_groups
        if "请修改为你的微信群名称" in str(groups):
            print("[WARN] 警告: 请修改target_groups为实际的微信群名称")
        else:
            print(f"[OK] 目标群聊已配置: {len(groups)}个群")
        
        # 验证配置合理性
        if config.listener.check_interval_seconds < 5:
            print("[WARN] 警告: 监听间隔过短，可能影响性能")
        elif config.listener.check_interval_seconds > 60:
            print("[WARN] 警告: 监听间隔过长，可能错过消息")
        else:
            print("[OK] 监听间隔设置合理")
        
        if config.workflow.dedup_threshold < 10:
            print("[WARN] 警告: 去重阈值过低，会频繁执行去重")
        elif config.workflow.dedup_threshold > 500:
            print("[WARN] 警告: 去重阈值过高，可能积压过多数据")
        else:
            print("[OK] 去重阈值设置合理")
        
        print()
        print("[DONE] 配置测试完成！现在可以运行:")
        print("       python start_listener_with_config.py")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 配置测试失败: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试配置文件")
    parser.add_argument(
        '-c', '--config', 
        default='config/listener_config.json',
        help='配置文件路径'
    )
    
    args = parser.parse_args()
    test_config(args.config) 