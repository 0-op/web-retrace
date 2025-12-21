const API_BASE_URL = 'http://localhost:8000';

// 页面加载时获取当前配置
document.addEventListener('DOMContentLoaded', async () => {
    await loadCurrentSettings();
});

// 加载当前配置
async function loadCurrentSettings() {
    try {
        const response = await fetch(`${API_BASE_URL}/settings`);
        if (response.ok) {
            const settings = await response.json();

            // 填充表单
            if (settings.api_key) {
                document.getElementById('apiKey').value = settings.api_key;
            }
            if (settings.base_url) {
                document.getElementById('baseUrl').value = settings.base_url;
            }
            if (settings.model) {
                document.getElementById('model').value = settings.model;
            }
        }
    } catch (error) {
        console.error('加载设置失败:', error);
    }
}

// 表单提交
document.getElementById('settingsForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const apiKey = document.getElementById('apiKey').value.trim();
    const baseUrl = document.getElementById('baseUrl').value.trim();
    const model = document.getElementById('model').value.trim();

    if (!apiKey) {
        showAlert('请输入API Key', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/settings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_key: apiKey,
                base_url: baseUrl,
                model: model
            })
        });

        if (response.ok) {
            showAlert('✅ 设置已保存！重启应用后生效', 'success');

            // 2秒后关闭窗口
            setTimeout(() => {
                window.close();
            }, 2000);
        } else {
            throw new Error('保存失败');
        }
    } catch (error) {
        console.error('保存设置失败:', error);
        showAlert('❌ 保存失败，请检查后端服务', 'error');
    }
});

// 显示提示消息
function showAlert(message, type) {
    const alertBox = document.getElementById('alertBox');
    alertBox.className = `alert alert-${type}`;
    alertBox.textContent = message;
    alertBox.classList.remove('hidden');

    if (type === 'success') {
        setTimeout(() => {
            alertBox.classList.add('hidden');
        }, 3000);
    }
}
