const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const path = require('path')
const { spawn, exec } = require('child_process')

const isDev = process.argv.includes('--dev')
const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'

function createWindow() {
  const win = new BrowserWindow({
    width: 1040,
    height: 720,
    minWidth: 920,
    minHeight: 640,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    },
    autoHideMenuBar: true
  })

  if (isDev) {
    win.loadURL('http://localhost:5173')
  } else {
    win.loadFile(path.join(__dirname, 'dist-react', 'index.html'))
  }
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// IPC Handlers
ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory']
  })
  if (result.canceled) return null
  return result.filePaths[0]
})

ipcMain.handle('get-default-download-dir', () => {
  return app.getPath('downloads')
})

ipcMain.handle('has-ffmpeg', async () => {
  const bridgeScript = path.join(__dirname, 'bridge.py')
  const tryCmd = (cmd) => new Promise((resolve) => {
    exec(`${cmd} "${bridgeScript}" check-ffmpeg`, { cwd: __dirname, timeout: 130000 }, (err, stdout) => {
      if (err) return resolve(null)
      try {
        const parsed = JSON.parse(stdout.trim())
        resolve(parsed.available === true)
      } catch {
        resolve(null)
      }
    })
  })
  // Try 'python' first, then 'py' (Windows Python Launcher)
  const result = await tryCmd(pythonCmd)
  if (result !== null) return result
  const fallback = await tryCmd('py')
  return fallback === true
})

ipcMain.handle('fetch-info', async (event, url) => {
  return new Promise((resolve) => {
    const bridgeScript = path.join(__dirname, 'bridge.py')
    const child = spawn(pythonCmd, [bridgeScript, 'info', url], { cwd: __dirname })
    let output = ''
    let errorOutput = ''

    child.stdout.on('data', (data) => {
      output += data.toString()
    })

    child.stderr.on('data', (data) => {
      errorOutput += data.toString()
    })

    child.on('close', (code) => {
      if (code !== 0) {
        try {
          const parsed = JSON.parse(output)
          resolve({ error: parsed.error || errorOutput || 'Failed to fetch details' })
        } catch {
          resolve({ error: errorOutput.trim() || output.trim() || 'Failed to fetch details' })
        }
      } else {
        try {
          const parsed = JSON.parse(output)
          resolve(parsed)
        } catch (e) {
          resolve({ error: 'Failed to parse video info: ' + e.message })
        }
      }
    })
  })
})

ipcMain.on('start-download', (event, { url, mediaType, quality, audioFormat, outputDir }) => {
  const bridgeScript = path.join(__dirname, 'bridge.py')
  const child = spawn(pythonCmd, [bridgeScript, 'download', url, mediaType, quality, audioFormat, outputDir], { cwd: __dirname })

  child.stdout.on('data', (data) => {
    const lines = data.toString().split('\n')
    for (const line of lines) {
      if (!line.trim()) continue
      try {
        const parsed = JSON.parse(line)
        if (parsed.status === 'downloading') {
          event.reply('download-progress', parsed)
        } else if (parsed.status === 'processing') {
          event.reply('download-processing', parsed)
        } else if (parsed.status === 'done') {
          event.reply('download-done', parsed)
        } else if (parsed.error) {
          event.reply('download-error', parsed.error)
        }
      } catch {
        // Non-json stdout line
      }
    }
  })

  child.stderr.on('data', (data) => {
    // Stderr output
  })

  child.on('close', (code) => {
    if (code !== 0) {
      event.reply('download-error', 'Download process exited with code ' + code)
    }
  })
})
