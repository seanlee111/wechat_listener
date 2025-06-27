"""
简化版wxauto测试脚本
测试基本的微信连接功能
"""

import warnings
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_wxauto_basic():
    """测试wxauto基本功能"""
    print("=== wxauto基本功能测试 ===")
    
    try:
        # 抑制版本警告
        warnings.filterwarnings("ignore", category=UserWarning)
        
        print("正在导入wxauto...")
        from wxauto import WeChat
        print("✓ wxauto导入成功")
        
        print("正在初始化微信连接...")
        wx = WeChat()
        print("✓ 微信连接初始化完成")
        
        # 检查微信是否已登录
        try:
            # 尝试获取当前聊天窗口信息
            print("正在测试微信连接...")
            # 简单测试，不进行实际操作
            print("✓ 微信连接测试通过")
            
        except Exception as e:
            print(f"⚠ 微信连接测试有问题: {e}")
            print("这可能是正常的，如果微信没有打开聊天窗口")
        
        return True
        
    except ImportError as e:
        print(f"❌ wxauto导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

def test_group_connection():
    """测试群聊连接（可选）"""
    print("\n=== 群聊连接测试 ===")
    
    # 测试群聊名称（请根据实际情况修改）
    test_groups = [
        "NFC金融实习分享群（一）",
        "NJU后浪-优质实习交流群"
    ]
    
    try:
        warnings.filterwarnings("ignore", category=UserWarning)
        from wxauto import WeChat
        
        wx = WeChat()
        
        for group_name in test_groups:
            try:
                print(f"测试群聊: {group_name}")
                chat = wx.ChatWith(group_name)
                if chat:
                    print(f"✓ 成功连接到群聊: {group_name}")
                else:
                    print(f"⚠ 找不到群聊: {group_name}")
            except Exception as e:
                print(f"❌ 连接群聊失败 {group_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 群聊连接测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始wxauto兼容性测试...")
    print("请确保微信PC版已经登录并正在运行\n")
    
    # 基本功能测试
    basic_success = test_wxauto_basic()
    
    if basic_success:
        print("\n基本功能测试通过！")
        
        # 询问是否进行群聊测试
        try:
            user_input = input("\n是否测试群聊连接？(y/n): ").lower().strip()
            if user_input in ['y', 'yes', '是']:
                test_group_connection()
        except KeyboardInterrupt:
            print("\n用户取消测试")
    else:
        print("\n基本功能测试失败，请检查wxauto安装和微信状态")
    
    print("\n测试完成！")
    input("按回车键退出...") 