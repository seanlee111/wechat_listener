"""
微信群聊监听助手 - 私有化部署安装包生成器
为用户生成完整的一键安装包
"""

import os
import shutil
import zipfile
from pathlib import Path
import json

class PrivateDeploymentPackager:
    """私有化部署打包器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent  # 上级目录
        self.output_dir = self.base_dir / "deployment_packages"
        self.output_dir.mkdir(exist_ok=True)
    
    def create_personal_package(self):
        """创建个人版部署包"""
        package_name = "WeChatListener_Personal_v2.0"
        package_dir = self.output_dir / package_name
        
        # 清理并创建目录
        if package_dir.exists():
            shutil.rmtree(package_dir)
        package_dir.mkdir()
        
        # 复制核心文件
        self._copy_core_files(package_dir)
        
        # 生成个人版配置
        self._generate_personal_config(package_dir)
        
        # 生成安装脚本
        self._generate_install_scripts(package_dir, "personal")
        
        # 生成用户手册
        self._generate_user_manual(package_dir, "personal")
        
        # 压缩为ZIP
        zip_path = self.output_dir / f"{package_name}.zip"
        self._create_zip(package_dir, zip_path)
        
        print(f"✓ 个人版部署包生成完成: {zip_path}")
        return zip_path
    
    def create_professional_package(self):
        """创建专业版部署包"""
        package_name = "WeChatListener_Professional_v2.0"
        package_dir = self.output_dir / package_name
        
        if package_dir.exists():
            shutil.rmtree(package_dir)
        package_dir.mkdir()
        
        # 复制所有文件（包括高级功能）
        self._copy_all_files(package_dir)
        
        # 生成专业版配置
        self._generate_professional_config(package_dir)
        
        # 生成安装脚本
        self._generate_install_scripts(package_dir, "professional")
        
        # 生成高级用户手册
        self._generate_user_manual(package_dir, "professional")
        
        # 生成远程支持工具
        self._generate_remote_support_tools(package_dir)
        
        # 压缩为ZIP
        zip_path = self.output_dir / f"{package_name}.zip"
        self._create_zip(package_dir, zip_path)
        
        print(f"✓ 专业版部署包生成完成: {zip_path}")
        return zip_path
    
    def create_enterprise_package(self):
        """创建企业版部署包（包含源码）"""
        package_name = "WeChatListener_Enterprise_v2.0"
        package_dir = self.output_dir / package_name
        
        if package_dir.exists():
            shutil.rmtree(package_dir)
        package_dir.mkdir()
        
        # 复制完整源码
        self._copy_source_code(package_dir)
        
        # 生成企业版配置
        self._generate_enterprise_config(package_dir)
        
        # 生成开发文档
        self._generate_development_docs(package_dir)
        
        # 生成部署脚本
        self._generate_enterprise_scripts(package_dir)
        
        # 压缩为ZIP
        zip_path = self.output_dir / f"{package_name}.zip"
        self._create_zip(package_dir, zip_path)
        
        print(f"✓ 企业版部署包生成完成: {zip_path}")
        return zip_path
    
    def _copy_core_files(self, target_dir):
        """复制核心文件（个人版）"""
        # 复制必要的源文件
        src_dir = target_dir / "src"
        src_dir.mkdir()
        
        core_files = [
            "wechat_listener.py",
            "database.py", 
            "jd_extractor.py",
            "report_generator.py"
        ]
        
        for file in core_files:
            shutil.copy2(self.base_dir / "src" / file, src_dir / file)
        
        # 复制批处理脚本
        batch_scripts = [
            "start.bat",
            "process_jds.bat", 
            "generate_report.bat",
            "initialize_database.bat"
        ]
        
        for script in batch_scripts:
            if (self.base_dir / script).exists():
                shutil.copy2(self.base_dir / script, target_dir / script)
    
    def _copy_all_files(self, target_dir):
        """复制所有文件（专业版）"""
        # 复制整个src目录
        shutil.copytree(self.base_dir / "src", target_dir / "src")
        
        # 复制配置文件
        if (self.base_dir / "config").exists():
            shutil.copytree(self.base_dir / "config", target_dir / "config")
        
        # 复制批处理脚本
        for bat_file in self.base_dir.glob("*.bat"):
            shutil.copy2(bat_file, target_dir / bat_file.name)
    
    def _copy_source_code(self, target_dir):
        """复制完整源码（企业版）"""
        # 排除列表
        exclude_dirs = {".git", "__pycache__", "venv", "data", "reports", "logs", "backups"}
        exclude_files = {"*.pyc", "*.log", "*.db", "*.sqlite"}
        
        # 复制整个项目
        for item in self.base_dir.iterdir():
            if item.name not in exclude_dirs:
                if item.is_dir():
                    shutil.copytree(item, target_dir / item.name, 
                                  ignore=shutil.ignore_patterns(*exclude_files))
                else:
                    shutil.copy2(item, target_dir / item.name)
    
    def _generate_personal_config(self, target_dir):
        """生成个人版配置"""
        config = {
            "version": "Personal",
            "listener": {
                "target_groups": ["请修改为你的微信群名称"],
                "check_interval_seconds": 10
            },
            "features": {
                "basic_monitoring": True,
                "jd_extraction": True,
                "excel_reports": True,
                "advanced_dedup": False,
                "batch_processing": False
            }
        }
        
        config_dir = target_dir / "config"
        config_dir.mkdir(exist_ok=True)
        
        with open(config_dir / "listener_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _generate_install_scripts(self, target_dir, version):
        """生成安装脚本"""
        # Windows安装脚本
        install_bat = f"""@echo off
chcp 65001 > nul
echo ===============================================
echo   微信群聊监听助手 {version.upper()}版 安装程序
echo ===============================================
echo.

echo [1/5] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✓ Python环境正常

echo.
echo [2/5] 创建虚拟环境...
python -m venv venv
if errorlevel 1 (
    echo ❌ 虚拟环境创建失败
    pause
    exit /b 1
)
echo ✓ 虚拟环境创建成功

echo.
echo [3/5] 激活虚拟环境并安装依赖...
call venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install wxauto sqlite-utils pandas openpyxl tabulate
if errorlevel 1 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)
echo ✓ 依赖安装成功

echo.
echo [4/5] 初始化数据库...
python src\\initialize_database.py
if errorlevel 1 (
    echo ⚠️ 数据库初始化失败，但可以手动运行
)
echo ✓ 数据库初始化完成

echo.
echo [5/5] 创建数据目录...
if not exist "data" mkdir data
if not exist "reports" mkdir reports
echo ✓ 目录创建完成

echo.
echo ===============================================
echo   🎉 安装完成！
echo ===============================================
echo.
echo 使用方法:
echo   1. 双击 "启动监听.bat" 开始监听
echo   2. 双击 "生成报告.bat" 生成Excel报告
echo.
echo 配置文件: config\\listener_config.json
echo 使用手册: 用户手册.pdf
echo.
pause
"""
        
        with open(target_dir / "安装程序.bat", "w", encoding="gbk") as f:
            f.write(install_bat)
        
        # 生成启动脚本
        start_bat = """@echo off
chcp 65001 > nul
echo 启动微信群聊监听助手...
call venv\\Scripts\\activate
python src\\wechat_listener.py
pause
"""
        
        with open(target_dir / "启动监听.bat", "w", encoding="gbk") as f:
            f.write(start_bat)
    
    def _generate_user_manual(self, target_dir, version):
        """生成用户手册"""
        manual_content = f"""
# 微信群聊监听助手 {version.upper()}版 用户手册

## 安装步骤
1. 解压下载的文件包
2. 双击运行"安装程序.bat"
3. 等待安装完成

## 使用步骤
1. 确保微信已登录
2. 编辑 config/listener_config.json，设置要监听的群名称
3. 双击"启动监听.bat"开始监听
4. 双击"生成报告.bat"生成Excel报告

## 配置说明
- target_groups: 要监听的微信群名称列表
- check_interval_seconds: 检查间隔（秒）

## 注意事项
1. 确保微信保持登录状态
2. 群名称必须完全一致
3. 生成的报告在reports文件夹中

## 技术支持
- 使用问题请联系技术支持
- 企业用户享有优先支持服务
"""
        
        with open(target_dir / "用户手册.md", "w", encoding="utf-8") as f:
            f.write(manual_content)
    
    def _generate_remote_support_tools(self, target_dir):
        """生成远程支持工具"""
        # 诊断脚本
        diagnostic_script = """@echo off
chcp 65001 > nul
echo 系统诊断报告
echo ==================

echo [Python环境]
python --version
echo.

echo [已安装包]
call venv\\Scripts\\activate
pip list
echo.

echo [数据库状态]
if exist "data\\wechat_jds.db" (
    echo ✓ 数据库文件存在
) else (
    echo ❌ 数据库文件不存在
)
echo.

echo [配置文件]
if exist "config\\listener_config.json" (
    echo ✓ 配置文件存在
    type config\\listener_config.json
) else (
    echo ❌ 配置文件不存在
)

pause
"""
        
        with open(target_dir / "系统诊断.bat", "w", encoding="gbk") as f:
            f.write(diagnostic_script)
    
    def _create_zip(self, source_dir, zip_path):
        """创建ZIP压缩包"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)

def main():
    """主函数"""
    packager = PrivateDeploymentPackager()
    
    print("🚀 开始生成私有化部署包...")
    
    # 生成所有版本
    personal_package = packager.create_personal_package()
    professional_package = packager.create_professional_package()
    enterprise_package = packager.create_enterprise_package()
    
    print("\n✅ 所有部署包生成完成！")
    print(f"📦 个人版: {personal_package}")
    print(f"📦 专业版: {professional_package}")
    print(f"📦 企业版: {enterprise_package}")
    
    print("\n💼 商业化部署建议:")
    print("1. 个人版 - 直接销售给个人用户")
    print("2. 专业版 - 提供技术支持服务") 
    print("3. 企业版 - 提供定制开发服务")

if __name__ == "__main__":
    main() 