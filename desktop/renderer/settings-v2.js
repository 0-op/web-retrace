const API_BASE_URL = 'http://localhost:8000';

let configs = [];
let currentConfigId = null;

// 预设配置
const PRESETS = {
    openai: {
        name: 'OpenAI',
        baseUrl: 'https://api.openai.com/v1',
        model: 'gpt-4'
    },
    deepseek: {
        name: 'DeepSeek',
        baseUrl: 'https://api.deepseek.com/v1',
        model: 'deepseek-chat'
    },
    siliconflow: {
        name: 'SiliconFlow',
        baseUrl: 'https://api.siliconflow.cn/v1',
        model: 'deepseek-ai/DeepSeek-V3'
    },
    google: {
        name: 'Google Gemini',
        baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai/',
        model: 'gemini-1.5-flash'
    },
    anthropic: {
        name: 'Anthropic Claude',
        baseUrl: 'https://api.anthropic.com/v1',
        model: 'claude-3-5-sonnet-20241022'
    },
    custom: {
        name: '自定义',
        baseUrl: '',
        model: ''
    }
};

// 页面加载
document.addEventListener('DOMContentLoaded', async () => {
    await loadConfigs();
    renderConfigsList();
});

// 加载所有配置
async function loadConfigs() {
    try {
        const response = await fetch(`${API_BASE_URL}/api-configs`);
        if (response.ok) {
            const data = await response.json();
            configs = data.configs || [];
            currentConfigId = data.active_config_id;

            // 如果没有配置，创建默认配置
            if (configs.length === 0) {
                configs = [{
                    id: Date.now().toString(),
                    name: 'SiliconFlow',
                    apiKey: '',
                    baseUrl: 'https://api.siliconflow.cn/v1',
                    model: 'deepseek-ai/DeepSeek-V3'
                }];
                currentConfigId = configs[0].id;
            }
        }
    } catch (error) {
        console.error('加载配置失败:', error);
        showAlert('无法连接到后端服务', 'error');
    }
}

// 渲染配置列表
function renderConfigsList() {
    const list = document.getElementById('configsList');

    if (configs.length === 0) {
        list.innerHTML = '<div style="padding:20px;text-align:center;color:#999;">暂无配置</div>';
        return;
    }

    list.innerHTML = configs.map(config => `
        <div class="config-item ${config.id === currentConfigId ? 'active' : ''}" 
             onclick="selectConfig('${config.id}')">
            <div class="config-name">${escapeHtml(config.name)}</div>
            <div class="config-provider">${config.baseUrl ? new URL(config.baseUrl).hostname : '未配置'}</div>
        </div>
    `).join('');

    // 加载当前配置到表单
    if (currentConfigId) {
        loadConfigToForm(currentConfigId);
    }
}

// 选择配置
function selectConfig(configId) {
    currentConfigId = configId;
    renderConfigsList();
}

// 加载配置到表单
function loadConfigToForm(configId) {
    const config = configs.find(c => c.id === configId);
    if (!config) return;

    document.getElementById('configName').value = config.name;
    document.getElementById('apiKey').value = config.apiKey || '';
    document.getElementById('baseUrl').value = config.baseUrl || '';
    document.getElementById('model').value = config.model || '';

    document.getElementById('deleteBtn').disabled = configs.length <= 1;
}

// 加载预设
function loadPreset(presetKey) {
    const preset = PRESETS[presetKey];
    if (!preset) return;

    document.getElementById('configName').value = preset.name;
    document.getElementById('baseUrl').value = preset.baseUrl;
    document.getElementById('model').value = preset.model;
}

// 新建配置
function addNewConfig() {
    const newConfig = {
        id: Date.now().toString(),
        name: '新配置',
        apiKey: '',
        baseUrl: 'https://api.openai.com/v1',
        model: 'gpt-4'
    };

    configs.push(newConfig);
    currentConfigId = newConfig.id;
    renderConfigsList();
}

// 删除配置
async function deleteConfig() {
    if (configs.length <= 1) {
        showAlert('至少需要保留一个配置', 'error');
        return;
    }

    if (!confirm('确定要删除这个配置吗？')) {
        return;
    }

    configs = configs.filter(c => c.id !== currentConfigId);
    currentConfigId = configs[0].id;

    await saveAllConfigs();
    renderConfigsList();
    showAlert('配置已删除', 'success');
}

// 保存表单
document.getElementById('configForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('configName').value.trim();
    const apiKey = document.getElementById('apiKey').value.trim();
    const baseUrl = document.getElementById('baseUrl').value.trim();
    const model = document.getElementById('model').value.trim();

    if (!name || !apiKey) {
        showAlert('请填写配置名称和API Key', 'error');
        return;
    }

    // 更新当前配置
    const config = configs.find(c => c.id === currentConfigId);
    if (config) {
        config.name = name;
        config.apiKey = apiKey;
        config.baseUrl = baseUrl;
        config.model = model;
    }

    await saveAllConfigs();
});

// 保存所有配置到后端
async function saveAllConfigs() {
    try {
        const response = await fetch(`${API_BASE_URL}/api-configs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                configs: configs,
                active_config_id: currentConfigId
            })
        });

        if (response.ok) {
            showAlert('✅ 配置已保存并立即生效！', 'success');
            renderConfigsList();

            setTimeout(() => {
                window.close();
            }, 2000);
        } else {
            throw new Error('保存失败');
        }
    } catch (error) {
        console.error('保存失败:', error);
        showAlert('❌ 保存失败，请检查后端服务', 'error');
    }
}

// 显示提示
function showAlert(message, type) {
    const alertBox = document.getElementById('alertBox');
    alertBox.className = `alert alert-${type}`;
    alertBox.textContent = message;
    alertBox.classList.remove('hidden');

    if (type === 'success') {
        setTimeout(() => alertBox.classList.add('hidden'), 3000);
    }
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
