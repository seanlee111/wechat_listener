# 微信群聊监听与JD信息提取系统 v2.0

## 项目简介

这是一个自动化的微信群聊监听系统，能够：
- 监听指定微信群聊的新消息
- 自动提取招聘信息（JD）
- 生成结构化的Excel报告
- 支持数据库存储和查询

## 功能模块

### 1. 消息监听 (`wechat_listener.py`)
- 监听指定微信群聊的新消息
- 支持ESC键安全停止
- 随机延时模拟人工操作
- 自动过滤系统消息

### 2. 数据库管理 (`database.py`)
- SQLite数据库存储
- 消息和JD信息分离存储
- 支持数据库结构自动迁移
- 索引优化查询性能

### 3. JD信息提取 (`jd_extractor.py`)
- 基于正则表达式的信息提取
- 支持公司、职位、地点、邮箱等字段
- 可重新处理历史消息
- 灵活的匹配模式配置

### 4. 报告生成 (`report_generator.py`)
- 生成Excel格式的JD汇总报告
- 包含原始消息和提取信息
- 时间戳命名避免覆盖

## 快速开始

### 环境准备
```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 初始化数据库
.\initialize_database.bat
```

### 基本使用流程
1. **启动监听**：`.\start.bat`
2. **处理JD信息**：`.\process_jds.bat`
3. **生成报告**：`.\generate_report.bat`
4. **查看数据库**：`.\view_db.bat`

## 配置说明

### 监听群聊配置
在 `src/wechat_listener.py` 中修改 `GROUP_NAMES` 列表：
```python
GROUP_NAMES = [
    "NFC金融实习分享群（一）",
    "NJU后浪-优质实习交流群"
]
```

### 提取规则配置
在 `src/jd_extractor.py` 中修改 `EXTRACTION_PATTERNS` 字典来调整信息提取规则。

## 文件结构
```
version2.0/
├── src/                    # 源代码
│   ├── wechat_listener.py  # 消息监听
│   ├── database.py         # 数据库操作
│   ├── jd_extractor.py     # JD信息提取
│   ├── report_generator.py # 报告生成
│   └── ...
├── data/                   # 数据库文件
├── reports/                # 生成的报告
├── venv/                   # 虚拟环境
└── *.bat                   # 批处理脚本
```

## 版本历史

### v2.0 (当前版本)
- 重构数据库结构
- 优化JD提取算法
- 改进报告生成功能
- 增强错误处理

## 注意事项

1. **数据安全**：数据库文件包含敏感信息，已加入.gitignore
2. **微信登录**：使用前请确保微信已登录
3. **权限要求**：需要微信窗口保持在前台
4. **停止操作**：按ESC键可安全停止监听

## 开发计划

- [ ] 支持更多消息格式
- [ ] 添加邮件自动发送功能
- [ ] 优化提取准确率
- [ ] 添加Web界面 