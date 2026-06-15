import { useState, useRef } from 'react'
import { uploadPDF } from '../services/api'

export default function FileUpload({ onUploadSuccess }) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState(null) // null | 'loading' | 'success' | 'error'
  const [statusMsg, setStatusMsg] = useState('')
  const inputRef = useRef(null)

  const handleFile = async (file) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setStatus('error')
      setStatusMsg('Only PDF files are supported.')
      return
    }

    setStatus('loading')
    setStatusMsg(`Processing "${file.name}"…`)
    setProgress(0)

    try {
      const result = await uploadPDF(file, (pct) => setProgress(pct))
      setStatus('success')
      setStatusMsg(`✓ ${result.chunk_count} chunks indexed`)
      onUploadSuccess(result)
    } catch (err) {
      setStatus('error')
      const msg = err?.response?.data?.detail || 'Upload failed. Please try again.'
      setStatusMsg(msg)
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setIsDragOver(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  const onInputChange = (e) => {
    handleFile(e.target.files[0])
    e.target.value = ''
  }

  return (
    <div>
      <p className="section-label">Upload Paper</p>
      <div
        id="file-upload-zone"
        className={`upload-zone ${isDragOver ? 'drag-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={onInputChange}
          style={{ display: 'none' }}
          id="pdf-file-input"
        />
        <span className="upload-icon">📄</span>
        <p className="upload-text-primary">
          {isDragOver ? 'Drop your PDF here' : 'Drop PDF or click to browse'}
        </p>
        <p className="upload-text-secondary">Research papers, articles, reports</p>

        {status === 'loading' && (
          <div className="upload-progress-wrap" style={{ marginTop: 12 }}>
            <div className="upload-progress-bar" style={{ width: `${progress}%` }} />
          </div>
        )}
      </div>

      {status && (
        <p className={`upload-status ${status}`}>
          {status === 'loading' && <span className="spinner" />}
          {statusMsg}
        </p>
      )}
    </div>
  )
}
