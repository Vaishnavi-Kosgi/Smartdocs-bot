import { useState } from 'react'

export default function SourcePanel({ sources }) {
  const [open, setOpen] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div>
      <button
        className="source-toggle"
        onClick={() => setOpen(!open)}
        id="source-toggle-btn"
      >
        <span>{open ? '▾' : '▸'}</span>
        {open ? 'Hide' : 'Show'} {sources.length} source chunk{sources.length > 1 ? 's' : ''}
      </button>

      {open && (
        <div className="source-panel">
          <div className="source-panel-header">📎 Retrieved Context</div>
          {sources.map((src, i) => (
            <div className="source-chunk" key={i}>
              <div className="source-chunk-meta">
                <span className="source-chunk-badge">
                  Chunk {src.chunk_index ?? i + 1}
                  {src.page ? ` · Page ${src.page}` : ''}
                </span>
                <span className="source-score">score: {src.score?.toFixed(4) ?? '–'}</span>
              </div>
              <p className="source-chunk-text">{src.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
