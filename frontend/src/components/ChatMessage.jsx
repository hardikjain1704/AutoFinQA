function ChatMessage({ message }) {
  const { role, content, timestamp } = message
  const isBot = role !== 'user'

  return (
    <div className={`flex ${isBot ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-xl rounded-3xl px-5 py-3 shadow-md transition ${
          isBot
            ? 'bg-white/90 text-slate-900 shadow-blue-900/10'
            : 'bg-blue-600 text-white shadow-blue-900/20'
        }`}
      >
        <p className="whitespace-pre-line text-sm md:text-base leading-relaxed">{content}</p>
        {timestamp && (
          <span
            className={`mt-2 block text-[11px] uppercase tracking-wide ${
              isBot ? 'text-slate-500' : 'text-blue-100'
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
