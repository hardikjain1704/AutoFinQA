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
            className="w-full resize-none rounded-2xl bg-gray-100 dark:bg-bg-secondary border border-border-primary text-text-primary placeholder:text-text-secondary/60 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-accent-coral focus:border-transparent"
            disabled={disabled}
          />
        </div>
        <button
          type="submit"
          className="shrink-0 rounded-2xl bg-accent-coral text-bg-primary font-semibold px-6 py-3 shadow-lg shadow-accent-coral/20 hover:bg-accent-coral/90 transition disabled:opacity-60 disabled:cursor-not-allowed"
          disabled={disabled || !message.trim()}
        >
          {disabled ? 'Thinking…' : 'Send'}
        </button>
      </div>
    </form>
  )
}

export default MessageInput
