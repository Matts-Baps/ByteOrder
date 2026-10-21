import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Ingredients from './Ingredients'

vi.mock('../lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

import api from '../lib/api'

const ALLERGENS = [
  { id: 'gluten', label: 'Cereals containing gluten' },
  { id: 'milk', label: 'Milk' },
  { id: 'sesame', label: 'Sesame' },
]

let ingredients

beforeEach(() => {
  vi.clearAllMocks()
  ingredients = [
    { id: 1, name: 'Bun', active: true, allergens: ['gluten', 'sesame'], allergens_checked: true },
    { id: 2, name: 'Secret sauce', active: true, allergens: [], allergens_checked: false },
  ]
  api.get.mockImplementation((url) => {
    if (url === '/menu/ingredients') return Promise.resolve({ data: ingredients })
    if (url === '/menu/allergens') return Promise.resolve({ data: ALLERGENS })
    return Promise.reject(new Error(`Unexpected GET ${url}`))
  })
})

function row(name) {
  return screen.getByText(name).closest('[data-testid="ingredient"]')
}

describe('Ingredients allergens', () => {
  it('lists each ingredient’s allergens by label', async () => {
    render(<Ingredients />)
    await screen.findByText('Bun')
    expect(within(row('Bun')).getByText('Cereals containing gluten')).toBeInTheDocument()
    expect(within(row('Bun')).getByText('Sesame')).toBeInTheDocument()
  })

  it('flags unchecked ingredients and counts them', async () => {
    render(<Ingredients />)
    await screen.findByText('Secret sauce')
    expect(within(row('Secret sauce')).getByText('Allergens not checked')).toBeInTheDocument()
    expect(within(row('Bun')).queryByText('Allergens not checked')).not.toBeInTheDocument()
    expect(screen.getByText(/1 ingredient needs its allergens checked/i)).toBeInTheDocument()
  })

  it('says when a checked ingredient has no allergens', async () => {
    ingredients[1] = { ...ingredients[1], allergens_checked: true }
    render(<Ingredients />)
    await screen.findByText('Secret sauce')
    expect(within(row('Secret sauce')).getByText('No allergens')).toBeInTheDocument()
    expect(screen.queryByText(/needs its allergens checked/i)).not.toBeInTheDocument()
  })

  it('saves edited allergens and the checked flag', async () => {
    const user = userEvent.setup()
    render(<Ingredients />)
    await screen.findByText('Secret sauce')

    await user.click(within(row('Secret sauce')).getByRole('button', { name: 'Allergens' }))
    const r = row('Secret sauce')
    await user.click(within(r).getByLabelText('Milk'))
    await user.click(within(r).getByLabelText(/I've checked this ingredient/i))
    await user.click(within(r).getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/menu/ingredients/2', {
      name: 'Secret sauce',
      active: true,
      allergens: ['milk'],
      allergens_checked: true,
    }))
  })

  it('keeps allergens when enabling or disabling', async () => {
    const user = userEvent.setup()
    render(<Ingredients />)
    await screen.findByText('Bun')
    await user.click(within(row('Bun')).getByRole('button', { name: 'Disable' }))
    expect(api.put).toHaveBeenCalledWith('/menu/ingredients/1', { name: 'Bun', active: false })
  })
})
