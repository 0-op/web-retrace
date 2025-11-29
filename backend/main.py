from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 创建 FastAPI 应用实例
app = FastAPI(title="Web-Retrace API", version="1.0.0")

# 配置 CORS - 允许 Chrome 扩展跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义请求模型
class ChatRequest(BaseModel):
    message: str

# 定义响应模型
class ChatResponse(BaseModel):
    response: str
    status: str

@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {"message": "Web-Retrace API 正在运行", "version": "1.0.0"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天端点 - 接收消息并返回响应
    
    Args:
        request: 包含用户消息的请求体
    
    Returns:
        包含响应消息和状态的响应体
    """
    # MVP 阶段：简单回显消息
    response_text = f"收到您的消息：{request.message}"
    
    return ChatResponse(
        response=response_text,
        status="success"
    )

if __name__ == "__main__":
    import uvicorn
    # 启动服务器
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
