import { useState, useEffect } from 'react'
import FileUpload from './components/FileUpload'
import DocumentList from './components/DocumentList'
import ChatWindow from './components/ChatWindow'
import { fetchDocuments, deleteDocument } from './services/api'

export default function App() {
  const [documents, setDocuments] = useState([])
  const [activeDoc, setActiveDoc] = useState(null)

  // Load existing documents on mount
  useEffect(() => {
    fetchDocuments()
      .then((docs) => setDocuments(docs || []))
      .catch(() => {}) // backend may not be running yet
  }, [])

  const handleUploadSuccess = (result) => {
    const newDoc = {
      doc_id: result.doc_id,
      filename: result.filename,
      chunk_count: result.chunk_count
    }
    setDocuments((prev) => {
      // Avoid duplicates
      const filtered = prev.filter((d) => d.doc_id !== newDoc.doc_id)
      return [newDoc, ...filtered]
    })
    setActiveDoc(newDoc)
  }

  const handleDocSelect = (doc) => {
    setActiveDoc(doc)
  }

  const handleDeleteDocument = (docId) => {
    deleteDocument(docId)
      .then(() => {
        setDocuments((prev) => prev.filter((d) => d.doc_id !== docId))
        if (activeDoc?.doc_id === docId) {
          setActiveDoc(null)
        }
      })
      .catch((err) => {
        alert(err?.message || 'Failed to delete document')
      })
  }

  return (
    <div className="app-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-icon">🧠</div>
            <span className="brand-name">SmartDocs AI</span>
          </div>
          <p className="brand-tagline">Research Paper Assistant</p>
        </div>

        <div className="sidebar-content">
          <FileUpload onUploadSuccess={handleUploadSuccess} />
          <DocumentList
            documents={documents}
            activeDocId={activeDoc?.doc_id}
            onSelect={handleDocSelect}
            onDelete={handleDeleteDocument}
          />
        </div>
      </aside>

      {/* ── Main Chat Area ── */}
      <main className="main-area">
        {/* Top Bar */}
        <header className="topbar">
          <div className="topbar-doc">
            <span className="topbar-doc-icon">
              {activeDoc ? '📑' : '🔬'}
            </span>
            <div>
              <p className="topbar-doc-name">
                {activeDoc ? activeDoc.filename : 'No document selected'}
              </p>
              <p className="topbar-doc-hint">
                {activeDoc
                  ? `${activeDoc.chunk_count ?? '?'} chunks · RAG + Gemini 1.5 Flash`
                  : 'Upload a PDF to begin'}
              </p>
            </div>
          </div>

        </header>

        {/* Chat */}
        <ChatWindow activeDoc={activeDoc} />
      </main>
    </div>
  )
}
