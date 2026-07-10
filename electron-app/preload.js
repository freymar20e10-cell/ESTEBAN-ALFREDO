/**
 * BT-7274 — Preload Script
 * Expone APIs seguras al renderer (la UI).
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('btAPI', {
    // Control de ventana
    minimize: () => ipcRenderer.invoke('window-minimize'),
    maximize: () => ipcRenderer.invoke('window-maximize'),
    close: () => ipcRenderer.invoke('window-close'),
    quit: () => ipcRenderer.invoke('window-quit'),

    // Autostart
    getAutoStart: () => ipcRenderer.invoke('get-autostart'),
    setAutoStart: (enable) => ipcRenderer.invoke('set-autostart', enable),

    // Abrir links externos
    openExternal: (url) => ipcRenderer.invoke('open-external', url),

    // Escuchar eventos del main process
    on: (channel, callback) => {
        ipcRenderer.on(channel, (_, ...args) => callback(...args));
    },
});
