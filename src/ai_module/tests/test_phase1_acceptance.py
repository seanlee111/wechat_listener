"""
Phase 1 验收测试
验证基础架构搭建是否完成并正常工作
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import traceback

# 添加项目路径到sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        # 测试AI模块核心导入
        from src.ai_module import AIDatabase, AIConfig, MessageSchema, JDSchema
        from src.ai_module.database.ai_database import get_ai_database
        from src.ai_module.config.ai_config import create_default_config
        
        print("✅ 所有核心模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def test_database_creation():
    """测试数据库创建"""
    print("\n🗄️ 测试数据库创建...")
    
    try:
        from src.ai_module.database.ai_database import get_ai_database
        # 创建AI数据库实例
        ai_db = get_ai_database()
        
        # 创建AI表结构
        success = ai_db.setup_ai_tables()
        
        if success:
            print("✅ AI数据库表创建成功")
            
            # 测试基础查询
            summary = ai_db.get_processing_summary()
            print(f"✅ 数据库查询测试成功: {summary}")
            
            ai_db.close()
            return True
        else:
            print("❌ AI数据库表创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 数据库创建测试失败: {e}")
        traceback.print_exc()
        return False

def test_data_models():
    """测试数据模型"""
    print("\n📋 测试数据模型...")
    
    try:
        from src.ai_module.models.schemas.message_schema import MessageSchema, MessageType
        from src.ai_module.models.schemas.jd_schema import JDSchema, ExtractionResult, WorkType
        
        # 测试消息模型
        message = MessageSchema(
            id=1,
            group_name="测试群",
            sender="测试用户",
            content="阿里巴巴招聘Java工程师，薪资20-30K，联系邮箱hr@alibaba.com",
            msg_type=MessageType.TEXT,
            timestamp=datetime.now().isoformat()
        )
        
        assert message.is_potential_jd() == True, "JD检测失败"
        print("✅ 消息模型验证成功")
        
        # 测试JD模型
        jd = JDSchema(
            company_name="阿里巴巴",
            position_title="Java工程师",
            work_location="杭州",
            salary_range="20-30K",
            contact_email="hr@alibaba.com",
            work_type=WorkType.FULL_TIME
        )
        
        assert jd.is_complete() == True, "JD完整性检查失败"
        assert jd.has_contact_info() == True, "联系方式检查失败"
        print("✅ JD模型验证成功")
        
        # 测试提取结果模型
        extraction_result = ExtractionResult(
            message_id=1,
            extraction_method="test",
            model_version="test-v1",
            is_job_posting=True,
            jd_detection_confidence=0.9,
            confidence_score=0.85,
            jd_info=jd
        )
        
        assert extraction_result.is_successful() == True, "提取结果验证失败"
        assert extraction_result.is_high_quality(0.8) == True, "高质量检查失败"
        print("✅ 提取结果模型验证成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据模型测试失败: {e}")
        traceback.print_exc()
        return False

def test_configuration():
    """测试配置管理"""
    print("\n⚙️ 测试配置管理...")
    
    try:
        from src.ai_module.config.ai_config import AIConfig, create_default_config, ProviderConfig, ProviderType
        
        # 创建默认配置
        config = create_default_config()
        
        # 验证配置
        errors = config.validate()
        if errors:
            print(f"⚠️ 配置验证警告: {errors}")
        else:
            print("✅ 配置验证通过")
        
        # 测试配置功能
        default_provider = config.get_default_provider()
        if default_provider:
            print(f"✅ 默认提供商: {default_provider.name}")
        
        available_providers = config.get_available_providers()
        print(f"✅ 可用提供商数量: {len(available_providers)}")
        
        # 测试配置序列化
        config_dict = config.to_dict()
        new_config = AIConfig.from_dict(config_dict)
        assert new_config.default_provider == config.default_provider, "配置序列化失败"
        print("✅ 配置序列化测试成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置管理测试失败: {e}")
        traceback.print_exc()
        return False

def test_database_operations():
    """测试数据库操作"""
    print("\n💾 测试数据库操作...")
    
    try:
        from src.ai_module.database.ai_database import get_ai_database
        from src.ai_module.models.schemas.jd_schema import ExtractionResult, JDSchema, WorkType
        
        ai_db = get_ai_database()
        
        # 测试批次创建
        batch_id = f"test_batch_{int(datetime.now().timestamp())}"
        batch_pk = ai_db.create_processing_batch(batch_id, 10, {"test": True})
        print(f"✅ 批次创建成功: {batch_pk}")
        
        # 测试提取结果保存
        test_jd = JDSchema(
            company_name="测试公司",
            position_title="测试职位",
            work_type=WorkType.FULL_TIME
        )
        
        extraction_result = ExtractionResult(
            message_id=999,  # 测试ID
            extraction_method="test",
            model_version="test-v1",
            is_job_posting=True,
            jd_detection_confidence=0.9,
            confidence_score=0.85,
            jd_info=test_jd
        )
        
        # 转换为数据库格式并保存
        result_data = extraction_result.to_database_dict()
        result_data["processing_batch_id"] = batch_id
        
        result_pk = ai_db.save_extraction_result(result_data)
        print(f"✅ 提取结果保存成功: {result_pk}")
        
        # 测试状态查询
        is_processed = ai_db.is_message_processed(999)
        print(f"✅ 消息处理状态查询: {is_processed}")
        
        # 更新批次状态
        ai_db.update_processing_batch(batch_id, {
            "status": "completed",
            "processed_messages": 1,
            "successful_extractions": 1,
            "jd_found_count": 1
        })
        print("✅ 批次状态更新成功")
        
        ai_db.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库操作测试失败: {e}")
        traceback.print_exc()
        return False

def run_phase1_acceptance_tests():
    """运行Phase 1验收测试"""
    print("🚀 开始Phase 1验收测试")
    print("=" * 50)
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("模块导入", test_imports),
        ("数据库创建", test_database_creation),
        ("数据模型", test_data_models),
        ("配置管理", test_configuration),
        ("数据库操作", test_database_operations)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            test_results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("📊 Phase 1验收测试结果汇总")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<15} : {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 Phase 1验收测试全部通过！")
        print("✅ 基础架构搭建完成，可以进入Phase 2开发")
        return True
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，需要修复后才能进入下一阶段")
        return False

if __name__ == "__main__":
    success = run_phase1_acceptance_tests()
    sys.exit(0 if success else 1) 