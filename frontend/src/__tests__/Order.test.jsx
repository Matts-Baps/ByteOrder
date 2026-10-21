import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../contexts/KitchenContext', () => ({
  useKitchen: () => ({ kitchenId: 'k', slug: null }),
}))

vi.mock('../lib/api', () => ({
  menuApi: {
    get: vi.fn((path) =>
      Promise.resolve({ data: path.startsWith('/categories') ? [] : { value: null } })
    ),
  },
  orderApi: { post: vi.fn() },
  assistantApi: { get: vi.fn(), post: vi.fn() },
}))

import { assistantApi } from '../lib/api'
import Order from '../pages/Order'

const DRAFT = {
  summary: 'Cola',
  items: [{ menu_item_id: 9, menu_item_name: 'Cola', ingredients: [], options: [] }],
}

async function startOrder(user) {
  render(<MemoryRouter><Order /></MemoryRouter>)
  await user.type(screen.getByPlaceholderText('Your name'), 'Sam')
  await user.click(screen.getByRole('button', { name: "Let's order!" }))
}

describe('Order page assistant', () => {
  beforeEach(() => vi.clearAllMocks())

  it('hides the assistant when the service is not available', async () => {
    assistantApi.get.mockRejectedValue(new Error('404'))
    const user = userEvent.setup()
    await startOrder(user)
    expect(screen.queryByRole('button', { name: 'Ask for help' })).not.toBeInTheDocument()
  })

  it('puts the draft in the basket for the customer to confirm', async () => {
    assistantApi.get.mockResolvedValue({ data: { status: 'ok' } })
    assistantApi.post.mockResolvedValue({ data: { reply: 'One cola.', draft: DRAFT } })
    const user = userEvent.setup()
    await startOrder(user)

    await user.click(await screen.findByRole('button', { name: 'Ask for help' }))
    await user.type(screen.getByLabelText('Message'), 'A cola')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await user.click(await screen.findByRole('button', { name: 'Use this order' }))

    expect(screen.getByText('Your order')).toBeInTheDocument()
    expect(screen.getByText('Cola')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Place Order' })).toBeEnabled()
    expect(assistantApi.post.mock.calls[0][1].customer_name).toBe('Sam')
  })
})
