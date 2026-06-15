import axios from 'axios'

const BASE_URL = '/api'

/**
 * Upload a PDF file to the backend.
 * @param {File} file
 * @param {function} onProgress - progress callback (0-100)
 */
export async function uploadPDF(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await axios.post(`${BASE_URL}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total))
      }
    }
  })
  return response.data
}

/**
 * Send a chat message for a specific document.
 * @param {string} docId
 * @param {string} query
 * @param {number} topK
 */
export async function sendChat(docId, query, topK = 5) {
  const response = await axios.post(`${BASE_URL}/chat`, {
    doc_id: docId,
    query,
    top_k: topK
  })
  return response.data
}

/**
 * Send a chat message and stream the response in real-time.
 * @param {string} docId
 * @param {string} query
 * @param {function} onToken - callback for each token (text: string) => {}
 * @param {function} onResult - callback for final result (result: object) => {}
 * @param {number} topK
 */
export async function sendChatStream(docId, query, onToken, onResult, topK = 5) {
  const response = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      doc_id: docId,
      query,
      top_k: topK
    })
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to send message')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop()

    for (const part of parts) {
      if (!part.trim()) continue

      const lines = part.split('\n')
      let event = ''
      let data = ''

      for (const line of lines) {
        if (line.startsWith('event:')) {
          event = line.substring(6).trim()
        } else if (line.startsWith('data:')) {
          data = line.substring(5).trim()
        }
      }

      if (event === 'token' && data) {
        try {
          onToken(JSON.parse(data))
        } catch (e) {
          console.error('Error parsing token:', e)
        }
      } else if (event === 'result' && data) {
        try {
          onResult(JSON.parse(data))
        } catch (e) {
          console.error('Error parsing result:', e)
        }
      } else if (event === 'error' && data) {
        try {
          throw new Error(JSON.parse(data))
        } catch (e) {
          throw new Error(data)
        }
      }
    }
  }
}

/**
 * Fetch all uploaded documents.
 */
export async function fetchDocuments() {
  const response = await axios.get(`${BASE_URL}/documents`)
  return response.data.documents
}

/**
 * Delete an uploaded document.
 * @param {string} docId
 */
export async function deleteDocument(docId) {
  const response = await axios.delete(`${BASE_URL}/documents/${docId}`)
  return response.data
}

