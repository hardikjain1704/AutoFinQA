import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import ChatMessage from '../components/ChatMessage'
import MessageInput from '../components/MessageInput'
import { chatService } from '../services/chatService'

function ChatPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { uploadedFileName, uploadResponse } = location.state || {}
  const [messages, setMessages] = useState(() => [
    {
      id: 'welcome',
      role: 'assistant',
      content: "Welcome to AutoFinQA. Ask me anything about your financial documents, and I'll break it down for you.",
      timestamp: new Date().toISOString()
    }
  ])
  const [isThinking, setIsThinking] = useState(false)
  const [error, setError] = useState('')

  const uploadSummary = useMemo(() => {
    if (!uploadedFileName) return null

    const size = uploadResponse?.size
      ? `${(uploadResponse.size / (1024 * 1024)).toFixed(2)} MB`
      : null

    return `I've ingested “${uploadedFileName}”${size ? ` (${size})` : ''}. What would you like to explore first?`
  }, [uploadedFileName, uploadResponse])

  useEffect(() => {
    if (!uploadedFileName) {
      return
    }

    setMessages((prev) => [
      ...prev,
      {
        id: `upload-${Date.now()}`,
        role: 'assistant',
        content: uploadSummary,
        timestamp: new Date().toISOString()
      }
    ])
  }, [uploadedFileName, uploadSummary])

  const handleSendMessage = async (content) => {
    setError('')

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }

    setMessages((prev) => [...prev, userMessage])
    setIsThinking(true)

    try {
      const response = await chatService.sendMessage(content, {
        source: uploadedFileName || 'manual-query'
      })

      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response?.answer || response?.message || 'I successfully received your question, but the backend did not return an answer yet.',
        timestamp: new Date().toISOString()
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      console.error('Chat error:', err)
      const assistantMessage = {
        id: `assistant-error-${Date.now()}`,
        role: 'assistant',
        content: err.message || 'I hit a snag reaching the backend. Please verify the server is running and try again.',
        timestamp: new Date().toISOString()
      }
      setMessages((prev) => [...prev, assistantMessage])
      setError(err.message ?? 'Unable to reach the AutoFinQA backend.')
    } finally {
      setIsThinking(false)
    }
  }

  const handleUploadAnother = () => {
    navigate('/', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="relative mx-auto max-w-5xl pt-12 pb-24 px-4 sm:px-6">
        <div className="flex justify-between items-start gap-4 mb-8">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-emerald-300/80">AutoFinQA Chat</p>
            <h1 className="mt-2 text-3xl md:text-4xl font-semibold text-white">Ask questions about your financial data</h1>
            <p className="mt-3 text-slate-400 max-w-2xl">
              Dive into ratios, segment trends, risk disclosures, or forecasts. I can connect insights back to the document you just uploaded.
            </p>
          </div>
          <button
            type="button"
            onClick={handleUploadAnother}
            className="rounded-full border border-emerald-400/60 bg-emerald-400/10 text-emerald-200 px-4 py-2 text-sm font-medium hover:bg-emerald-400/20 transition"
          >
            Upload another file
          </button>
        </div>

        <div className="backdrop-blur-xl bg-slate-900/60 border border-slate-800/60 rounded-3xl shadow-2xl overflow-hidden">
          <div className="max-h-[60vh] overflow-y-auto px-6 pt-8 pb-4 space-y-6">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isThinking && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1 bg-white/10 border border-white/10 rounded-full px-4 py-2 text-[13px] text-slate-200">
                  <span className="w-2 h-2 rounded-full bg-emerald-300 animate-bounce" />
                  <span className="w-2 h-2 rounded-full bg-emerald-300 animate-bounce [animation-delay:120ms]" />
                  <span className="w-2 h-2 rounded-full bg-emerald-300 animate-bounce [animation-delay:240ms]" />
                  <span className="ml-3">Analyzing…</span>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="px-6">
              <div className="mb-4 rounded-2xl border border-rose-400/60 bg-rose-500/20 px-4 py-3 text-sm text-rose-100">
                {error}
              </div>
            </div>
          )}

          <MessageInput onSend={handleSendMessage} disabled={isThinking} />
        </div>
      </div>
    </div>
  )
}

export default ChatPage
