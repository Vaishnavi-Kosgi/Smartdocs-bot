import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import { sendChatStream } from '../services/api'

const SUGGESTIONS = [
  '📋 Summarize this paper',
  '🔍 Explain the methodology',
  '❓ What are the key findings?',
  '📊 What dataset was used?'
]

let msgCounter = 0
const nextId = () => ++msgCounter

export default function ChatWindow({ activeDoc }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  // Reset chat when document changes
  useEffect(() => {
    setMessages([])
  }, [activeDoc?.doc_id])

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (queryText) => {
    const query = (queryText || input).trim()
    if (!query || isLoading || !activeDoc) return

    setInput('')

    // Add user message
    const userMsg = { id: nextId(), role: 'user', content: query }
    // Add AI typing placeholder
    const typingMsg = { id: nextId(), role: 'ai', isTyping: true, content: '' }

    setMessages((prev) => [...prev, userMsg, typingMsg])
    setIsLoading(true)

    try {
      let currentContent = ''

      await sendChatStream(
        activeDoc.doc_id,
        query,
        (token) => {
          currentContent += token
          setMessages((prev) =>
            prev.map((m) =>
              m.isTyping
                ? {
                  ...m,
                  content: currentContent
                }
                : m
            )
          )
        },
        (result) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.isTyping
                ? {
                  id: m.id,
                  role: 'ai',
                  content: result.answer || currentContent,
                  intent: result.intent,
                  sources: result.sources,
                  isTyping: false
                }
                : m
            )
          )
        }
      )
    } catch (err) {
      const errMsg = err?.message || 'Something went wrong. Please try again.'
      setMessages((prev) =>
        prev.map((m) =>
          m.isTyping
            ? { id: m.id, role: 'ai', content: `⚠️ ${errMsg}`, isTyping: false }
            : m
        )
      )
    } finally {
      setIsLoading(false)
      textareaRef.current?.focus()
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // ── Empty state (no active doc) ──
  if (!activeDoc) {
    return (
      <div className="chat-container">
        <div className="chat-empty">
          <span className="chat-empty-icon">🧠</span>
          <h2 className="chat-empty-title">SmartDocs AI</h2>
          <p className="chat-empty-subtitle">
            Upload a research paper on the left, then start asking questions, request summaries, or get explanations.
          </p>
        </div>
      </div>
    )
  }

  // ── Empty chat (doc selected but no messages) ──
  if (messages.length === 0) {
    return (
      <div className="chat-container">
        <div className="chat-empty">
          <span className="chat-empty-icon">💬</span>
          <h2 className="chat-empty-title">Ask about this paper</h2>
          <p className="chat-empty-subtitle">
            Try one of these or type your own question below:
          </p>
          <div className="suggestions">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                className="suggestion-chip"
                onClick={() => sendMessage(s.replace(/^[^\s]+ /, ''))}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="chat-input-area">
          <ChatInput
            input={input}
            setInput={setInput}
            onSend={sendMessage}
            onKeyDown={onKeyDown}
            isLoading={isLoading}
            textareaRef={textareaRef}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="chat-container">
      <div className="messages-list">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-area">
        <ChatInput
          input={input}
          setInput={setInput}
          onSend={sendMessage}
          onKeyDown={onKeyDown}
          isLoading={isLoading}
          textareaRef={textareaRef}
        />
      </div>
    </div>
  )
}

// ── Sub-component: input bar ──
function ChatInput({ input, setInput, onSend, onKeyDown, isLoading, textareaRef }) {
  return (
    <>
      <div className="chat-input-wrap">
        <textarea
          ref={textareaRef}
          id="chat-input"
          className="chat-textarea"
          placeholder="Ask a question, request a summary, or explain a concept…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          disabled={isLoading}
        />
        <button
          id="send-btn"
          className="send-btn"
          onClick={() => onSend()}
          disabled={!input.trim() || isLoading}
          aria-label="Send message"
        >
          {isLoading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : '➤'}
        </button>
      </div>
      <p className="chat-hint">Enter to send · Shift+Enter for new line</p>
    </>
  )
}
