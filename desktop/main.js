const { app, BrowserWindow, Tray, Menu, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let tray;
let backendProcess;

// 启动FastAPI后端服务
function startBackend() {
    console.log('Starting FastAPI backend...');

    const pythonPath = path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe');
    const backendPath = path.join(__dirname, '..', 'backend', 'main.py');

    backendProcess = spawn(pythonPath, [
        '-m', 'uvicorn',
        'backend.main:app',
        '--host', '127.0.0.1',
        '--port', '8000'
    ], {
        cwd: path.join(__dirname, '..')
    });

    backendProcess.stdout.on('data', (data) => {
        console.log(`Backend: ${data}`);
    });

    backendProcess.stderr.on('data', (data) => {
        console.error(`Backend Error: ${data}`);
    });

    backendProcess.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
    });
}

// 停止后端服务
function stopBackend() {
    if (backendProcess) {
        console.log('Stopping backend...');
        backendProcess.kill();
        backendProcess = null;
    }
}

// 创建主窗口
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false
        },
        icon: path.join(__dirname, 'icon.png')
    });

    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

    // 开发模式下打开DevTools
    // mainWindow.webContents.openDevTools();

    mainWindow.on('close', (event) => {
        if (!app.isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// 创建系统托盘
function createTray() {
    // 使用默认图标（可以后续替换）
    const iconPath = path.join(__dirname, 'icon.png');
    tray = new Tray(iconPath);

    const contextMenu = Menu.buildFromTemplate([
        {
            label: '打开知识库',
            click: () => {
                if (mainWindow === null) {
                    createWindow();
                } else {
                    mainWindow.show();
                }
            }
        },
        {
            label: '后端状态',
            enabled: false
        },
        {
            type: 'separator'
        },
        {
            label: '退出',
            click: () => {
                app.isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setToolTip('Web-Retrace 知识库');
    tray.setContextMenu(contextMenu);

    tray.on('click', () => {
        if (mainWindow === null) {
            createWindow();
        } else {
            mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
        }
    });
}

// 应用启动
app.whenReady().then(() => {
    startBackend();

    // 等待后端启动
    setTimeout(() => {
        createWindow();
        createTray();
    }, 3000);

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

// 应用退出
app.on('before-quit', () => {
    stopBackend();
});

app.on('window-all-closed', () => {
    // 在macOS下，除非用户明确退出，否则应用会保持活动状态
    if (process.platform !== 'darwin') {
        // Windows下窗口关闭不退出应用，只是隐藏
    }
});

// IPC通信
ipcMain.handle('get-backend-status', async () => {
    return backendProcess !== null;
});
