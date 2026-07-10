/**
 * BT-7274 — Electron Main Process
 * App de escritorio nativa con bandeja del sistema.
 */

const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// Evitar múltiples instancias
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
    app.quit();
}

// Manejar errores de pipe no capturados (EPIPE)
process.on('uncaughtException', (err) => {
    if (err.code === 'EPIPE') return; // Ignorar silenciosamente
    // Para otros errores, mostrar en consola si es posible
    try {
        process.stderr.write(`Uncaught: ${err.message}\n`);
    } catch (e) {}
});

// ═══════════════════════════════════════════
// ESTADO
// ═══════════════════════════════════════════

let mainWindow = null;
let tray = null;
let pythonProcess = null;
let isQuitting = false;

const PYTHON_SERVER_PORT = 8765;
const HTTP_SERVER_PORT = 8080;

// ═══════════════════════════════════════════
// INICIAR SERVIDOR PYTHON
// ═══════════════════════════════════════════

function startPythonServer() {
    const projectDir = path.join(__dirname, '..');
    const serverPath = path.join(projectDir, 'server.py');

    if (!fs.existsSync(serverPath)) {
        console.error('server.py no encontrado en:', serverPath);
        return;
    }

    console.log('Iniciando servidor Python...');
    pythonProcess = spawn('python', [serverPath], {
        cwd: projectDir,
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: false,
    });

    pythonProcess.stdout.on('data', (data) => {
        try {
            process.stdout.write(`[Python] ${data.toString().trim()}\n`);
        } catch (e) {
            // Ignorar errores de pipe
        }
    });

    pythonProcess.stderr.on('data', (data) => {
        const msg = data.toString().trim();
        if (msg) {
            try {
                process.stderr.write(`[Python Error] ${msg}\n`);
            } catch (e) {
                // Ignorar errores de pipe roto
            }
        }
    });

    pythonProcess.on('close', (code) => {
        console.log(`Servidor Python cerrado (código ${code})`);
    });
}

function stopPythonServer() {
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
}

// ═══════════════════════════════════════════
// VENTANA PRINCIPAL
// ═══════════════════════════════════════════

function createWindow() {
    mainWindow = new BrowserWindow({
        title: 'JARVIS — El Núcleo',
        width: 1200,
        height: 750,
        minWidth: 900,
        minHeight: 600,
        frame: false,           // Sin borde nativo — usaremos el nuestro
        transparent: false,
        backgroundColor: '#0a0f1a',
        icon: path.join(__dirname, 'assets', 'icon.png'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        show: false,            // No mostrar hasta que cargue
    });

    // Esperar a que el servidor Python esté listo, luego cargar
    let retries = 0;
    const tryLoad = () => {
        const http = require('http');
        const req = http.get(`http://127.0.0.1:${HTTP_SERVER_PORT}`, (res) => {
            console.log('Servidor listo, cargando interfaz...');
            mainWindow.loadURL(`http://127.0.0.1:${HTTP_SERVER_PORT}`);
        });
        req.on('error', () => {
            retries++;
            if (retries < 20) {
                setTimeout(tryLoad, 500);
            } else {
                console.error('No se pudo conectar al servidor Python');
                mainWindow.loadURL(`http://127.0.0.1:${HTTP_SERVER_PORT}`);
            }
        });
        req.end();
    };

    setTimeout(tryLoad, 1000);

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // Minimizar a bandeja en vez de cerrar
    mainWindow.on('close', (event) => {
        if (!isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// ═══════════════════════════════════════════
// BANDEJA DEL SISTEMA (System Tray)
// ═══════════════════════════════════════════

function createTray() {
    const iconPath = path.join(__dirname, 'assets', 'icon-tray.png');
    const icon = fs.existsSync(iconPath) ? iconPath : path.join(__dirname, 'assets', 'icon.png');

    tray = new Tray(icon);

    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'BT-7274 — Active',
            enabled: false,
        },
        { type: 'separator' },
        {
            label: 'Open Dashboard',
            click: () => showWindow(),
        },
        {
            label: 'Settings',
            click: () => {
                showWindow();
                mainWindow?.webContents.send('open-settings');
            },
        },
        {
            label: 'Toggle Voice Chat',
            click: () => {
                mainWindow?.webContents.send('toggle-voice-chat');
            },
        },
        { type: 'separator' },
        {
            label: 'Quit BT-7274',
            click: () => quitApp(),
        },
    ]);

    tray.setToolTip('BT-7274 — Protocol 3 Active');
    tray.setContextMenu(contextMenu);

    tray.on('click', () => {
        if (mainWindow?.isVisible()) {
            mainWindow.hide();
        } else {
            showWindow();
        }
    });
}

function showWindow() {
    if (!mainWindow) {
        createWindow();
        return;
    }
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
}

function quitApp() {
    isQuitting = true;
    stopPythonServer();
    globalShortcut.unregisterAll();
    app.quit();
}

// ═══════════════════════════════════════════
// ARRANQUE AUTOMÁTICO CON WINDOWS
// ═══════════════════════════════════════════

function setAutoStart(enable) {
    app.setLoginItemSettings({
        openAtLogin: enable,
        name: 'BT-7274',
        path: process.execPath,
    });
}

// ═══════════════════════════════════════════
// IPC — Comunicación con el renderer
// ═══════════════════════════════════════════

ipcMain.handle('window-minimize', () => mainWindow?.minimize());
ipcMain.handle('window-maximize', () => {
    if (mainWindow?.isMaximized()) {
        mainWindow.unmaximize();
    } else {
        mainWindow?.maximize();
    }
});
ipcMain.handle('window-close', () => mainWindow?.hide());
ipcMain.handle('window-quit', () => quitApp());

ipcMain.handle('get-autostart', () => {
    return app.getLoginItemSettings().openAtLogin;
});
ipcMain.handle('set-autostart', (_, enable) => {
    setAutoStart(enable);
    return enable;
});

ipcMain.handle('open-external', (_, url) => {
    shell.openExternal(url);
});

// ═══════════════════════════════════════════
// APP EVENTS
// ═══════════════════════════════════════════

app.whenReady().then(() => {
    // Iniciar servidor Python
    startPythonServer();

    // Crear ventana
    createWindow();

    // Crear tray
    createTray();

    // HOTKEYS GLOBALES
    
    // Ctrl+Shift+B: Abrir/cerrar BT-7274
    globalShortcut.register('CommandOrControl+Shift+B', () => {
        if (mainWindow?.isVisible()) {
            mainWindow.hide();
        } else {
            showWindow();
        }
    });

    // Ctrl+Shift+V: Activar/desactivar chat de voz
    globalShortcut.register('CommandOrControl+Shift+V', () => {
        showWindow(); // Asegurar que la ventana está visible
        mainWindow?.webContents.send('toggle-voice-chat');
    });

    // Ctrl+Alt+M: Minimizar a tray (sin abrir)
    globalShortcut.register('CommandOrControl+Alt+M', () => {
        if (mainWindow?.isVisible()) {
            mainWindow.hide();
        }
    });

    // Configurar arranque automático (activado por defecto)
    setAutoStart(true);
    console.log('Hotkeys registrados: Ctrl+Shift+B, Ctrl+Shift+V, Ctrl+Alt+M');
});

app.on('second-instance', () => {
    showWindow();
});

app.on('window-all-closed', () => {
    // No cerrar la app cuando se cierran ventanas — se va a tray
    // En macOS esto es el comportamiento normal
    // En Windows y Linux lo manejamos nosotros
    if (process.platform !== 'darwin') {
        // No llamar app.quit() — la app sigue en tray
    }
});

app.on('activate', () => {
    showWindow();
});

app.on('before-quit', () => {
    isQuitting = true;
    stopPythonServer();
});
