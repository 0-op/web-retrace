"""
ChromaDB 集成验证脚本
验证后端的记忆功能和RAG检索功能
"""
import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_root():
    """测试根端点 - 检查API状态"""
    print("=" * 50)
    print("测试 1: API 健康检查")
    print("=" * 50)
    
    response = requests.get(f"{API_BASE_URL}/")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_memorize():
    """测试记忆端点 - 存储页面内容"""
    print("=" * 50)
    print("测试 2: 记忆页面内容")
    print("=" * 50)
    
    # 测试数据 - 模拟维基百科AI页面
    test_data = {
        "title": "Artificial Intelligence - Wikipedia",
        "content": """Artificial intelligence (AI) is intelligence demonstrated by machines, 
        as opposed to natural intelligence displayed by animals including humans. 
        AI research has been defined as the field of study of intelligent agents, 
        which refers to any system that perceives its environment and takes actions 
        that maximize its chance of achieving its goals. The term artificial intelligence 
        is often used to describe machines that mimic cognitive functions that humans 
        associate with the human mind, such as learning and problem solving."""
    }
    
    response = requests.post(
        f"{API_BASE_URL}/memorize",
        json=test_data
    )
    
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    print()
    return result

def test_memorize_multiple():
    """测试存储多个页面"""
    print("=" * 50)
    print("测试 3: 记忆多个页面")
    print("=" * 50)
    
    pages = [
        {
            "title": "Machine Learning - Wikipedia",
            "content": """Machine learning is a subset of artificial intelligence that 
            focuses on the use of data and algorithms to imitate the way that humans learn, 
            gradually improving its accuracy. Machine learning is an important component 
            of the growing field of data science."""
        },
        {
            "title": "Neural Networks - Wikipedia",
            "content": """A neural network is a series of algorithms that endeavors to recognize 
            underlying relationships in a set of data through a process that mimics the way 
            the human brain operates. In this sense, neural networks refer to systems of neurons, 
            either organic or artificial in nature."""
        }
    ]
    
    for i, page in enumerate(pages, 1):
        response = requests.post(f"{API_BASE_URL}/memorize", json=page)
        result = response.json()
        print(f"页面 {i}: {result['title']}")
        print(f"  状态: {result['status']}")
        print(f"  文档ID: {result['doc_id']}")
        print()

def test_chat_rag():
    """测试RAG增强的聊天"""
    print("=" * 50)
    print("测试 4: RAG 聊天检索")
    print("=" * 50)
    
    queries = [
        "What is artificial intelligence?",
        "Tell me about machine learning",
        "How do neural networks work?"
    ]
    
    for query in queries:
        print(f"\n问题: {query}")
        print("-" * 40)
        
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={"message": query}
        )
        
        result = response.json()
        print(f"回答:\n{result['response']}")
        print()

def main():
    print("\n🧪 ChromaDB RAG 功能验证测试\n")
    
    try:
        # 测试 1: API 健康检查
        test_root()
        
        # 测试 2: 记忆单个页面
        test_memorize()
        
        # 测试 3: 记忆多个页面
        test_memorize_multiple()
        
        # 测试 4: RAG 检索测试
        test_chat_rag()
        
        # 最终状态检查
        print("=" * 50)
        print("最终状态检查")
        print("=" * 50)
        response = requests.get(f"{API_BASE_URL}/")
        print(f"总共存储的页面数: {response.json()['stored_pages']}")
        
        print("\n✅ 所有测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 错误: 无法连接到后端服务")
        print("   请确保后端服务正在运行: python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

if __name__ == "__main__":
    main()
