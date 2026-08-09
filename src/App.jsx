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
    // Check FFmpeg and get default directory on load
    if (window.api) {
      window.api.hasFfmpeg().then(setHasFfmpeg)
      window.api.getDefaultDownloadDir().then(setOutputDir)
      
      // Wire up IPC event listeners
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
        setStatusMessage(`Download complete! Saved to folder: ${data.dest}`)
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
    setVideoTitle('Loading video details...')
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
        setQuality('best') // Default to best available
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
      alert('The URL has changed. Please click "Fetch Info" first to load the correct qualities.')
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

  return (
    <div className="app-container">
      <header>
        <div className="logo-container">
          <div className="logo-icon">⬇</div>
          <div>
            <h1>YT Downloader</h1>
            <p className="subtitle">High-fidelity media downloading utility</p>
          </div>
        </div>
        <div>
          {hasFfmpeg ? (
            <span className="ffmpeg-badge">
              <span>●</span> FFmpeg Available (Merging Active)
            </span>
          ) : (
            <span className="ffmpeg-badge missing">
              <span>●</span> FFmpeg Missing (Restricted to 360p)
            </span>
          )}
        </div>
      </header>

      <main className="dashboard-card">
        {/* YouTube URL input card */}
        <div className="input-section">
          <label htmlFor="url-input">YouTube Video or Playlist URL</label>
          <div className="url-input-container">
            <input
              id="url-input"
              type="text"
              className="text-input"
              placeholder="https://www.youtube.com/watch?v=..."
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
              {isFetching ? 'Fetching...' : 'Fetch Info'}
            </button>
          </div>
        </div>

        {/* Video Title Details Panel */}
        {videoTitle && (
          <div className="video-info-box">
            <div className="video-info-label">Active Video</div>
            <div className="video-title">{videoTitle}</div>
          </div>
        )}

        {/* Mode & Options Grid */}
        <div className="options-grid">
          <div className="option-group">
            <label>Download Mode</label>
            <div className="mode-switches">
              <div
                className={`mode-card ${mediaType === 'video' ? 'active' : ''}`}
                onClick={() => {
                  if (downloadStatus !== 'downloading' && downloadStatus !== 'processing') {
                    setMediaType('video')
                  }
                }}
              >
                <div className="mode-bullet"></div>
                <div className="mode-label">Video & Audio</div>
              </div>
              <div
                className={`mode-card ${mediaType === 'audio' ? 'active' : ''}`}
                onClick={() => {
                  if (downloadStatus !== 'downloading' && downloadStatus !== 'processing') {
                    setMediaType('audio')
                  }
                }}
              >
                <div className="mode-bullet"></div>
                <div className="mode-label">Audio Only</div>
              </div>
            </div>
          </div>

          <div className="option-group">
            {mediaType === 'video' ? (
              <>
                <label htmlFor="quality-select">Preferred Quality</label>
                <div className="select-wrapper">
                  <select
                    id="quality-select"
                    className="custom-select"
                    value={quality}
                    onChange={(e) => setQuality(e.target.value)}
                    disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
                  >
                    <option value="best">Best available quality</option>
                    {availableHeights.map((h) => (
                      <option key={h} value={h}>
                        {h}p
                      </option>
                    ))}
                    <option value="small">Smallest file size</option>
                  </select>
                </div>
              </>
            ) : (
              <>
                <label htmlFor="audio-format-select">Audio Format</label>
                <div className="select-wrapper">
                  <select
                    id="audio-format-select"
                    className="custom-select"
                    value={audioFormat}
                    onChange={(e) => setAudioFormat(e.target.value)}
                    disabled={downloadStatus === 'downloading' || downloadStatus === 'processing'}
                  >
                    <option value="original">Original / M4A (No merging)</option>
                    <option value="mp3" disabled={!hasFfmpeg}>
                      MP3 (Requires FFmpeg)
                    </option>
                    <option value="opus" disabled={!hasFfmpeg}>
                      Opus (Requires FFmpeg)
                    </option>
                  </select>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Directory selection card */}
        <div className="input-section">
          <label htmlFor="dir-input">Save Directory</label>
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

        {/* Download Action Bar */}
        <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            className="btn btn-primary"
            style={{ minWidth: '160px', padding: '14px 30px', fontSize: '15px' }}
            onClick={handleDownload}
            disabled={!fetchedUrl || downloadStatus === 'downloading' || downloadStatus === 'processing'}
          >
            Download
          </button>
        </div>

        {/* Dynamic progress panel */}
        {downloadStatus && (
          <div className="status-area">
            <div className="status-header">
              <span className="status-text">{statusMessage}</span>
              {downloadStatus === 'downloading' && (
                <span className="status-stats">
                  {speed && `${speed} • `} {eta && `ETA ${eta}`}
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
