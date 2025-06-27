# 微信监听器测试框架设计文档

## 📋 测试策略概览

### 测试目标
1. **功能正确性**：确保所有功能按预期工作
2. **数据安全性**：验证数据不会丢失或损坏
3. **性能稳定性**：确保新架构性能符合要求
4. **可靠性验证**：验证错误恢复和异常处理机制

### 测试金字塔
```
                    E2E测试 (5%)
                /                \
           集成测试 (20%)
        /                        \
   单元测试 (75%)
```

## 🧪 测试框架架构

### 1. 测试目录结构
```
tests/
├── unit/                    # 单元测试
│   ├── test_database.py     # 数据库操作测试
│   ├── test_deduplicator.py # 去重逻辑测试
│   ├── test_backup_manager.py # 备份管理测试
│   └── test_validators.py   # 数据验证测试
├── integration/             # 集成测试
│   ├── test_workflow.py     # 完整工作流测试
│   ├── test_migration.py    # 数据迁移测试
│   └── test_compatibility.py # 向后兼容测试
├── performance/             # 性能测试
│   ├── test_benchmark.py    # 基准性能测试
│   ├── test_memory.py       # 内存使用测试
│   └── test_concurrent.py   # 并发性能测试
├── stress/                  # 压力测试
│   ├── test_large_data.py   # 大数据量测试
│   ├── test_long_running.py # 长时间运行测试
│   └── test_failure_scenarios.py # 故障场景测试
├── fixtures/                # 测试数据
│   ├── sample_messages.json
│   ├── duplicate_data.json
│   └── edge_cases.json
├── utils/                   # 测试工具
│   ├── test_data_generator.py
│   ├── database_helper.py
│   └── assertion_helpers.py
└── conftest.py             # pytest配置
```

## 🔧 测试工具和依赖

### 核心测试库
```python
# requirements-test.txt
pytest>=7.0.0              # 测试框架
pytest-cov>=4.0.0          # 代码覆盖率
pytest-benchmark>=4.0.0    # 性能基准测试
pytest-mock>=3.10.0        # Mock功能
pytest-xdist>=3.0.0        # 并行测试
pytest-html>=3.1.0         # HTML测试报告
pytest-timeout>=2.1.0      # 超时控制
memory-profiler>=0.60.0    # 内存分析
psutil>=5.9.0              # 系统资源监控
faker>=18.0.0              # 测试数据生成
```

### 测试配置
```python
# conftest.py
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
import sqlite3

@pytest.fixture(scope="function")
def temp_database():
    """创建临时测试数据库"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_wechat.db"
    
    # 创建测试数据库
    conn = sqlite3.connect(str(db_path))
    # 初始化表结构
    setup_test_database(conn)
    conn.close()
    
    yield db_path
    
    # 清理
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="function")
def sample_messages():
    """提供测试消息数据"""
    return [
        {
            "group_name": "测试群1",
            "sender": "用户A",
            "content": "这是一条测试消息",
            "msg_type": "Text"
        },
        # 更多测试数据...
    ]

@pytest.fixture(scope="session")
def performance_baseline():
    """性能基准数据"""
    return {
        "dedup_time_per_1000_messages": 2.0,  # 秒
        "memory_usage_mb": 50,
        "database_growth_factor": 1.3
    }
```

## 📝 单元测试详细设计

### 1. 数据库操作测试 (test_database.py)
```python
class TestDatabaseOperations:
    """数据库基础操作测试"""
    
    def test_save_raw_message(self, temp_database):
        """测试保存原始消息"""
        # 测试正常保存
        # 测试重复保存
        # 测试异常数据处理
        
    def test_batch_insert_performance(self, temp_database):
        """测试批量插入性能"""
        # 测试1000条消息批量插入时间
        
    def test_database_constraints(self, temp_database):
        """测试数据库约束"""
        # 测试外键约束
        # 测试唯一性约束
        # 测试NOT NULL约束
        
    def test_transaction_rollback(self, temp_database):
        """测试事务回滚"""
        # 模拟操作失败场景
        # 验证数据完整性
```

### 2. 去重逻辑测试 (test_deduplicator.py)
```python
class TestDeduplicationLogic:
    """去重逻辑测试"""
    
    def test_duplicate_detection(self):
        """测试重复检测准确性"""
        # 完全相同的消息
        # 部分相同的消息
        # 时间戳不同但内容相同
        
    def test_dedup_hash_generation(self):
        """测试去重哈希生成"""
        # 相同内容生成相同哈希
        # 不同内容生成不同哈希
        
    def test_edge_cases(self):
        """测试边界情况"""
        # 空消息内容
        # 超长消息内容
        # 特殊字符消息
        
    def test_dedup_performance(self):
        """测试去重性能"""
        # 1万条消息去重时间测试
```

### 3. 备份管理测试 (test_backup_manager.py)
```python
class TestBackupManager:
    """备份管理器测试"""
    
    def test_create_backup(self, temp_database):
        """测试创建备份"""
        # 测试自动备份
        # 测试手动备份
        # 测试备份文件完整性
        
    def test_restore_backup(self, temp_database):
        """测试恢复备份"""
        # 测试完整恢复
        # 测试部分恢复
        # 测试损坏备份处理
        
    def test_backup_metadata(self, temp_database):
        """测试备份元数据"""
        # 验证元数据记录准确性
        # 测试备份过期清理
        
    def test_checksum_validation(self):
        """测试校验和验证"""
        # 正常文件校验
        # 损坏文件检测
```

## 🔗 集成测试详细设计

### 1. 完整工作流测试 (test_workflow.py)
```python
class TestCompleteWorkflow:
    """完整工作流集成测试"""
    
    def test_listen_to_clean_workflow(self, temp_database):
        """测试从监听到清洁数据的完整流程"""
        # 1. 模拟微信消息接收
        # 2. 保存到raw表
        # 3. 执行去重处理
        # 4. 验证clean表数据
        # 5. 检查处理日志
        
    def test_error_recovery_workflow(self, temp_database):
        """测试错误恢复工作流"""
        # 模拟各种错误场景
        # 验证自动恢复机制
        
    def test_concurrent_processing(self):
        """测试并发处理"""
        # 多个进程同时处理不同批次
        # 验证数据一致性
```

### 2. 数据迁移测试 (test_migration.py)
```python
class TestDataMigration:
    """数据迁移测试"""
    
    def test_legacy_to_new_migration(self):
        """测试从旧架构到新架构的迁移"""
        # 创建旧格式数据
        # 执行迁移脚本
        # 验证数据完整性
        
    def test_migration_rollback(self):
        """测试迁移回滚"""
        # 迁移过程中断
        # 执行回滚操作
        # 验证数据恢复
```

## ⚡ 性能测试详细设计

### 1. 基准性能测试 (test_benchmark.py)
```python
class TestBenchmark:
    """性能基准测试"""
    
    def test_dedup_performance_baseline(self, benchmark):
        """去重性能基准测试"""
        # 使用pytest-benchmark测试去重性能
        # 设定性能基准和阈值
        
    def test_database_query_performance(self, benchmark):
        """数据库查询性能测试"""
        # 测试各种查询场景的性能
        
    def test_memory_usage_benchmark(self):
        """内存使用基准测试"""
        # 使用memory-profiler监控内存使用
```

### 2. 压力测试 (test_stress.py)
```python
class TestStressScenarios:
    """压力测试场景"""
    
    def test_large_dataset_processing(self):
        """大数据集处理测试"""
        # 生成10万条测试消息
        # 测试处理时间和内存使用
        
    def test_long_running_stability(self):
        """长时间运行稳定性测试"""
        # 连续运行24小时
        # 监控内存泄漏和性能退化
        
    def test_failure_recovery_stress(self):
        """故障恢复压力测试"""
        # 模拟各种故障场景
        # 测试系统恢复能力
```

## 📊 数据完整性测试

### 1. 数据一致性验证
```python
class TestDataIntegrity:
    """数据完整性测试"""
    
    def test_no_data_loss(self):
        """验证无数据丢失"""
        # 比较处理前后的数据总量
        # 验证每条原始数据都有对应的处理结果
        
    def test_dedup_accuracy(self):
        """验证去重准确性"""
        # 人工标注的重复数据集
        # 对比自动去重结果
        
    def test_foreign_key_consistency(self):
        """验证外键一致性"""
        # 检查所有外键引用的完整性
```

## 🎯 测试自动化和CI/CD

### 1. 测试执行脚本
```python
# run_tests.py
import subprocess
import sys
from pathlib import Path

def run_test_suite():
    """运行完整测试套件"""
    
    # 单元测试
    print("运行单元测试...")
    result = subprocess.run([
        "pytest", "tests/unit/", 
        "--cov=src", 
        "--cov-report=html",
        "-v"
    ])
    
    # 集成测试
    print("运行集成测试...")
    subprocess.run([
        "pytest", "tests/integration/", 
        "-v"
    ])
    
    # 性能测试
    print("运行性能测试...")
    subprocess.run([
        "pytest", "tests/performance/", 
        "--benchmark-only",
        "--benchmark-html=reports/benchmark.html"
    ])

if __name__ == "__main__":
    run_test_suite()
```

### 2. 持续集成配置
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.9
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
        
    - name: Run unit tests
      run: pytest tests/unit/ --cov=src
      
    - name: Run integration tests
      run: pytest tests/integration/
      
    - name: Run performance tests
      run: pytest tests/performance/ --benchmark-only
```

## 📈 测试报告和监控

### 1. 测试报告格式
- **HTML报告**：包含详细的测试结果和代码覆盖率
- **性能报告**：基准测试结果和趋势图
- **失败分析报告**：失败用例的详细分析

### 2. 质量门禁标准
- 代码覆盖率 ≥ 90%
- 所有单元测试通过率 100%
- 集成测试通过率 ≥ 95%
- 性能回归 ≤ 10%
- 无严重内存泄漏

## 🔄 测试数据管理

### 1. 测试数据生成器
```python
# test_data_generator.py
class TestDataGenerator:
    """测试数据生成器"""
    
    def generate_duplicate_messages(self, count):
        """生成包含重复的测试消息"""
        # 生成指定数量的消息，包含预定比例的重复
        
    def generate_edge_case_messages(self):
        """生成边界情况测试数据"""
        # 空消息、超长消息、特殊字符等
        
    def generate_performance_dataset(self, size):
        """生成性能测试数据集"""
        # 生成指定大小的数据集用于性能测试
```

通过这个全面的测试框架，我们可以确保新架构的：
- ✅ **功能正确性**：所有功能按预期工作
- ✅ **数据安全性**：原始数据永不丢失
- ✅ **性能稳定性**：性能符合或超过预期
- ✅ **可靠性**：错误处理和恢复机制可靠

这个测试框架将在后续的实施阶段中逐步实现和完善。您对这个测试框架设计有什么意见或建议吗？ 