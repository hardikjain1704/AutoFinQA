import { useState } from 'react'

function MessageInput({ onSend, disabled }) {
  const [message, setMessage] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()
    if (!message.trim() || disabled) return

    onSend(message.trim())
    setMessage('')
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit(event)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="px-6 pb-6">
      <div className="flex items-start gap-4">
        <div className="flex-1">
            <label htmlFor="chat-input" className="sr-only">
            Ask a financial question
            </label>
            <textarea
                id="chat-input"
                rows={1}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about revenue trends, margins, risks..."
                className="w-full resize-none rounded-2xl bg-slate-900/60 border border-white/10 text-white placeholder:text-slate-400 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent"
                disabled={disabled}
            />
        </div>
            <button
                type="submit"
                className="shrink-0 rounded-2xl bg-emerald-400 text-slate-900 font-semibold px-6 py-3 shadow-lg shadow-emerald-900/40 hover:bg-emerald-300 transition disabled:opacity-60 disabled:cursor-not-allowed"
                disabled={disabled || !message.trim()}
            >
                {disabled ? 'Thinking…' : 'Send'}
            </button>
      </div>
    </form>
  )
}

export default MessageInput
