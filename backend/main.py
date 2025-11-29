from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
import hashlib
from datetime import datetime

# 创建 FastAPI 应用实例
app = FastAPI(title="Web-Retrace API", version="2.0.0")

# 配置 CORS - 允许 Chrome 扩展跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 ChromaDB 客户端和集合
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="web_pages",
    metadata={"description": "Stores web page content for RAG retrieval"}
)

# 定义请求模型
class ChatRequest(BaseModel):
    message: str

class MemorizeRequest(BaseModel):
    title: str
    content: str

# 定义响应模型
class ChatResponse(BaseModel):
    response: str
    status: str

class MemorizeResponse(BaseModel):
    status: str
    doc_id: str
    title: str
    message: str

@app.get("/")
async def root():
    """根路径 - 健康检查"""
    # 获取集合统计信息
    count = collection.count()
    return {
        "message": "Web-Retrace API 正在运行",
        "version": "2.0.0",
        "stored_pages": count
    }

@app.post("/memorize", response_model=MemorizeResponse)
async def memorize(request: MemorizeRequest):
    """
    记忆端点 - 存储网页内容到向量数据库
    
    Args:
        request: 包含页面标题和内容的请求体
    
    Returns:
        包含存储状态和文档ID的响应体
    """
    try:
        # 生成唯一文档ID（使用标题+时间戳的哈希）
        timestamp = datetime.now().isoformat()
        doc_id = hashlib.md5(f"{request.title}{timestamp}".encode()).hexdigest()
        
        # 存储到 ChromaDB
        collection.add(
            documents=[request.content],
            metadatas=[{
                "title": request.title,
                "timestamp": timestamp
            }],
            ids=[doc_id]
        )
        
        return MemorizeResponse(
            status="success",
            doc_id=doc_id,
            title=request.title,
            message=f"成功存储页面: {request.title}"
        )
    
    except Exception as e:
        return MemorizeResponse(
            status="error",
            doc_id="",
            title=request.title,
            message=f"存储失败: {str(e)}"
        )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天端点 - 接收消息并返回响应（带RAG增强）
    
    Args:
        request: 包含用户消息的请求体
    
    Returns:
        包含响应消息和状态的响应体
    """
    try:
        # 检查数据库中是否有内容
        count = collection.count()
        
        if count == 0:
            # 数据库为空，返回简单响应
            response_text = f"收到您的消息：{request.message}\n\n💡 提示：目前还没有记忆任何页面。点击「Memorize This Page」按钮来保存页面内容。"
        else:
            # 使用RAG检索相关内容
            results = collection.query(
                query_texts=[request.message],
                n_results=min(3, count)  # 最多返回3个相关结果
            )
            
            # 构建响应
            if results and results['documents'] and len(results['documents'][0]) > 0:
                response_text = f"根据您的问题「{request.message}」，我找到了以下相关内容：\n\n"
                
                for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
                    title = metadata.get('title', '未知标题')
                    # 截取内容前200个字符作为摘要
                    snippet = doc[:200] + "..." if len(doc) > 200 else doc
                    response_text += f"📄 {i}. {title}\n{snippet}\n\n"
            else:
                response_text = f"收到您的消息：{request.message}\n\n未找到相关的页面内容。"
        
        return ChatResponse(
            response=response_text,
            status="success"
        )
    
    except Exception as e:
        return ChatResponse(
            response=f"处理消息时出错: {str(e)}",
            status="error"
        )

if __name__ == "__main__":
    import uvicorn
    # 启动服务器
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
