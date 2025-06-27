# 微信监听器安全去重架构设计文档 v2.1

## 📋 目标与原则

### 核心目标
- **数据安全第一**：确保原始数据永不丢失
- **操作可逆性**：所有操作都可以回滚
- **性能优化**：增量处理，避免全表扫描
- **向后兼容**：保持现有API接口不变

### 设计原则
1. **分层存储**：原始数据 → 处理缓存 → 清洁数据
2. **事务保护**：关键操作使用事务确保原子性
3. **状态跟踪**：记录每条数据的处理状态
4. **备份优先**：操作前自动备份

## 🏗️ 新架构设计

### 数据流架构图
```
微信监听器 → messages_raw (原始数据，永不删除)
                ↓
           数据处理器 (读取未处理数据)
                ↓
        messages_staging (临时处理表)
                ↓
           去重验证器 (安全去重逻辑)
                ↓
         messages_clean (清洁数据表)
                ↓
           JD提取器 → jobs (招聘信息)
                ↓
           报告生成器
```

### 核心表结构设计

#### 1. messages_raw (原始数据表)
```sql
CREATE TABLE messages_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    msg_type TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 捕获时间
    processed_status INTEGER DEFAULT 0,               -- 0:未处理 1:已处理 2:处理失败
    processing_attempts INTEGER DEFAULT 0,            -- 处理尝试次数
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. messages_staging (处理缓存表)
```sql
CREATE TABLE messages_staging (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_message_id INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    msg_type TEXT,
    timestamp DATETIME,
    dedup_hash TEXT,                                   -- 去重哈希值
    processing_batch_id TEXT,                          -- 处理批次ID
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (raw_message_id) REFERENCES messages_raw(id)
);
```

#### 3. messages_clean (清洁数据表)
```sql
CREATE TABLE messages_clean (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_message_id INTEGER NOT NULL,
    staging_message_id INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    msg_type TEXT,
    timestamp DATETIME,
    dedup_hash TEXT,
    processed_batch_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_name, sender, content),               -- 唯一性约束
    FOREIGN KEY (raw_message_id) REFERENCES messages_raw(id),
    FOREIGN KEY (staging_message_id) REFERENCES messages_staging(id)
);
```

#### 4. processing_logs (处理日志表)
```sql
CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    operation_type TEXT NOT NULL,                      -- 'dedup', 'backup', 'migrate'
    status TEXT NOT NULL,                              -- 'started', 'completed', 'failed'
    records_processed INTEGER DEFAULT 0,
    records_affected INTEGER DEFAULT 0,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. backup_metadata (备份元数据表)
```sql
CREATE TABLE backup_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_file_path TEXT NOT NULL,
    backup_type TEXT NOT NULL,                         -- 'auto', 'manual', 'pre-operation'
    source_tables TEXT NOT NULL,                       -- JSON格式的表名列表
    record_count INTEGER,
    file_size_bytes INTEGER,
    checksum TEXT,                                      -- 文件校验和
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expiry_date DATETIME                               -- 备份过期时间
);
```

### 安全处理流程

#### 去重处理工作流
```python
def safe_deduplication_workflow():
    """安全去重工作流程"""
    batch_id = generate_batch_id()
    
    try:
        # 第1步：创建处理批次日志
        log_batch_start(batch_id, 'dedup')
        
        # 第2步：自动备份当前状态
        backup_file = create_automatic_backup(batch_id)
        
        # 第3步：读取未处理的原始数据
        unprocessed_messages = get_unprocessed_raw_messages()
        
        # 第4步：将数据复制到staging表
        copy_to_staging_table(unprocessed_messages, batch_id)
        
        # 第5步：在staging表中执行去重逻辑
        dedup_results = deduplicate_in_staging(batch_id)
        
        # 第6步：验证去重结果
        if validate_dedup_results(dedup_results):
            # 第7步：将清洁数据移动到clean表
            move_to_clean_table(batch_id)
            
            # 第8步：标记原始数据为已处理
            mark_raw_messages_processed(batch_id)
            
            # 第9步：清理staging表
            cleanup_staging_table(batch_id)
            
            # 第10步：记录成功日志
            log_batch_success(batch_id, dedup_results)
            
        else:
            # 回滚操作
            rollback_dedup_operation(batch_id, backup_file)
            
    except Exception as e:
        # 异常处理和回滚
        handle_dedup_exception(batch_id, e, backup_file)
```

## 🔒 安全特性

### 1. 数据保护机制
- **原始数据不变性**：messages_raw表只插入，从不删除
- **多层备份**：操作前自动备份，支持手动备份
- **事务保护**：关键操作使用数据库事务
- **校验和验证**：备份文件包含校验和

### 2. 错误恢复机制
- **自动回滚**：操作失败时自动恢复到操作前状态
- **重试机制**：失败操作支持重试，带指数退避
- **状态跟踪**：详细记录每个操作的状态
- **错误隔离**：单条记录错误不影响批次处理

### 3. 性能优化
- **增量处理**：只处理新增的未处理数据
- **批量操作**：支持批量插入和更新
- **索引优化**：关键字段添加适当索引
- **分页处理**：大数据量时分页处理避免内存溢出

## 📊 向后兼容性

### API兼容性保证
```python
# 现有的API接口保持不变
def save_message(group_name, sender, content, msg_type):
    """向后兼容的消息保存接口"""
    # 内部调用新的save_raw_message函数
    return save_raw_message(group_name, sender, content, msg_type)

# 现有的查询接口通过视图实现兼容
CREATE VIEW messages AS 
SELECT id, group_name, sender, content, msg_type, timestamp
FROM messages_clean;
```

### 数据迁移策略
1. **渐进式迁移**：现有数据逐步迁移到新架构
2. **双写模式**：迁移期间同时写入新旧表
3. **回退方案**：如需回退，可恢复到原始架构

## 🧪 测试策略

### 1. 单元测试
- [ ] 数据库操作测试
- [ ] 去重逻辑测试
- [ ] 备份恢复测试
- [ ] 错误处理测试

### 2. 集成测试
- [ ] 完整工作流测试
- [ ] 并发处理测试
- [ ] 大数据量测试
- [ ] 异常场景测试

### 3. 性能测试
- [ ] 处理速度基准测试
- [ ] 内存使用测试
- [ ] 数据库性能测试
- [ ] 并发性能测试

### 4. 数据完整性测试
- [ ] 数据一致性验证
- [ ] 去重准确性测试
- [ ] 备份完整性测试
- [ ] 恢复正确性测试

## 📅 实施时间表

| 阶段 | 时间 | 主要任务 |
|------|------|----------|
| 阶段1 | 1天 | 架构设计、测试框架 |
| 阶段2 | 2天 | 数据库扩展、备份管理 |
| 阶段3 | 3天 | 安全去重器、验证机制 |
| 阶段4 | 3天 | 全面测试、性能优化 |

## 🎯 成功标准

### 功能性标准
- [ ] 所有现有功能正常运行
- [ ] 新的去重机制准确可靠
- [ ] 数据完整性100%保证
- [ ] 操作可逆性验证通过

### 性能标准
- [ ] 去重处理速度 ≥ 当前方案的80%
- [ ] 内存使用增长 ≤ 50%
- [ ] 数据库大小增长 ≤ 30%

### 可靠性标准
- [ ] 24小时连续运行无故障
- [ ] 异常恢复成功率 100%
- [ ] 备份恢复成功率 100% 