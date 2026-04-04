import os
import sys
from pathlib import Path

print("=== 详细诊断测试 ===")
print(f"Python版本: {sys.version}")
print(f"当前工作目录: {os.getcwd()}")

# 检查DASHSCOPE_API_KEY
print("\n=== API密钥检查 ===")
dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
if dashscope_key:
    print(f"[OK] DASHSCOPE_API_KEY 已配置 (长度: {len(dashscope_key)})")
else:
    print("[FAIL] DASHSCOPE_API_KEY 未配置")

# 尝试导入依赖
print("\n=== 依赖导入测试 ===")
try:
    from langchain_community.embeddings import DashScopeEmbeddings
    print("[OK] DashScopeEmbeddings 导入成功")
except Exception as e:
    print(f"[FAIL] DashScopeEmbeddings 导入失败: {e}")

# 尝试初始化DashScopeEmbeddings
print("\n=== 初始化DashScopeEmbeddings测试 ===")
try:
    if dashscope_key:
        embeddings = DashScopeEmbeddings(model="text-embedding-v2")
        print("[OK] DashScopeEmbeddings 初始化成功")
        
        # 测试嵌入功能
        test_text = "测试嵌入"
        try:
            embedding = embeddings.embed_query(test_text)
            print(f"[OK] 嵌入测试成功，向量长度: {len(embedding)}")
        except Exception as e:
            print(f"[FAIL] 嵌入测试失败: {e}")
    else:
        print("[SKIP] 未配置API密钥，跳过初始化测试")
except Exception as e:
    print(f"[FAIL] DashScopeEmbeddings 初始化失败: {e}")
    import traceback
    traceback.print_exc()

# 尝试导入MultiKBSystem
print("\n=== MultiKBSystem导入测试 ===")
try:
    from rag_backend import MultiKBSystem
    print("[OK] MultiKBSystem 导入成功")
    
    # 尝试初始化
    print("\n=== MultiKBSystem初始化测试 ===")
    try:
        system = MultiKBSystem(storage_path="./medical_kb")
        print("[OK] MultiKBSystem 初始化成功")
        print(f"   知识库数量: {len(system.kb_info)}")
    except Exception as e:
        print(f"[FAIL] MultiKBSystem 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"[FAIL] MultiKBSystem 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 诊断完成 ===")