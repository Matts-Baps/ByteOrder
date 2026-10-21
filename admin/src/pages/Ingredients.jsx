import { useState, useEffect } from 'react'
import api from '../lib/api'

function AllergenEditor({ ingredient, allergens, onSave, onCancel }) {
  const [selected, setSelected] = useState(new Set(ingredient.allergens))
  const [checked, setChecked] = useState(ingredient.allergens_checked)

  function toggle(id) {
    const next = new Set(selected)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelected(next)
  }

  return (
    <div className="mt-3 bg-brand-50 rounded-lg p-3">
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        {allergens.map(a => (
          <label key={a.id} className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={selected.has(a.id)} onChange={() => toggle(a.id)} />
            {a.label}
          </label>
        ))}
      </div>
      <label className="mt-3 flex items-center gap-2 text-sm font-medium text-gray-800">
        <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} />
        I've checked this ingredient's allergens and the list is complete
      </label>
      <div className="mt-3 flex gap-2">
        <button
          onClick={() => onSave(allergens.map(a => a.id).filter(id => selected.has(id)), checked)}
          className="bg-brand-600 hover:bg-brand-700 text-white rounded-lg px-3 py-1 text-sm font-medium"
        >
          Save
        </button>
        <button onClick={onCancel} className="text-sm text-gray-500 hover:text-gray-800">Cancel</button>
      </div>
    </div>
  )
}

export default function Ingredients() {
  const [ingredients, setIngredients] = useState([])
  const [allergens, setAllergens] = useState([])
  const [editing, setEditing] = useState(null)
  const [newName, setNewName] = useState('')

  async function load() {
    const { data } = await api.get('/menu/ingredients')
    setIngredients(data)
  }

  useEffect(() => {
    load()
    api.get('/menu/allergens').then(({ data }) => setAllergens(data))
  }, [])

  const label = id => allergens.find(a => a.id === id)?.label ?? id
  const unchecked = ingredients.filter(i => i.active && !i.allergens_checked).length

  async function add() {
    if (!newName.trim()) return
    await api.post('/menu/ingredients', { name: newName })
    setNewName('')
    load()
  }

  async function toggle(ing) {
    // Allergen fields are left out, so the menu service keeps them as they are.
    await api.put(`/menu/ingredients/${ing.id}`, { name: ing.name, active: !ing.active })
    load()
  }

  async function saveAllergens(ing, ids, checked) {
    await api.put(`/menu/ingredients/${ing.id}`, {
      name: ing.name,
      active: ing.active,
      allergens: ids,
      allergens_checked: checked,
    })
    setEditing(null)
    load()
  }

  async function remove(ing) {
    if (!confirm(`Delete ingredient "${ing.name}"? It will be removed from all menu items.`)) return
    await api.delete(`/menu/ingredients/${ing.id}`)
    load()
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-brand-text mb-2">Ingredients</h1>
      <p className="text-sm text-gray-500 mb-4">
        Tick the allergens in each ingredient, then mark it as checked. Customers see
        "allergens not confirmed" on any item with an unchecked ingredient.
      </p>
      {unchecked > 0 && (
        <p className="mb-4 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
          {unchecked} {unchecked === 1 ? 'ingredient needs its' : 'ingredients need their'} allergens checked.
        </p>
      )}

      <div className="bg-brand-surface rounded-xl shadow divide-y">
        {ingredients.map(ing => (
          <div
            key={ing.id}
            data-testid="ingredient"
            className={`px-4 py-3 ${ing.active && !ing.allergens_checked ? 'border-l-4 border-amber-400' : ''}`}
          >
            <div className="flex items-center justify-between">
              <span className={`font-medium ${!ing.active ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                {ing.name}
              </span>
              <div className="flex gap-3">
                <button
                  onClick={() => setEditing(editing === ing.id ? null : ing.id)}
                  className="text-sm text-brand-600 hover:text-brand-700"
                >
                  Allergens
                </button>
                <button onClick={() => toggle(ing)} className="text-sm text-gray-500 hover:text-gray-800">
                  {ing.active ? 'Disable' : 'Enable'}
                </button>
                <button onClick={() => remove(ing)} className="text-sm text-red-500 hover:text-red-700">
                  Delete
                </button>
              </div>
            </div>
            <div className="mt-1 flex flex-wrap gap-1 text-xs">
              {!ing.allergens_checked && (
                <span className="rounded-full bg-amber-100 text-amber-800 px-2 py-0.5">Allergens not checked</span>
              )}
              {ing.allergens.map(id => (
                <span key={id} className="rounded-full bg-brand-100 text-gray-800 px-2 py-0.5">{label(id)}</span>
              ))}
              {ing.allergens_checked && ing.allergens.length === 0 && (
                <span className="text-gray-400">No allergens</span>
              )}
            </div>
            {editing === ing.id && (
              <AllergenEditor
                ingredient={ing}
                allergens={allergens}
                onSave={(ids, checked) => saveAllergens(ing, ids, checked)}
                onCancel={() => setEditing(null)}
              />
            )}
          </div>
        ))}
        {ingredients.length === 0 && (
          <p className="px-4 py-6 text-gray-400 text-center">No ingredients yet</p>
        )}
      </div>

      <div className="mt-4 flex gap-2">
        <input
          value={newName}
          onChange={e => setNewName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="New ingredient name"
          className="flex-1 border rounded-lg px-3 py-2"
        />
        <button
          onClick={add}
          className="bg-brand-600 hover:bg-brand-700 text-white rounded-lg px-4 py-2 font-medium"
        >
          Add
        </button>
      </div>
    </div>
  )
}
