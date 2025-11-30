from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
import hashlib
from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 获取 LLM 配置
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

# 初始化 LLM 客户端
llm_client = None
if LLM_API_KEY:
    llm_client = OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL
    )

# 初始化文本分块器
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)

# 创建 FastAPI 应用实例
app = FastAPI(title="Web-Retrace API", version="3.0.0")

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
    记忆端点 - 使用文本分块存储网页内容到向量数据库
    
    Args:
        request: 包含页面标题和内容的请求体
    
    Returns:
        包含存储状态和文档ID的响应体
    """
    try:
        # 生成唯一的源文档ID（使用标题+时间戳的哈希）
        timestamp = datetime.now().isoformat()
        source_id = hashlib.md5(f"{request.title}{timestamp}".encode()).hexdigest()
        
        # 使用文本分块器拆分内容
        chunks = text_splitter.split_text(request.content)
        
        # 准备批量存储数据
        chunk_ids = []
        chunk_documents = []
        chunk_metadatas = []
        
        for i, chunk in enumerate(chunks):
            # 为每个 chunk 生成唯一 ID
            chunk_id = f"{source_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            chunk_documents.append(chunk)
            
            # 为每个 chunk 添加完整的元数据
            chunk_metadatas.append({
                "title": request.title,
                "source_id": source_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "timestamp": timestamp
            })
        
        # 批量存储所有 chunks 到 ChromaDB
        collection.add(
            documents=chunk_documents,
            metadatas=chunk_metadatas,
            ids=chunk_ids
        )
        
        return MemorizeResponse(
            status="success",
            doc_id=source_id,
            title=request.title,
            message=f"成功存储页面: {request.title} (拆分为 {len(chunks)} 个文本块)"
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
    聊天端点 - 使用 LLM 生成智能回答（基于 RAG 检索）
    
    Args:
        request: 包含用户消息的请求体
    
    Returns:
        包含 LLM 生成的回答和状态的响应体
    """
    try:
        # 检查数据库中是否有内容
        count = collection.count()
        
        if count == 0:
            # 数据库为空，返回简单响应
            response_text = f"收到您的消息：{request.message}\n\n💡 提示：目前还没有记忆任何页面。点击「Memorize This Page」按钮来保存页面内容。"
            return ChatResponse(
                response=response_text,
                status="success"
            )
        
        # 使用 RAG 检索 Top 5 最相关的文本块
        results = collection.query(
            query_texts=[request.message],
            n_results=min(15, count)
        )
        
        # 检查是否找到相关内容
        if not results or not results['documents'] or len(results['documents'][0]) == 0:
            response_text = f"收到您的消息：{request.message}\n\n未找到相关的页面内容。"
            return ChatResponse(
                response=response_text,
                status="success"
            )
        
        # 构建上下文
        context_snippets = []
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
            title = metadata.get('title', '未知标题')
            chunk_index = metadata.get('chunk_index', 0)
            context_snippets.append(f"[片段 {i} - 来自: {title}, 块 #{chunk_index}]\n{doc}")
        
        context = "\n\n".join(context_snippets)
        
        # 如果 LLM 客户端可用，使用 LLM 生成回答
        if llm_client:
            try:
                # 构建系统提示和用户消息
                system_prompt = """You are a helpful assistant. Answer the user's question based ONLY on the following context snippets. 
If the answer is not in the context, say you don't know. 
Please answer in the same language as the user's question.
Be concise and accurate."""
                
                user_message = f"""Context:
{context}

Question: {request.message}"""
                
                # 调用 LLM API
                completion = llm_client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                # 提取 LLM 回答
                llm_response = completion.choices[0].message.content
                
                return ChatResponse(
                    response=llm_response,
                    status="success"
                )
                
            except Exception as llm_error:
                # LLM 调用失败，降级为基础文本检索
                fallback_response = f"⚠️ LLM 服务暂时不可用，为您展示相关片段：\n\n"
                for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
                    title = metadata.get('title', '未知标题')
                    snippet = doc[:150] + "..." if len(doc) > 150 else doc
                    fallback_response += f"📄 {i}. {title}\n{snippet}\n\n"
                
                fallback_response += f"\n🔧 错误详情: {str(llm_error)}"
                
                return ChatResponse(
                    response=fallback_response,
                    status="fallback"
                )
        else:
            # LLM 客户端未配置，返回基础文本检索结果
            response_text = f"💡 提示：请配置 LLM API Key 以获得智能问答功能。\n\n根据您的问题「{request.message}」，找到以下相关内容：\n\n"
            
            for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
                title = metadata.get('title', '未知标题')
                snippet = doc[:150] + "..." if len(doc) > 150 else doc
                response_text += f"📄 {i}. {title}\n{snippet}\n\n"
            
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
