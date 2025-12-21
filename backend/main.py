from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
import hashlib
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

# 加载环境变量
load_dotenv()

# LLM客户端（支持热重载）
def get_llm_client():
    """获取LLM客户端（每次重新读取配置）"""
    # 重新加载环境变量
    load_dotenv(override=True)
    
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    
    if api_key:
        return OpenAI(api_key=api_key, base_url=base_url)
    return None

def get_llm_model():
    """获取当前配置的模型名称"""
    load_dotenv(override=True)
    return os.getenv("LLM_MODEL", "gpt-3.5-turbo")

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

class SettingsRequest(BaseModel):
    api_key: str
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "deepseek-ai/DeepSeek-V3"

# 辅助函数：读写.env文件
def read_env_file():
    """读取.env文件内容"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    return env_vars

def write_env_file(settings):
    """写入设置到.env文件"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(f"# LLM API Configuration\n")
        f.write(f"# 由桌面客户端自动生成\n\n")
        f.write(f"LLM_API_KEY={settings['api_key']}\n")
        f.write(f"LLM_BASE_URL={settings['base_url']}\n")
        f.write(f"LLM_MODEL={settings['model']}\n")

# 多配置管理
def get_configs_file_path():
    """获取配置文件路径"""
    return os.path.join(os.path.dirname(__file__), '..', 'api_configs.json')

def read_all_configs():
    """读取所有API配置"""
    config_path = get_configs_file_path()
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"configs": [], "active_config_id": None}

def write_all_configs(data):
    """保存所有配置到JSON文件"""
    config_path = get_configs_file_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 同时更新.env文件为当前激活的配置
    if data.get('active_config_id') and data.get('configs'):
        active_config = next(
            (c for c in data['configs'] if c['id'] == data['active_config_id']),
            None
        )
        if active_config:
            write_env_file({
                'api_key': active_config.get('apiKey', ''),
                'base_url': active_config.get('baseUrl', ''),
                'model': active_config.get('model', '')
            })



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
        llm_client = get_llm_client()
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
                    model=get_llm_model(),
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

@app.post("/chat-free", response_model=ChatResponse)
async def chat_free(request: ChatRequest):
    """
    自由聊天端点 - 结合知识库但允许AI自由发挥
    
    Args:
        request: 包含用户消息的请求体
    
    Returns:
        包含 LLM 生成的回答和状态的响应体
    """
    try:
        llm_client = get_llm_client()
        
        if not llm_client:
            return ChatResponse(
                response="⚠️ LLM未配置，请在桌面客户端设置中配置API Key",
                status="error"
            )
        
        # 检查数据库中是否有内容
        count = collection.count()
        context = ""
        
        if count > 0:
            # 检索相关内容作为参考
            results = collection.query(
                query_texts=[request.message],
                n_results=min(5, count)
            )
            
            if results and results['documents'] and len(results['documents'][0]) > 0:
                context_snippets = []
                for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
                    title = metadata.get('title', '未知标题')
                    context_snippets.append(f"[参考 {i} - {title}]\n{doc}")
                context = "\n\n".join(context_snippets)
        
        # 构建自由模式的系统提示
        system_prompt = """You are a helpful and knowledgeable assistant. 
If the user's question relates to the provided context, use it as a reference.
However, you are NOT limited to the context - you can also use your general knowledge to provide a comprehensive answer.
If the context is empty or irrelevant, just answer based on your general knowledge.
Please answer in the same language as the user's question.
Be helpful, accurate, and engaging."""
        
        if context:
            user_message = f"""参考资料（如相关）:
{context}

用户问题: {request.message}"""
        else:
            user_message = request.message
        
        # 调用 LLM API  
        completion = llm_client.chat.completions.create(
            model=get_llm_model(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        llm_response = completion.choices[0].message.content
        
        return ChatResponse(
            response=llm_response,
            status="success"
        )
    
    except Exception as e:
        return ChatResponse(
            response=f"处理消息时出错: {str(e)}",
            status="error"
        )


@app.get("/pages")
async def get_all_pages():
    """
    获取所有已保存页面的列表
    
    Returns:
        包含页面列表的响应
    """
    try:
        # 获取所有文档
        results = collection.get()
        
        if not results or not results['documents']:
            return {"pages": [], "total": 0}
        
        # 按source_id分组统计
        pages_dict = {}
        for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
            source_id = metadata.get('source_id', 'unknown')
            
            if source_id not in pages_dict:
                pages_dict[source_id] = {
                    'id': source_id,
                    'title': metadata.get('title', '未知标题'),
                    'timestamp': metadata.get('timestamp', ''),
                    'chunks': 1,
                    'preview': doc[:200] if doc else ''
                }
            else:
                pages_dict[source_id]['chunks'] += 1
        
        # 转换为列表并按时间排序
        pages = list(pages_dict.values())
        pages.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            "pages": pages,
            "total": len(pages)
        }
    
    except Exception as e:
        return {
            "pages": [],
            "total": 0,
            "error": str(e)
        }

@app.get("/pages/{page_id}")
async def get_page_detail(page_id: str):
    """
    获取单个页面的详细内容
    
    Args:
        page_id: 页面的source_id
    
    Returns:
        包含页面详细信息的响应
    """
    try:
        # 查询该source_id的所有chunks
        results = collection.get(
            where={"source_id": page_id}
        )
        
        if not results or not results['documents']:
            return {
                "error": "页面不存在",
                "id": page_id
            }
        
        # 合并所有chunks
        metadata = results['metadatas'][0]
        content = '\n\n'.join(results['documents'])
        
        return {
            "id": page_id,
            "title": metadata.get('title', '未知标题'),
            "timestamp": metadata.get('timestamp', ''),
            "chunks": len(results['documents']),
            "content": content
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "id": page_id
        }

@app.get("/settings")
async def get_settings():
    """获取当前LLM配置"""
    try:
        env_vars = read_env_file()
        return {
            "api_key": env_vars.get("LLM_API_KEY", ""),
            "base_url": env_vars.get("LLM_BASE_URL", "https://api.siliconflow.cn/v1"),
            "model": env_vars.get("LLM_MODEL", "deepseek-ai/DeepSeek-V3")
        }
    except Exception as e:
        return {
            "api_key": "",
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "deepseek-ai/DeepSeek-V3",
            "error": str(e)
        }

@app.post("/settings")
async def save_settings(settings: SettingsRequest):
    """保存LLM配置到.env文件"""
    try:
        write_env_file({
            "api_key": settings.api_key,
            "base_url": settings.base_url,
            "model": settings.model
        })
        return {
            "status": "success",
            "message": "设置已保存，请重启应用以生效"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"保存失败: {str(e)}"
        }

@app.get("/api-configs")
async def get_api_configs():
    """获取所有API配置"""
    try:
        return read_all_configs()
    except Exception as e:
        return {
            "configs": [],
            "active_config_id": None,
            "error": str(e)
        }

@app.post("/api-configs")
async def save_api_configs(data: dict):
    """保存所有API配置"""
    try:
        write_all_configs(data)
        return {
            "status": "success",
            "message": "配置已保存"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"保存失败: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    # 启动服务器
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
