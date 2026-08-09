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
        setStatusMessage(`Downloading... ${data.percent ? data.percent.toFixed(1) + '%' : ''}`)
      })

      window.api.onDownloadProcessing(() => {
        setDownloadStatus('processing')
        setStatusMessage('Processing and merging streams (FFmpeg)...')
      })

      window.api.onDownloadDone((data) => {
        setDownloadStatus('done')
        setProgress(100)
        setStatusMessage(`Download complete! Saved to: ${data.dest}`)
      })

      window.api.onDownloadError((err) => {
        setDownloadStatus('error')
        setStatusMessage(`Failed: ${err}`)
      })
    }
  }, [])

  const handleFetchInfo = async (e) => {
    if (e) e.preventDefault()
    const cleanUrl = url.trim()
    if (!cleanUrl) return

    setIsFetching(true)
    setVideoTitle('Analyzing video metadata...')
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
      alert('Please enter a YouTube link first.')
      return
    }

    if (cleanUrl !== fetchedUrl) {
      alert('The URL has changed. Please click "Fetch Info" first to load available qualities.')
      return
    }

    setDownloadStatus('downloading')
    setProgress(0)
    setSpeed('')
    setEta('')
    setStatusMessage('Starting download...')

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

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText()
      if (text) {
        setUrl(text)
      }
    } catch (err) {
      // Ignore fallback
    }
  }

  return (
    <div className="app-container">
      {/* Glow Backdrop Lights */}
      <div className="glow-light glow-1"></div>
      <div className="glow-light glow-2"></div>

      <header>
        <div className="logo-container">
          <div className="logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
          </div>
          <div>
            <h1>YT Downloader</h1>
            <p className="subtitle">Modern High-Quality Media Utility</p>
          </div>
        </div>
        <div>
          {hasFfmpeg ? (
            <span className="ffmpeg-badge">
              <span className="dot"></span> Bundled FFmpeg Ready
            </span>
          ) : (
            <span className="ffmpeg-badge missing">
              <span className="dot"></span> System Mode (360p max)
            </span>
          )}
        </div>
      </header>

      <main className="dashboard-card">
        {/* Main URL Bar */}
        <div className="input-section">
          <div className="section-header">
            <label htmlFor="url-input">YouTube Link</label>
            <button className="btn-link" onClick={handlePaste} type="button">
              Paste from Clipboard
            </button>
          </div>
          <div className="url-input-container">
            <input
              id="url-input"
              type="text"
              className="text-input"
              placeholder="Paste video or playlist link here..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={handleUrlKeyDown}
              disabled={isFetching || downloadStatus === 'downloading' || downloadStatus === 'processing'}
            />
            <button
              className="btn btn-secondary"
              onClick={handleFetchInfo}
              disabled={!url.trim() || isFetching || downloadStatus === 'downloading' || downloadStatus === 'processing'}
            >
              {isFetching ? (
                <>
                  <span className="spinner"></span> Fetching...
                </>
              ) : (
                'Fetch Info'
              )}
            </button>
          </div>
        </div>

        {/* Video Preview Card */}
        {videoTitle && (
          <div className="video-info-box">
            <div className="video-info-header">
              <span className="badge-tag">READY</span>
              <span className="video-info-label">Detected Media Title</span>
            </div>
            <div className="video-title">{videoTitle}</div>
          </div>
        )}

        {/* Media Type Tabs */}
        <div className="option-group">
          <label>Format Type</label>
          <div className="mode-switches">
            <div
              className={`mode-card ${mediaType === 'video' ? 'active' : ''}`}
              onClick={() => {
                if (downloadStatus !== 'downloading' && downloadStatus !== 'processing') {
                  setMediaType('video')
                }
              }}
            >
              <div className="mode-icon">🎬</div>
              <div>
                <div className="mode-label">Video & Audio</div>
                <div className="mode-desc">High resolution MP4 video</div>
              </div>
            </div>
            <div
              className={`mode-card ${mediaType === 'audio' ? 'active' : ''}`}
              onClick={() => {
                if (downloadStatus !== 'downloading' && downloadStatus !== 'processing') {
                  setMediaType('audio')
                }
              }}
            >
              <div className="mode-icon">🎵</div>
              <div>
                <div className="mode-label">Audio Only</div>
                <div className="mode-desc">Extract MP3, M4A, or Opus</div>
              </div>
            </div>
          </div>
        </div>

        {/* Quality / Audio Format Grid */}
        <div className="option-group">
          <label>{mediaType === 'video' ? 'Video Quality Selection' : 'Audio Format Selection'}</label>
          
          {mediaType === 'video' ? (
            <div className="quality-grid">
              <button
                type="button"
                className={`quality-chip ${quality === 'best' ? 'active' : ''}`}
                onClick={() => setQuality('best')}
                disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-title">Best Available</span>
                <span className="chip-sub">Highest Quality</span>
              </button>

              {availableHeights.map((h) => (
                <button
                  type="button"
                  key={h}
                  className={`quality-chip ${quality === String(h) ? 'active' : ''}`}
                  onClick={() => setQuality(String(h))}
                  disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
                >
                  <span className="chip-title">{h}p</span>
                  <span className="chip-sub">{h >= 1080 ? 'Full HD' : h >= 720 ? 'HD' : 'Standard'}</span>
                </button>
              ))}

              <button
                type="button"
                className={`quality-chip ${quality === 'small' ? 'active' : ''}`}
                onClick={() => setQuality('small')}
                disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-title">Smallest</span>
                <span className="chip-sub">Compact File</span>
              </button>
            </div>
          ) : (
            <div className="quality-grid">
              <button
                type="button"
                className={`quality-chip ${audioFormat === 'mp3' ? 'active' : ''}`}
                onClick={() => setAudioFormat('mp3')}
                disabled={!hasFfmpeg || downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-title">MP3</span>
                <span className="chip-sub">Universal Audio</span>
              </button>
              <button
                type="button"
                className={`quality-chip ${audioFormat === 'original' ? 'active' : ''}`}
                onClick={() => setAudioFormat('original')}
                disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-title">M4A / Original</span>
                <span className="chip-sub">Native Stream</span>
              </button>
              <button
                type="button"
                className={`quality-chip ${audioFormat === 'opus' ? 'active' : ''}`}
                onClick={() => setAudioFormat('opus')}
                disabled={!hasFfmpeg || downloadStatus === 'downloading' || downloadStatus === 'processing'}
              >
                <span className="chip-title">Opus</span>
                <span className="chip-sub">High Efficiency</span>
              </button>
            </div>
          )}
        </div>

        {/* Directory Picker */}
        <div className="input-section">
          <label htmlFor="dir-input">Destination Folder</label>
          <div className="url-input-container">
            <input
              id="dir-input"
              type="text"
              className="text-input"
              value={outputDir}
              onChange={(e) => setOutputDir(e.target.value)}
              disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
            />
            <button
              className="btn btn-secondary"
              onClick={handleBrowse}
              disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
            >
              Browse
            </button>
          </div>
        </div>

        {/* Action Button */}
        <div className="action-row">
          <button
            className="btn btn-primary btn-large"
            onClick={handleDownload}
            disabled={!fetchedUrl || downloadStatus === 'downloading' || downloadStatus === 'processing'}
          >
            Start Download
          </button>
        </div>

        {/* Progress & Toast Notification */}
        {downloadStatus && (
          <div className={`status-area ${downloadStatus}`}>
            <div className="status-header">
              <span className="status-text">{statusMessage}</span>
              {downloadStatus === 'downloading' && (
                <span className="status-stats">
                  {speed && `${speed}`} {eta && ` • ETA ${eta}`}
                </span>
              )}
            </div>
            
            <div className={`progress-track ${downloadStatus === 'processing' ? 'indeterminate' : ''}`}>
              <div
                className="progress-fill"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
