// API 配置
const API_BASE_URL = 'http://localhost:8000';

// DOM 元素
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const messagesContainer = document.getElementById('messagesContainer');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');

// 更新状态指示器
function updateStatus(status, text) {
    statusDot.className = `status-dot status-${status}`;
    statusText.textContent = text;
}

// 添加消息到界面
function addMessage(text, type = 'user') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);
    
    // 移除欢迎消息
    const welcomeMessage = messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 发送消息到后端
async function sendMessage() {
    const message = messageInput.value.trim();
    
    if (!message) {
        return;
    }
    
    // 禁用输入和按钮
    sendButton.disabled = true;
    messageInput.disabled = true;
    updateStatus('loading', '发送中...');
    
    // 显示用户消息
    addMessage(message, 'user');
    messageInput.value = '';
    
    try {
        // 调用后端 API
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP 错误: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 显示后端响应
        addMessage(data.response, 'assistant');
        updateStatus('success', '连接成功');
        
    } catch (error) {
        console.error('发送消息失败:', error);
        addMessage(`❌ 错误: ${error.message}。请确保后端服务已启动 (localhost:8000)`, 'error');
        updateStatus('error', '连接失败');
    } finally {
        // 恢复输入和按钮
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

// 事件监听器
sendButton.addEventListener('click', sendMessage);

messageInput.addEventListener('keydown', (e) => {
    // Ctrl+Enter 或 Cmd+Enter 发送消息
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        sendMessage();
    }
});

// 初始化
updateStatus('ready', '就绪');
messageInput.focus();
