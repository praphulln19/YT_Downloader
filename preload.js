const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  fetchInfo: (url) => ipcRenderer.invoke('fetch-info', url),
  startDownload: (args) => ipcRenderer.send('start-download', args),
  onDownloadProgress: (callback) => ipcRenderer.on('download-progress', (event, data) => callback(data)),
  onDownloadDone: (callback) => ipcRenderer.on('download-done', (event, data) => callback(data)),
  onDownloadError: (callback) => ipcRenderer.on('download-error', (event, data) => callback(data)),
  onDownloadProcessing: (callback) => ipcRenderer.on('download-processing', (event, data) => callback(data)),
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  getDefaultDownloadDir: () => ipcRenderer.invoke('get-default-download-dir'),
  hasFfmpeg: () => ipcRenderer.invoke('has-ffmpeg'),
})
