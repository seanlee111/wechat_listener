# Git 版本控制工作流程

## 分支策略

### 主分支 (master/main)
- 保持稳定可用的代码
- 只接受经过测试的合并请求
- 每次提交都应该可以正常运行

### 开发分支 (develop)
- 用于集成功能开发
- 从master分支创建
- 功能完成后合并回master

### 功能分支 (feature/*)
- 用于开发新功能
- 从develop分支创建
- 命名格式：`feature/功能名称`
- 例如：`feature/email-automation`

### 修复分支 (hotfix/*)
- 用于紧急修复
- 从master分支创建
- 修复后同时合并到master和develop
- 命名格式：`hotfix/修复描述`

## 提交规范

### 提交信息格式
```
类型(范围): 简短描述

详细描述（可选）

相关任务: #123
```

### 类型说明
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

### 示例
```
feat(extractor): 添加邮箱自动识别功能

- 支持多种邮箱格式识别
- 优化正则表达式匹配规则
- 添加邮箱验证功能

相关任务: #45
```

## 日常开发流程

### 1. 开始新功能开发
```bash
# 切换到develop分支
git checkout develop
git pull origin develop

# 创建功能分支
git checkout -b feature/new-feature

# 开发完成后提交
git add .
git commit -m "feat: 新功能描述"

# 推送到远程
git push origin feature/new-feature
```

### 2. 完成功能开发
```bash
# 确保代码已提交
git status

# 切换到develop分支
git checkout develop
git pull origin develop

# 合并功能分支
git merge feature/new-feature

# 推送到远程
git push origin develop

# 删除本地功能分支
git branch -d feature/new-feature
```

### 3. 发布版本
```bash
# 从develop合并到master
git checkout master
git merge develop

# 创建版本标签
git tag -a v2.1.0 -m "版本2.1.0发布"

# 推送到远程
git push origin master
git push origin v2.1.0
```

## 常用命令

### 查看状态
```bash
git status                    # 查看工作区状态
git log --oneline            # 查看提交历史
git branch -a                # 查看所有分支
```

### 撤销操作
```bash
git reset --soft HEAD~1      # 撤销最后一次提交，保留修改
git reset --hard HEAD~1      # 撤销最后一次提交，丢弃修改
git checkout -- filename     # 撤销文件修改
```

### 分支操作
```bash
git branch feature-name      # 创建分支
git checkout feature-name    # 切换分支
git checkout -b feature-name # 创建并切换分支
git branch -d feature-name   # 删除分支
```

## 注意事项

1. **经常提交**：小步快跑，经常提交代码
2. **清晰描述**：提交信息要清晰描述变更内容
3. **测试代码**：提交前确保代码可以正常运行
4. **及时合并**：功能完成后及时合并到主分支
5. **备份重要**：重要修改前先备份或创建分支

## 推荐工具

- **Git GUI**: SourceTree, GitKraken
- **IDE集成**: VS Code, PyCharm
- **在线平台**: GitHub, GitLab, Gitee 