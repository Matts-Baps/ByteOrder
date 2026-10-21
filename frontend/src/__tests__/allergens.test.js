import { describe, it, expect } from 'vitest'
import { summarise, describeAllergens } from '../lib/allergens'

const LABELS = { gluten: 'Cereals containing gluten', milk: 'Milk', eggs: 'Eggs' }
const ing = (allergens, checked = true, active = true) => ({ allergens, allergens_checked: checked, active })

describe('summarise', () => {
  it('collects allergens from the ingredients, without duplicates', () => {
    expect(summarise([ing(['gluten', 'milk']), ing(['milk'])])).toEqual({
      contains: ['gluten', 'milk'], confirmed: true,
    })
  })

  it('is unconfirmed if any ingredient is unchecked', () => {
    expect(summarise([ing(['gluten']), ing([], false)]).confirmed).toBe(false)
  })

  it('is unconfirmed with no ingredients', () => {
    expect(summarise([])).toEqual({ contains: [], confirmed: false })
  })

  it('ignores inactive ingredients', () => {
    expect(summarise([ing(['gluten']), ing(['eggs'], false, false)])).toEqual({
      contains: ['gluten'], confirmed: true,
    })
  })

  it('copes with ingredients that have no allergen fields', () => {
    expect(summarise([{ active: true }])).toEqual({ contains: [], confirmed: false })
  })
})

describe('describeAllergens', () => {
  it('lists what a confirmed item contains', () => {
    expect(describeAllergens({ contains: ['gluten', 'milk'], confirmed: true }, LABELS))
      .toBe('Contains: Cereals containing gluten, Milk')
  })

  it('says when a confirmed item has none', () => {
    expect(describeAllergens({ contains: [], confirmed: true }, LABELS)).toBe('No major allergens')
  })

  it('never presents an unconfirmed list as complete', () => {
    expect(describeAllergens({ contains: [], confirmed: false }, LABELS)).toBe('Allergens not confirmed')
    expect(describeAllergens({ contains: ['gluten'], confirmed: false }, LABELS))
      .toBe('Allergens not confirmed. Known so far: Cereals containing gluten')
  })

  it('falls back to the id when a label is missing', () => {
    expect(describeAllergens({ contains: ['lupin'], confirmed: true }, {})).toBe('Contains: lupin')
  })
})
