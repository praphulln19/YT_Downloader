import React, { useState, useEffect } from 'react'

export default function App() {
  const [url, setUrl] = useState('')
  const [mediaType, setMediaType] = useState('video') // 'video' | 'audio'
  const [quality, setQuality] = useState('best')
  const [audioFormat, setAudioFormat] = useState('mp3')
  const [outputDir, setOutputDir] = useState('')
  
  // App system state
  const [hasFfmpeg, setHasFfmpeg] = useState(true)
  const [isFetching, setIsFetching] = useState(false)
  const [fetchedUrl, setFetchedUrl] = useState('')
  const [videoTitle, setVideoTitle] = useState('')
  const [availableHeights, setAvailableHeights] = useState([])
  
  // Download progress state
  const [downloadStatus, setDownloadStatus] = useState(null) // null | 'downloading' | 'processing' | 'done' | 'error'
  const [progress, setProgress] = useState(0)
  const [speed, setSpeed] = useState('')
  const [eta, setEta] = useState('')
  const [statusMessage, setStatusMessage] = useState('')

  useEffect(() => {
    if (window.api) {
      window.api.hasFfmpeg().then(setHasFfmpeg)
      window.api.getDefaultDownloadDir().then(setOutputDir)
      
      window.api.onDownloadProgress((data) => {
        setDownloadStatus('downloading')
        setProgress(data.percent || 0)
        setSpeed(data.speed || '')
        setEta(data.eta || '')
        setStatusMessage(`Downloading stream... ${data.percent ? data.percent.toFixed(1) + '%' : ''}`)
      })

      window.api.onDownloadProcessing(() => {
        setDownloadStatus('processing')
        setStatusMessage('Merging audio & video streams with FFmpeg...')
      })

      window.api.onDownloadDone((data) => {
        setDownloadStatus('done')
        setProgress(100)
        setStatusMessage(`Download complete. File saved to: ${data.dest}`)
      })

      window.api.onDownloadError((err) => {
        setDownloadStatus('error')
        setStatusMessage(`Error encountered: ${err}`)
      })
    }
  }, [])

  const handleFetchInfo = async (e) => {
    if (e) e.preventDefault()
    const cleanUrl = url.trim()
    if (!cleanUrl) return

    setIsFetching(true)
    setVideoTitle('Fetching media metadata...')
    setAvailableHeights([])
    setDownloadStatus(null)

    try {
      const info = await window.api.fetchInfo(cleanUrl)
      if (info.error) {
        setVideoTitle('')
        alert(`Failed to load video details: ${info.error}`)
      } else {
        setVideoTitle(info.title)
        setAvailableHeights(info.heights || [])
        setFetchedUrl(cleanUrl)
        setQuality('best')
      }
    } catch (err) {
      setVideoTitle('')
      alert(`Error fetching details: ${err.message}`)
    } finally {
      setIsFetching(false)
    }
  }

  const handleBrowse = async () => {
    const selected = await window.api.selectDirectory()
    if (selected) {
      setOutputDir(selected)
    }
  }

  const handleDownload = () => {
    const cleanUrl = url.trim()
    if (!cleanUrl) {
      alert('Please enter a YouTube URL first.')
      return
    }

    if (cleanUrl !== fetchedUrl) {
      alert('The URL has changed. Please click "Fetch Details" first.')
      return
    }

    setDownloadStatus('downloading')
    setProgress(0)
    setSpeed('')
    setEta('')
    setStatusMessage('Initializing download worker...')

    window.api.startDownload({
      url: cleanUrl,
      mediaType,
      quality,
      audioFormat,
      outputDir
    })
  }

  const handleUrlKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleFetchInfo()
    }
  }

  return (
    <div className="app-container">
      <header>
        <div className="logo-container">
          <div className="logo-badge">↓</div>
          <div>
            <h1>YT Downloader</h1>
            <p className="subtitle">Standalone Media Engine</p>
          </div>
        </div>

        <div>
          {hasFfmpeg ? (
            <div className="status-pill">
              <span className="pulse-dot">
                <span className="pulse-ping"></span>
                <span className="pulse-core"></span>
              </span>
              <span>FFmpeg Available</span>
            </div>
          ) : (
            <div className="status-pill missing">
              <span className="pulse-dot">
                <span className="pulse-ping"></span>
                <span className="pulse-core"></span>
              </span>
              <span>FFmpeg Missing (360p Max)</span>
            </div>
          )}
        </div>
      </header>

      <main className="dashboard-card">
        {/* URL Input Section */}
        <div className="input-group">
          <div className="section-title">01. Media URL</div>
          <div className="input-row">
            <input
              type="text"
              className="text-input"
              placeholder="https://www.youtube.com/watch?v=..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={handleUrlKeyDown}
              disabled={isFetching || downloadStatus === 'downloading' || downloadStatus === 'processing'}
            />
            <button
              className="btn btn-black"
              onClick={handleFetchInfo}
              disabled={!url.trim() || isFetching || downloadStatus === 'downloading' || downloadStatus === 'processing'}
            >
              {isFetching ? 'Fetching...' : 'Fetch Details'}
            </button>
          </div>
        </div>

        {/* Video Preview Card */}
        {videoTitle && (
          <div className="video-preview-card">
            <div className="video-preview-meta">YTD_STREAM_METADATA :: READY</div>
            <div className="video-preview-title">{videoTitle}</div>
          </div>
        )}

        {/* Format & Mode Selection */}
        <div className="input-group">
          <div className="section-title">02. Media Type</div>
          <div className="mode-grid">
            <div
              className={`mode-item ${mediaType === 'video' ? 'active' : ''}`}
              onClick={() => {
                if (downloadStatus !== 'downloading' && downloadStatus !== 'processing') {
                  setMediaType('video')
                }
              }}
            >
              <div className="mode-title">Video & Audio</div>
              <div className="mode-desc">High-definition video (MP4)</div>
            </div>

            <div
              className={`mode-item ${mediaType === 'audio' ? 'active' : ''}`}
              onClick={() => {
                if (downloadStatus !== 'downloading' && downloadStatus !== 'processing') {
                  setMediaType('audio')
                }
              }}
            >
              <div className="mode-title">Audio Only</div>
              <div className="mode-desc">Audio stream (MP3, M4A, Opus)</div>
            </div>
          </div>
        </div>

        {/* Quality Chips Selection */}
        <div className="input-group">
          <div className="section-title">
            {mediaType === 'video' ? '03. Preferred Quality' : '03. Audio Format'}
          </div>

          {mediaType === 'video' ? (
            <div className="chip-grid">
              <button
                type="button"
                className={`chip-item ${quality === 'best' ? 'active' : ''}`}
                onClick={() => setQuality('best')}
                disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-main">Best</span>
                <span className="chip-sub">Max Quality</span>
              </button>

              {availableHeights.map((h) => (
                <button
                  type="button"
                  key={h}
                  className={`chip-item ${quality === String(h) ? 'active' : ''}`}
                  onClick={() => setQuality(String(h))}
                  disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
                >
                  <span className="chip-main">{h}p</span>
                  <span className="chip-sub">{h >= 1080 ? 'Full HD' : h >= 720 ? 'HD' : 'SD'}</span>
                </button>
              ))}

              <button
                type="button"
                className={`chip-item ${quality === 'small' ? 'active' : ''}`}
                onClick={() => setQuality('small')}
                disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-main">Small</span>
                <span className="chip-sub">Compact</span>
              </button>
            </div>
          ) : (
            <div className="chip-grid">
              <button
                type="button"
                className={`chip-item ${audioFormat === 'mp3' ? 'active' : ''}`}
                onClick={() => setAudioFormat('mp3')}
                disabled={!hasFfmpeg || downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-main">MP3</span>
                <span className="chip-sub">Universal</span>
              </button>
              <button
                type="button"
                className={`chip-item ${audioFormat === 'original' ? 'active' : ''}`}
                onClick={() => setAudioFormat('original')}
                disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-main">M4A</span>
                <span className="chip-sub">Original</span>
              </button>
              <button
                type="button"
                className={`chip-item ${audioFormat === 'opus' ? 'active' : ''}`}
                onClick={() => setAudioFormat('opus')}
                disabled={!hasFfmpeg || downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-main">Opus</span>
                <span className="chip-sub">High Efficiency</span>
              </button>
            </div>
          )}
        </div>

        {/* Destination Path */}
        <div className="input-group">
          <div className="section-title">04. Save Location</div>
          <div className="input-row">
            <input
              type="text"
              className="text-input"
              value={outputDir}
              onChange={(e) => setOutputDir(e.target.value)}
              disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
            />
            <button
              className="btn btn-outline"
              onClick={handleBrowse}
              disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
            >
              Browse
            </button>
          </div>
        </div>

        {/* Action Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
          <button
            className="btn btn-black"
            style={{ padding: '14px 32px', fontSize: '15px' }}
            onClick={handleDownload}
            disabled={!fetchedUrl || downloadStatus === 'downloading' || downloadStatus === 'processing'}
          >
            Start Download
          </button>
        </div>

        {/* Terminal Widget Output Console */}
        {downloadStatus && (
          <div className="terminal-widget">
            <div className="terminal-header">
              <div className="terminal-dots">
                <div className="terminal-dot"></div>
                <div className="terminal-dot"></div>
                <div className="terminal-dot"></div>
              </div>
              <div className="terminal-path">session@yt-downloader:~</div>
            </div>
            <div className="terminal-body">
              <div>
                <span className="terminal-prompt">➜</span>
                <span>{statusMessage}</span>
              </div>
              {downloadStatus === 'downloading' && (
                <div>
                  <span className="terminal-prompt">➜</span>
                  <span>{speed && `Speed: ${speed}`} {eta && `• ETA: ${eta}`}</span>
                </div>
              )}
              <div className={`progress-bar-bg ${downloadStatus === 'processing' ? 'indeterminate' : ''}`}>
                <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer>
        <span>YT Downloader v1.0.3</span>
        <span>Built with Electron & React</span>
      </footer>
    </div>
  )
}
