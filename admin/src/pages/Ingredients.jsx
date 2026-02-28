import { useState, useEffect } from 'react'
import api from '../lib/api'

export default function Ingredients() {
  const [ingredients, setIngredients] = useState([])
  const [newName, setNewName] = useState('')

  async function load() {
    const { data } = await api.get('/menu/ingredients')
    setIngredients(data)
  }

  useEffect(() => { load() }, [])

  async function add() {
    if (!newName.trim()) return
    await api.post('/menu/ingredients', { name: newName })
    setNewName('')
    load()
  }

  async function toggle(ing) {
    await api.put(`/menu/ingredients/${ing.id}`, { name: ing.name, active: !ing.active })
    load()
  }

  async function remove(ing) {
    if (!confirm(`Delete ingredient "${ing.name}"? It will be removed from all menu items.`)) return
    await api.delete(`/menu/ingredients/${ing.id}`)
    load()
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Ingredients</h1>

      <div className="bg-white rounded-xl shadow divide-y">
        {ingredients.map(ing => (
          <div key={ing.id} className="flex items-center justify-between px-4 py-3">
            <span className={`font-medium ${!ing.active ? 'line-through text-gray-400' : 'text-gray-800'}`}>
              {ing.name}
            </span>
            <div className="flex gap-3">
              <button onClick={() => toggle(ing)} className="text-sm text-gray-500 hover:text-gray-800">
                {ing.active ? 'Disable' : 'Enable'}
              </button>
              <button onClick={() => remove(ing)} className="text-sm text-red-500 hover:text-red-700">
                Delete
              </button>
            </div>
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
