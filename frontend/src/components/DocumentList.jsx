export default function DocumentList({ documents, activeDocId, onSelect, onDelete }) {
  return (
    <div>
      <p className="section-label">Documents ({documents.length})</p>
      {documents.length === 0 ? (
        <p className="doc-empty">No documents yet. Upload a PDF to get started.</p>
      ) : (
        <div className="doc-list">
          {documents.map((doc) => (
            <div
              key={doc.doc_id}
              id={`doc-item-${doc.doc_id}`}
              className={`doc-item ${activeDocId === doc.doc_id ? 'active' : ''}`}
              onClick={() => onSelect(doc)}
              title={doc.filename}
            >
              <span className="doc-item-icon">📑</span>
              <div className="doc-item-info">
                <p className="doc-item-name">{doc.filename || `Document ${doc.doc_id}`}</p>
                <p className="doc-item-meta">
                  {doc.chunk_count != null ? `${doc.chunk_count} chunks` : 'Ready'} · ID: {doc.doc_id}
                </p>
              </div>
              <button
                className="doc-delete-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  if (confirm(`Are you sure you want to delete "${doc.filename}"?`)) {
                    onDelete(doc.doc_id)
                  }
                }}
                title="Delete document"
                aria-label="Delete document"
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

