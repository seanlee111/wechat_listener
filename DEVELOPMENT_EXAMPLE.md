# 实际开发流程示例

## 示例：添加邮件自动发送功能

### 第一步：准备开发环境

```bash
# 1. 确保在develop分支
git checkout develop

# 2. 拉取最新代码
git pull origin develop

# 3. 创建功能分支
git checkout -b feature/email-automation
```

### 第二步：开发过程

#### 2.1 创建邮件发送模块
```python
# src/email_sender.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailSender:
    def __init__(self, smtp_server, port, username, password):
        self.smtp_server = smtp_server
        self.port = port
        self.username = username
        self.password = password
    
    def send_jd_email(self, to_email, job_info):
        # 邮件发送逻辑
        pass
```

#### 2.2 提交第一个功能
```bash
git add src/email_sender.py
git commit -m "feat(email): 创建邮件发送基础模块

- 添加EmailSender类
- 实现SMTP连接配置
- 添加邮件发送基础方法"
```

#### 2.3 集成到数据库模块
```python
# 修改 src/database.py
from email_sender import EmailSender

def send_jd_notification(job_data):
    # 发送邮件通知逻辑
    pass
```

#### 2.4 提交集成代码
```bash
git add src/database.py
git commit -m "feat(database): 集成邮件通知功能

- 添加邮件通知方法
- 在JD保存时自动发送通知
- 支持自定义邮件模板"
```

#### 2.5 添加配置文件
```python
# src/config.py
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'port': 587,
    'username': 'your-email@gmail.com',
    'password': 'your-app-password'
}
```

#### 2.6 提交配置
```bash
git add src/config.py
git commit -m "feat(config): 添加邮件配置模块

- 创建邮件服务器配置
- 支持Gmail SMTP
- 添加安全配置选项"
```

### 第三步：测试和优化

#### 3.1 创建测试文件
```python
# src/test_email.py
from email_sender import EmailSender
from config import EMAIL_CONFIG

def test_email_sending():
    sender = EmailSender(**EMAIL_CONFIG)
    # 测试代码
    pass
```

#### 3.2 提交测试代码
```bash
git add src/test_email.py
git commit -m "test(email): 添加邮件发送测试

- 创建邮件发送测试用例
- 验证SMTP连接
- 测试邮件模板功能"
```

### 第四步：完成功能开发

#### 4.1 推送到远程
```bash
git push origin feature/email-automation
```

#### 4.2 合并到develop分支
```bash
# 切换回develop分支
git checkout develop

# 拉取最新代码
git pull origin develop

# 合并功能分支
git merge feature/email-automation

# 推送到远程
git push origin develop

# 删除本地功能分支
git branch -d feature/email-automation
```

### 第五步：发布新版本

#### 5.1 合并到master
```bash
# 切换到master分支
git checkout master

# 合并develop分支
git merge develop

# 创建版本标签
git tag -a v2.1.0 -m "添加邮件自动发送功能"

# 推送到远程
git push origin master
git push origin v2.1.0
```

## 常见问题和解决方案

### 问题1：合并冲突
```bash
# 当合并时出现冲突
git status  # 查看冲突文件
# 手动编辑冲突文件
git add .   # 标记冲突已解决
git commit  # 完成合并
```

### 问题2：撤销错误提交
```bash
# 撤销最后一次提交但保留修改
git reset --soft HEAD~1

# 撤销最后一次提交并丢弃修改
git reset --hard HEAD~1
```

### 问题3：查看历史修改
```bash
# 查看某个文件的修改历史
git log --follow src/database.py

# 查看某次提交的详细内容
git show <commit-hash>
```

## 开发检查清单

- [ ] 在develop分支上创建功能分支
- [ ] 小步提交，每次提交都有明确的目的
- [ ] 提交信息清晰描述修改内容
- [ ] 测试代码确保功能正常
- [ ] 推送到远程仓库备份
- [ ] 合并到develop分支
- [ ] 重要版本合并到master并打标签 