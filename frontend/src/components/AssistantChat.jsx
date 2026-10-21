import { useEffect, useRef, useState } from 'react'
import { assistantApi } from '../lib/api'

// Must match the limits in assistant-service.
const MAX_MESSAGES = 20
const MAX_LENGTH = 1000

function newConversationId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `c${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`
}

function errorMessage(err) {
  if (err?.response?.status === 429) {
    return "You're sending messages too quickly. Please wait a minute and try again."
  }
  return "The assistant isn't available right now. You can still order from the menu."
}

export default function AssistantChat({ customerName, onUseDraft, onClose }) {
  const [conversationId, setConversationId] = useState(newConversationId)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState(null)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)

  const full = messages.length >= MAX_MESSAGES

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [messages, draft, error])

  async function send(e) {
    e?.preventDefault()
    const text = input.trim()
    if (!text || sending || full) return

    const history = [...messages, { role: 'user', content: text }]
    setMessages(history)
    setInput('')
    setError(null)
    setSending(true)
    try {
      const { data } = await assistantApi.post('/chat', {
        messages: history,
        customer_name: customerName,
        conversation_id: conversationId,
      })
      setMessages([...history, { role: 'assistant', content: data.reply }])
      if (data.draft) setDraft(data.draft)
    } catch (err) {
      setMessages(messages)
      setInput(text)
      setError(errorMessage(err))
    } finally {
      setSending(false)
    }
  }

  function startOver() {
    setMessages([])
    setDraft(null)
    setError(null)
    setInput('')
    setConversationId(newConversationId())
  }

  return (
    <div className="fixed inset-0 z-50 bg-brand-bg flex flex-col" role="dialog" aria-label="Ordering assistant">
      <header className="bg-brand-600 text-white px-4 py-4 flex items-center gap-3">
        <button onClick={onClose} aria-label="Close assistant" className="text-white text-xl">←</button>
        <h1 className="text-xl font-bold">Ask for help</h1>
        <button
          onClick={startOver}
          className="ml-auto bg-white text-brand-600 font-bold px-3 py-1 rounded-lg text-sm"
        >
          Start over
        </button>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-lg mx-auto px-4 py-6 space-y-3">
          {messages.length === 0 && (
            <div className="bg-brand-surface rounded-2xl shadow px-5 py-4 text-brand-text">
              <p className="font-bold mb-1">Hi {customerName}! What would you like?</p>
              <p className="text-sm text-gray-500">
                Tell me what you fancy, or anything you'd like to avoid, and I'll put an order together for you to check.
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
              <p
                className={`max-w-[85%] rounded-2xl px-4 py-3 whitespace-pre-wrap ${
                  m.role === 'user'
                    ? 'bg-brand-600 text-white'
                    : 'bg-brand-surface shadow text-brand-text'
                }`}
              >
                {m.content}
              </p>
            </div>
          ))}

          {sending && <p className="text-sm text-gray-400 px-1">Thinking…</p>}

          {draft && (
            <div className="bg-brand-surface rounded-2xl shadow border-2 border-brand-300 px-5 py-4">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-1">Suggested order</h3>
              <p className="font-bold text-brand-text mb-3">{draft.summary}</p>
              <button
                onClick={() => onUseDraft(draft.items)}
                className="w-full bg-brand-600 hover:bg-brand-700 text-white font-bold py-3 rounded-xl transition-colors"
              >
                Use this order
              </button>
              <p className="text-xs text-gray-400 mt-2">You can check and change it in your basket before ordering.</p>
            </div>
          )}

          {error && <p className="text-sm text-red-500 px-1" role="alert">{error}</p>}

          {full && (
            <p className="text-sm text-gray-500 px-1">
              This conversation is full. Press <span className="font-semibold">Start over</span> to begin a new one.
            </p>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <form onSubmit={send} className="border-t border-gray-200 bg-brand-surface">
        <div className="max-w-lg mx-auto px-4 py-3">
          <div className="flex gap-2">
            <input
              type="text"
              aria-label="Message"
              value={input}
              onChange={e => setInput(e.target.value)}
              maxLength={MAX_LENGTH}
              disabled={full}
              placeholder="e.g. something veggie, no onion"
              className="flex-1 border-2 border-gray-200 focus:border-brand-500 rounded-xl px-4 py-3 outline-none disabled:opacity-40"
            />
            <button
              type="submit"
              disabled={!input.trim() || sending || full}
              className="bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white font-bold px-5 rounded-xl transition-colors"
            >
              Send
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            The assistant can make mistakes. For allergies, please ask the kitchen staff.
          </p>
        </div>
      </form>
    </div>
  )
}
