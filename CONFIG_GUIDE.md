# 🛠️ 高级监听器配置指南

## 📋 快速开始

### 第1步：创建配置文件
```bash
# 创建配置文件模板
python start_listener_with_config.py --create-template

# 或者指定自定义路径
python start_listener_with_config.py --create-template -c my_config.json
```

### 第2步：修改配置文件
编辑 `config/listener_config.json`，修改你需要的参数

### 第3步：启动监听器
```bash
# 使用默认配置文件
python start_listener_with_config.py

# 使用自定义配置文件
python start_listener_with_config.py -c my_config.json
```

## ⚙️ 配置参数详解

### 🎯 监听器配置 (listener)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `target_groups` | 数组 | `["群名1", "群名2"]` | **必填**：要监听的微信群名称列表 |
| `check_interval_seconds` | 整数 | `10` | 监听间隔（秒），建议5-30秒 |
| `workflow_check_interval_minutes` | 整数 | `30` | 工作流执行间隔（分钟），建议15-60分钟 |
| `auto_workflow_enabled` | 布尔 | `true` | 是否自动执行工作流（去重、备份等） |
| `max_session_duration_hours` | 整数 | `12` | 最大运行时长（小时），到时自动停止 |
| `enable_realtime_monitoring` | 布尔 | `true` | 是否启用实时状态监控 |
| `monitoring_port` | 整数 | `8080` | 监控端口（暂未使用） |

**示例**：
```json
"listener": {
  "target_groups": [
    "NFC金融实习分享群（一）",
    "技术交流群"
  ],
  "check_interval_seconds": 15,
  "workflow_check_interval_minutes": 20,
  "auto_workflow_enabled": true,
  "max_session_duration_hours": 8,
  "enable_realtime_monitoring": true
}
```

### 🔄 工作流配置 (workflow)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `auto_dedup_enabled` | 布尔 | `true` | 是否自动去重 |
| `dedup_threshold` | 整数 | `50` | 触发去重的消息数量阈值 |
| `auto_backup_enabled` | 布尔 | `true` | 是否自动备份数据库 |
| `validation_enabled` | 布尔 | `true` | 是否自动数据验证 |
| `max_dedup_failures` | 整数 | `3` | 最大去重失败次数，超过会报警 |
| `dedup_interval_minutes` | 整数 | `30` | 去重间隔（分钟） |
| `health_check_interval_minutes` | 整数 | `60` | 健康检查间隔（分钟） |

**调优建议**：
- **高频监听**：`dedup_threshold: 20-30`
- **中频监听**：`dedup_threshold: 50-100`  
- **低频监听**：`dedup_threshold: 100-200`

### 💾 数据库配置 (database)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `db_path` | 字符串 | `"data/wechat_jds.db"` | 数据库文件路径 |
| `backup_path` | 字符串 | `"backups/"` | 备份文件存储目录 |
| `max_backup_files` | 整数 | `30` | 最大备份文件数，超过自动删除旧文件 |
| `auto_cleanup_enabled` | 布尔 | `true` | 是否自动清理过期备份 |

### 📝 日志配置 (logging)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `level` | 字符串 | `"INFO"` | 日志级别：DEBUG/INFO/WARNING/ERROR |
| `file_enabled` | 布尔 | `true` | 是否写入日志文件 |
| `console_enabled` | 布尔 | `true` | 是否控制台输出 |
| `max_log_files` | 整数 | `7` | 最大日志文件数 |
| `log_file_path` | 字符串 | `"logs/wechat_listener.log"` | 日志文件路径 |

### 🔒 安全配置 (security)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `enable_data_encryption` | 布尔 | `false` | 数据加密（暂未实现） |
| `backup_compression` | 布尔 | `true` | 备份文件压缩，节省空间 |
| `data_retention_days` | 整数 | `365` | 数据保留天数 |

### ⚡ 性能配置 (performance)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `message_buffer_size` | 整数 | `20` | 消息缓冲区大小，满了自动保存 |
| `batch_processing_size` | 整数 | `500` | 批处理大小 |
| `max_memory_usage_mb` | 整数 | `512` | 最大内存使用（MB，暂未实现） |
| `enable_performance_monitoring` | 布尔 | `true` | 是否启用性能监控 |

## 🎯 常用配置场景

### 场景1：高频监听（金融群、IT群）
```json
{
  "listener": {
    "check_interval_seconds": 5,
    "workflow_check_interval_minutes": 15
  },
  "workflow": {
    "dedup_threshold": 30
  },
  "performance": {
    "message_buffer_size": 50
  }
}
```

### 场景2：中频监听（学习群、交流群）
```json
{
  "listener": {
    "check_interval_seconds": 10,
    "workflow_check_interval_minutes": 30
  },
  "workflow": {
    "dedup_threshold": 50
  },
  "performance": {
    "message_buffer_size": 20
  }
}
```

### 场景3：低频监听（通知群、公告群）
```json
{
  "listener": {
    "check_interval_seconds": 30,
    "workflow_check_interval_minutes": 60
  },
  "workflow": {
    "dedup_threshold": 100
  },
  "performance": {
    "message_buffer_size": 10
  }
}
```

### 场景4：测试环境
```json
{
  "listener": {
    "check_interval_seconds": 5,
    "max_session_duration_hours": 1
  },
  "workflow": {
    "dedup_threshold": 5
  },
  "logging": {
    "level": "DEBUG"
  }
}
```

## 🚀 使用技巧

### 1. 批量修改群名称
```bash
# 1. 获取你的微信群列表
# 在微信中查看群聊名称，准确复制

# 2. 修改配置文件
"target_groups": [
  "你的群名称1",
  "你的群名称2",
  "你的群名称3"
]
```

### 2. 性能调优
```bash
# 高性能配置（适合服务器）
"performance": {
  "message_buffer_size": 100,
  "batch_processing_size": 1000
}

# 低资源配置（适合个人电脑）
"performance": {
  "message_buffer_size": 10,
  "batch_processing_size": 200
}
```

### 3. 调试模式
```bash
# 开启详细日志
"logging": {
  "level": "DEBUG",
  "console_enabled": true
}

# 快速测试
"listener": {
  "check_interval_seconds": 3,
  "max_session_duration_hours": 0.1
}
```

## ❗ 常见问题

### Q1: 找不到微信群怎么办？
**A**: 确保群名称完全一致，包括标点符号和空格

### Q2: 监听器启动失败？
**A**: 检查配置文件格式，确保JSON语法正确

### Q3: 内存占用过高？
**A**: 降低 `message_buffer_size` 和 `batch_processing_size`

### Q4: 消息丢失？
**A**: 检查 `auto_backup_enabled` 是否为 `true`

### Q5: 去重效果不好？
**A**: 调整 `dedup_threshold`，数值越小去重越频繁

## 🔧 高级技巧

### 多配置文件管理
```bash
# 工作配置
python start_listener_with_config.py -c config/work.json

# 个人配置  
python start_listener_with_config.py -c config/personal.json

# 测试配置
python start_listener_with_config.py -c config/test.json
```

### 定时任务设置
```bash
# Windows定时任务
# 添加到任务计划程序，每天定时启动

# Linux/Mac定时任务
# 添加到crontab，自动重启
0 8 * * * cd /path/to/wechat_listener && python start_listener_with_config.py
```

现在你拥有了完全可配置的高级监听器！🎉 