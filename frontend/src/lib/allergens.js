// Allergen wording for the ordering page (#73). The data comes from the menu
// service (#72): each ingredient has `allergens` and `allergens_checked`.

/**
 * Allergens in a set of ingredients the customer will get.
 * Unconfirmed if any of them is unchecked, or if there are none at all, as
 * then nobody has said what is in the item.
 * `order` is the allergen ids in display order (from GET /allergens/).
 */
export function summarise(ingredients, order = []) {
  const active = ingredients.filter(i => i.active !== false)
  const found = new Set(active.flatMap(i => i.allergens ?? []))
  const rank = id => (order.includes(id) ? order.indexOf(id) : order.length)
  const contains = [...found].sort((a, b) => rank(a) - rank(b))
  const confirmed = active.length > 0 && active.every(i => i.allergens_checked === true)
  return { contains, confirmed }
}

const names = (ids, labels) => ids.map(id => labels[id] ?? id).join(', ')

/** One line for customers. An unconfirmed list is never shown as complete. */
export function describeAllergens({ contains, confirmed }, labels) {
  if (!confirmed) {
    return contains.length
      ? `Allergens not confirmed. Known so far: ${names(contains, labels)}`
      : 'Allergens not confirmed'
  }
  return contains.length ? `Contains: ${names(contains, labels)}` : 'No major allergens'
}

export function describeExtras(inExtras, labels) {
  return inExtras?.length ? `Optional extras can add: ${names(inExtras, labels)}` : null
}
