const API_BASE_URL = 'http://localhost:8000';

let allPages = [];
let filteredPages = [];

// DOM元素
const searchInput = document.getElementById('searchInput');
const pagesList = document.getElementById('pagesList');
const statusText = document.getElementById('statusText');
const totalPagesEl = document.getElementById('totalPages');
const detailModal = document.getElementById('detailModal');
const closeBtn = document.querySelector('.close');
const settingsBtn = document.getElementById('settingsBtn');

// 初始化
async function init() {
    await checkBackendStatus();
    await loadPages();
    setupEventListeners();
}

// 检查后端状态
async function checkBackendStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
            const data = await response.json();
            statusText.textContent = '后端运行中';
            totalPagesEl.textContent = data.stored_pages;
            return true;
        }
    } catch (error) {
        statusText.textContent = '后端连接失败';
        return false;
    }
}

// 加载所有页面
async function loadPages() {
    try {
        pagesList.innerHTML = '<div class="loading">正在加载页面...</div>';

        // 调用后端API获取所有存储的页面
        // 注意：需要在后端添加获取所有页面的API端点
        // 目前先模拟从ChromaDB获取
        const response = await fetch(`${API_BASE_URL}/pages`);

        if (!response.ok) {
            throw new Error('加载失败');
        }

        const data = await response.json();
        allPages = data.pages || [];
        filteredPages = [...allPages];

        renderPages();
    } catch (error) {
        console.error('加载页面失败:', error);
        pagesList.innerHTML = `
            <div class="loading">
                ⚠️ 暂时无法加载页面列表<br>
                <small>后端API尚未完全实现，请稍候...</small>
            </div>
        `;
    }
}

// 渲染页面列表
function renderPages() {
    if (filteredPages.length === 0) {
        pagesList.innerHTML = '<div class="loading">没有找到页面</div>';
        return;
    }

    const html = filteredPages.map(page => `
        <div class="page-item" data-id="${page.id}">
            <div class="page-title">${escapeHtml(page.title)}</div>
            <div class="page-meta">
                <span>📅 ${formatDate(page.timestamp)}</span>
                ${page.chunks ? `<span>📦 ${page.chunks} 个片段</span>` : ''}
            </div>
            ${page.preview ? `<div class="page-preview">${escapeHtml(page.preview)}</div>` : ''}
        </div>
    `).join('');

    pagesList.innerHTML = html;

    // 添加点击事件
    document.querySelectorAll('.page-item').forEach(item => {
        item.addEventListener('click', () => {
            const pageId = item.dataset.id;
            showPageDetail(pageId);
        });
    });
}

// 显示页面详情
async function showPageDetail(pageId) {
    try {
        const response = await fetch(`${API_BASE_URL}/pages/${pageId}`);
        const data = await response.json();

        document.getElementById('detailTitle').textContent = data.title;
        document.getElementById('detailTime').textContent = `保存于 ${formatDate(data.timestamp)}`;
        document.getElementById('detailContent').textContent = data.content || '内容为空';

        detailModal.style.display = 'block';
    } catch (error) {
        console.error('加载详情失败:', error);
        alert('无法加载页面详情');
    }
}

// 搜索功能
function handleSearch() {
    const query = searchInput.value.toLowerCase().trim();

    if (!query) {
        filteredPages = [...allPages];
    } else {
        filteredPages = allPages.filter(page =>
            page.title.toLowerCase().includes(query) ||
            (page.preview && page.preview.toLowerCase().includes(query))
        );
    }

    renderPages();
}

// 设置事件监听
function setupEventListeners() {
    // 搜索
    searchInput.addEventListener('input', handleSearch);

    // 设置按钮
    settingsBtn.addEventListener('click', () => {
        window.open('settings.html', '_blank', 'width=700,height=600');
    });

    // 关闭模态框
    closeBtn.addEventListener('click', () => {
        detailModal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target === detailModal) {
            detailModal.style.display = 'none';
        }
    });
}

// 工具函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(timestamp) {
    if (!timestamp) return '未知时间';
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
}

// 启动应用
document.addEventListener('DOMContentLoaded', init);
