import React, { useState, useRef, useEffect } from 'react'
import { HeroHighlight, Highlight } from '../components/HeroHighlight'
import { motion } from 'framer-motion'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

async function streamQuery(
  question: string,
  onChunk: (chunk: string) => void,
): Promise<void> {
  const res = await fetch('/api/v1/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      filters: {},
      use_grounding: false,
      stream: true,
    }),
  })

  if (!res.body) return

  const reader = res.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value)
    const lines = text.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ') && !line.includes('[DONE]')) {
        try {
          const payload = JSON.parse(line.slice(6))
          if (payload.chunk) {
            onChunk(payload.chunk as string)
          }
        } catch {
          // ignore bad chunk
        }
      }
    }
  }
}

export default function ChatbotPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  // auto-scroll to bottom on new messages
  useEffect(() => {
    const el = containerRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || isLoading) return

    setInput('')
    setIsLoading(true)

    // add user message + empty assistant message
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: question },
      { role: 'assistant', content: '' },
    ])

    try {
      await streamQuery(question, (chunk) => {
        setMessages((prev) => {
          if (prev.length === 0) return prev
          const updated = [...prev]
          const lastIndex = updated.length - 1
          const last = updated[lastIndex]

          if (last.role !== 'assistant') {
            // safety: if last is not assistant, append a new one
            updated.push({ role: 'assistant', content: chunk })
          } else {
            updated[lastIndex] = {
              ...last,
              content: last.content + chunk,
            }
          }

          return updated
        })
      })
    } catch (err) {
      console.error('Chatbot query failed', err)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, the authority chatbot could not respond right now.',
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="p-6 h-full flex flex-col max-h-screen">
      <div className="rounded-2xl overflow-hidden mb-4 shrink-0 shadow-xl">
        <HeroHighlight containerClassName="h-60 bg-black">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: [20, -5, 0] }}
            transition={{ duration: 0.5, ease: [0.4, 0.0, 0.2, 1] }}
            className="text-2xl md:text-3xl lg:text-4xl font-bold text-white max-w-3xl leading-relaxed text-left px-8"
          >
            <Highlight className="text-white">
              Authority AI
            </Highlight>{' '}
            Instant insights and <span className="text-indigo-400">grounded analysis</span> of crisis data.
          </motion.h1>
        </HeroHighlight>
      </div>

      <h2 className="text-xl font-semibold mb-4">Chat Assistant</h2>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto bg-white rounded-lg shadow p-4 space-y-3 mb-4"
      >
        {messages.length === 0 && (
          <div className="text-sm text-slate-500 text-center mt-10">
            Ask questions like: &quot;Fires in Mumbai last hour?&quot; or
            &quot;High severity incidents today?&quot;
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[70%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-900'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 border border-slate-300 rounded px-3 py-2 text-sm"
          placeholder="Ask about incidents, e.g. 'How many fires in Mumbai last hour?'"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={isLoading}
          className={`px-4 py-2 rounded text-sm font-medium ${
            isLoading
              ? 'bg-slate-300 text-slate-600 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {isLoading ? 'Streaming...' : 'Send'}
        </button>
      </div>
    </div>
  )
}