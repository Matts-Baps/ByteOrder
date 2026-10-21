import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../contexts/KitchenContext', () => ({
  useKitchen: () => ({ kitchenId: 'k', slug: null }),
}))

const ingredient = (id, name, allergens, checked = true) => ({
  id, name, active: true, allergens, allergens_checked: checked,
})

const CATEGORIES = [{
  id: 1, name: 'Burgers', items: [
    {
      id: 10, name: 'Cheeseburger', description: null,
      item_ingredients: [
        { is_default: true, ingredient: ingredient(1, 'Bun', ['gluten']) },
        { is_default: true, ingredient: ingredient(2, 'Cheese', ['milk']) },
        { is_default: false, ingredient: ingredient(3, 'Mayo', ['eggs']) },
      ],
      allergens: { contains: ['gluten', 'milk'], in_extras: ['eggs'], confirmed: true },
    },
    {
      id: 11, name: 'Mystery burger', description: null,
      item_ingredients: [
        { is_default: true, ingredient: ingredient(1, 'Bun', ['gluten']) },
        { is_default: false, ingredient: ingredient(4, 'Secret sauce', [], false) },
      ],
      allergens: { contains: ['gluten'], in_extras: [], confirmed: false },
    },
  ],
}]

const ALLERGENS = [
  { id: 'gluten', label: 'Cereals containing gluten' },
  { id: 'milk', label: 'Milk' },
  { id: 'eggs', label: 'Eggs' },
]

vi.mock('../lib/api', () => ({
  menuApi: { get: vi.fn() },
  orderApi: { post: vi.fn() },
  assistantApi: { get: vi.fn(() => Promise.reject(new Error('off'))), post: vi.fn() },
}))

import { menuApi } from '../lib/api'
import Order from '../pages/Order'

beforeEach(() => {
  vi.clearAllMocks()
  menuApi.get.mockImplementation((path) => {
    if (path.startsWith('/categories')) return Promise.resolve({ data: CATEGORIES })
    if (path.startsWith('/allergens')) return Promise.resolve({ data: ALLERGENS })
    return Promise.resolve({ data: { value: null } })
  })
})

async function openBurgers(user) {
  render(<MemoryRouter><Order /></MemoryRouter>)
  await user.type(screen.getByPlaceholderText('Your name'), 'Sam')
  await user.click(screen.getByRole('button', { name: "Let's order!" }))
  await user.click(await screen.findByRole('button', { name: /Burgers/ }))
}

describe('Order page allergens', () => {
  it('shows what each item contains and what extras add', async () => {
    const user = userEvent.setup()
    await openBurgers(user)
    const burger = screen.getByRole('button', { name: /^Cheeseburger/ })
    expect(within(burger).getByText('Contains: Cereals containing gluten, Milk')).toBeInTheDocument()
    expect(within(burger).getByText('Optional extras can add: Eggs')).toBeInTheDocument()
  })

  it('marks items with unchecked ingredients as not confirmed', async () => {
    const user = userEvent.setup()
    await openBurgers(user)
    const burger = screen.getByRole('button', { name: /^Mystery burger/ })
    expect(within(burger).getByText('Allergens not confirmed. Known so far: Cereals containing gluten')).toBeInTheDocument()
  })

  it('tells customers to ask the cook about serious allergies', async () => {
    const user = userEvent.setup()
    await openBurgers(user)
    expect(screen.getByText(/Prepared in a home kitchen\. Ask the cook if you have a serious allergy\./)).toBeInTheDocument()
  })

  it('updates the allergens as toppings change', async () => {
    const user = userEvent.setup()
    await openBurgers(user)
    await user.click(screen.getByRole('button', { name: /^Cheeseburger/ }))
    const summary = () => screen.getByTestId('allergen-summary')
    expect(summary()).toHaveTextContent('Contains: Cereals containing gluten, Milk')

    await user.click(screen.getByRole('button', { name: 'Cheese' }))
    expect(summary()).toHaveTextContent('Contains: Cereals containing gluten')
    expect(summary()).not.toHaveTextContent('Milk')

    await user.click(screen.getByRole('button', { name: 'Mayo' }))
    expect(summary()).toHaveTextContent('Contains: Cereals containing gluten, Eggs')
  })

  it('becomes confirmed once the unchecked topping is left off', async () => {
    const user = userEvent.setup()
    await openBurgers(user)
    await user.click(screen.getByRole('button', { name: /^Mystery burger/ }))
    // Secret sauce is an optional extra, so it starts off.
    expect(screen.getByTestId('allergen-summary')).toHaveTextContent('Contains: Cereals containing gluten')
    await user.click(screen.getByRole('button', { name: 'Secret sauce' }))
    expect(screen.getByTestId('allergen-summary')).toHaveTextContent('Allergens not confirmed')
  })

  it('shows allergens for each item in the basket', async () => {
    const user = userEvent.setup()
    await openBurgers(user)
    await user.click(screen.getByRole('button', { name: /^Cheeseburger/ }))
    await user.click(screen.getByRole('button', { name: 'Add to order' }))
    expect(await screen.findByText('Your order')).toBeInTheDocument()
    expect(screen.getByText('Contains: Cereals containing gluten, Milk')).toBeInTheDocument()
  })
})
