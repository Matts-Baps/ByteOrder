import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('../lib/api', () => ({
  assistantApi: { post: vi.fn(), get: vi.fn() },
}))

import { assistantApi } from '../lib/api'
import AssistantChat from '../components/AssistantChat'

const DRAFT = {
  summary: 'Margherita (no Basil)',
  items: [{ menu_item_id: 4, menu_item_name: 'Margherita', ingredients: [], options: [] }],
}

function setup(props = {}) {
  const onUseDraft = vi.fn()
  const onClose = vi.fn()
  render(<AssistantChat customerName="Sam" onUseDraft={onUseDraft} onClose={onClose} {...props} />)
  return { onUseDraft, onClose, user: userEvent.setup() }
}

async function send(user, text) {
  await user.type(screen.getByLabelText('Message'), text)
  await user.click(screen.getByRole('button', { name: 'Send' }))
}

describe('AssistantChat', () => {
  beforeEach(() => vi.clearAllMocks())

  it('sends the conversation, name and a conversation id, then shows the reply', async () => {
    assistantApi.post.mockResolvedValue({ data: { reply: 'We have pizza.', draft: null } })
    const { user } = setup()

    await send(user, 'What do you have?')

    expect(await screen.findByText('We have pizza.')).toBeInTheDocument()
    expect(screen.getByText('What do you have?')).toBeInTheDocument()
    const [path, body] = assistantApi.post.mock.calls[0]
    expect(path).toBe('/chat')
    expect(body.messages).toEqual([{ role: 'user', content: 'What do you have?' }])
    expect(body.customer_name).toBe('Sam')
    expect(body.conversation_id).toMatch(/^[A-Za-z0-9_-]+$/)
  })

  it('includes earlier turns and keeps the same conversation id', async () => {
    assistantApi.post
      .mockResolvedValueOnce({ data: { reply: 'Hi Sam!', draft: null } })
      .mockResolvedValueOnce({ data: { reply: 'Sure.', draft: null } })
    const { user } = setup()

    await send(user, 'Hello')
    await screen.findByText('Hi Sam!')
    await send(user, 'A pizza please')
    await screen.findByText('Sure.')

    const first = assistantApi.post.mock.calls[0][1]
    const second = assistantApi.post.mock.calls[1][1]
    expect(second.messages).toEqual([
      { role: 'user', content: 'Hello' },
      { role: 'assistant', content: 'Hi Sam!' },
      { role: 'user', content: 'A pizza please' },
    ])
    expect(second.conversation_id).toBe(first.conversation_id)
  })

  it('offers a draft and hands its items over', async () => {
    assistantApi.post.mockResolvedValue({ data: { reply: 'Draft ready.', draft: DRAFT } })
    const { user, onUseDraft } = setup()

    await send(user, 'Margherita without basil')
    expect(await screen.findByText('Margherita (no Basil)')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Use this order' }))

    expect(onUseDraft).toHaveBeenCalledWith(DRAFT.items)
  })

  it('explains rate limiting', async () => {
    assistantApi.post.mockRejectedValue({ response: { status: 429 } })
    const { user } = setup()
    await send(user, 'Hi')
    expect(await screen.findByText(/too quickly/i)).toBeInTheDocument()
  })

  it('suggests the menu when the assistant is down, and keeps the message for retry', async () => {
    assistantApi.post.mockRejectedValue({ response: { status: 503 } })
    const { user } = setup()
    await send(user, 'Hi')
    expect(await screen.findByText(/order from the menu/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Message')).toHaveValue('Hi')
  })

  it('does not send blank messages', async () => {
    const { user } = setup()
    await user.type(screen.getByLabelText('Message'), '   ')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(assistantApi.post).not.toHaveBeenCalled()
  })

  it('limits message length', () => {
    setup()
    expect(screen.getByLabelText('Message')).toHaveAttribute('maxLength', '1000')
  })

  it('closes', async () => {
    const { user, onClose } = setup()
    await user.click(screen.getByRole('button', { name: 'Close assistant' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('starts over when the conversation is full', async () => {
    let n = 0
    assistantApi.post.mockImplementation(() => Promise.resolve({ data: { reply: `Reply ${++n}`, draft: null } }))
    const { user } = setup()
    for (let i = 0; i < 10; i++) {
      await send(user, `Message ${i}`)
      await screen.findByText(`Reply ${i + 1}`)
    }
    expect(screen.getByLabelText('Message')).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Start over' }))
    expect(screen.queryByText('Reply 1')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Message')).not.toBeDisabled()
  })
})
