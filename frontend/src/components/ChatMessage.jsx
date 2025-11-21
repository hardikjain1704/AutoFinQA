function ChatMessage({ message }) {
  const { role, content, timestamp } = message
  const isBot = role !== 'user'

  return (
    <div className={`flex ${isBot ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-xl px-5 py-3 transition ${isBot
            ? 'text-text-primary'
            : 'text-accent-coral'
          }`}
      >
        <p className="whitespace-pre-line text-sm md:text-base leading-relaxed">{content}</p>
        {timestamp && (
          <span
            className={`mt-2 block text-[11px] uppercase tracking-wide ${isBot ? 'text-text-secondary' : 'text-text-secondary/80'
              }`}
          >
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  )
}

export default ChatMessage
