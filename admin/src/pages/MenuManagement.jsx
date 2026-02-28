import { useState, useEffect } from 'react'
import api from '../lib/api'

function OptionGroupsPanel({ itemId, groups, onAdd, onDelete, onAddOption, onDeleteOption }) {
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupRequired, setNewGroupRequired] = useState(false)
  const [newGroupMax, setNewGroupMax] = useState(1)
  const [newOptionName, setNewOptionName] = useState({}) // { [groupId]: string }

  function handleAddGroup(e) {
    e.preventDefault()
    if (!newGroupName.trim()) return
    onAdd(itemId, newGroupName.trim(), newGroupRequired, 0, newGroupMax)
    setNewGroupName('')
    setNewGroupRequired(false)
    setNewGroupMax(1)
  }

  function handleAddOption(e, groupId) {
    e.preventDefault()
    const name = newOptionName[groupId]?.trim()
    if (!name) return
    onAddOption(itemId, groupId, name)
    setNewOptionName(prev => ({ ...prev, [groupId]: '' }))
  }

  return (
    <div className="mt-2 space-y-3">
      {groups.map(group => (
        <div key={group.id} className="border rounded-lg p-3 bg-gray-50">
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className="text-sm font-medium text-gray-800">{group.name}</span>
              <span className="ml-2 text-xs text-gray-500">
                {group.required ? 'Required' : 'Optional'} · max {group.max_select}
              </span>
            </div>
            <button
              onClick={() => onDelete(itemId, group.id)}
              className="text-xs text-red-500 hover:text-red-700"
            >
              Delete group
            </button>
          </div>

          <div className="flex flex-wrap gap-1 mb-2">
            {group.options?.map(opt => (
              <span key={opt.id} className="inline-flex items-center gap-1 text-xs bg-white border rounded-full px-2 py-0.5">
                {opt.name}
                <button
                  onClick={() => onDeleteOption(itemId, group.id, opt.id)}
                  className="text-gray-400 hover:text-red-500 leading-none"
                >
                  ×
                </button>
              </span>
            ))}
          </div>

          <form onSubmit={e => handleAddOption(e, group.id)} className="flex gap-1">
            <input
              value={newOptionName[group.id] || ''}
              onChange={e => setNewOptionName(prev => ({ ...prev, [group.id]: e.target.value }))}
              placeholder="New option"
              className="flex-1 min-w-0 border rounded px-2 py-1 text-xs"
            />
            <button type="submit" className="bg-brand-600 text-white rounded px-2 py-1 text-xs">+</button>
          </form>
        </div>
      ))}

      <form onSubmit={handleAddGroup} className="border rounded-lg p-3 bg-white space-y-2">
        <p className="text-xs font-semibold text-gray-500">Add option group</p>
        <div className="flex gap-2">
          <input
            value={newGroupName}
            onChange={e => setNewGroupName(e.target.value)}
            placeholder="Group name (e.g. Size)"
            className="flex-1 min-w-0 border rounded px-2 py-1 text-xs"
          />
          <label className="flex items-center gap-1 text-xs">
            <input
              type="checkbox"
              checked={newGroupRequired}
              onChange={e => setNewGroupRequired(e.target.checked)}
            />
            Required
          </label>
          <label className="flex items-center gap-1 text-xs">
            Max
            <input
              type="number"
              min="1"
              value={newGroupMax}
              onChange={e => setNewGroupMax(parseInt(e.target.value) || 1)}
              className="w-12 border rounded px-1 py-1 text-xs"
            />
          </label>
          <button type="submit" className="bg-brand-600 text-white rounded px-2 py-1 text-xs">Add</button>
        </div>
      </form>
    </div>
  )
}

export default function MenuManagement() {
  const [categories, setCategories] = useState([])
  const [ingredients, setIngredients] = useState([])
  const [selected, setSelected] = useState(null) // selected category
  const [newCatName, setNewCatName] = useState('')
  const [newItemName, setNewItemName] = useState('')
  const [newItemDesc, setNewItemDesc] = useState('')
  const [expandedOptions, setExpandedOptions] = useState(new Set()) // item IDs with section open
  const [itemOptions, setItemOptions] = useState({})  // { [itemId]: [OptionGroupOut] }

  async function load() {
    const [cats, ings] = await Promise.all([
      api.get('/menu/categories?active_only=false'),
      api.get('/menu/ingredients'),
    ])
    setCategories(cats.data)
    setIngredients(ings.data)
    if (selected) {
      const fresh = cats.data.find(c => c.id === selected.id)
      setSelected(fresh || null)
    }
  }

  useEffect(() => { load() }, [])

  async function addCategory() {
    if (!newCatName.trim()) return
    await api.post('/menu/categories', { name: newCatName, sort_order: categories.length })
    setNewCatName('')
    load()
  }

  async function toggleCategory(cat) {
    await api.put(`/menu/categories/${cat.id}`, { ...cat, active: !cat.active })
    load()
  }

  async function addItem() {
    if (!newItemName.trim() || !selected) return
    await api.post('/menu/items', {
      category_id: selected.id,
      name: newItemName,
      description: newItemDesc,
      sort_order: selected.items?.length || 0,
    })
    setNewItemName('')
    setNewItemDesc('')
    load()
  }

  async function toggleItem(item) {
    await api.put(`/menu/items/${item.id}`, { ...item, active: !item.active })
    load()
  }

  async function deleteItem(item) {
    if (!confirm(`Delete "${item.name}"?`)) return
    await api.delete(`/menu/items/${item.id}`)
    load()
  }

  async function toggleIngredient(item, ingId, linked) {
    if (!linked) {
      // Not on item → add as optional topping (not pre-selected)
      await api.post(`/menu/items/${item.id}/ingredients`, { ingredient_id: ingId, is_default: false })
    } else if (!linked.is_default) {
      // Optional → make it pre-selected by default
      await api.delete(`/menu/items/${item.id}/ingredients/${ingId}`)
      await api.post(`/menu/items/${item.id}/ingredients`, { ingredient_id: ingId, is_default: true })
    } else {
      // Pre-selected default → remove from item entirely
      await api.delete(`/menu/items/${item.id}/ingredients/${ingId}`)
    }
    load()
  }

  async function loadOptionGroups(itemId) {
    const { data } = await api.get(`/menu/items/${itemId}/option-groups`)
    setItemOptions(prev => ({ ...prev, [itemId]: data }))
  }

  function toggleOptions(itemId) {
    const isOpening = !expandedOptions.has(itemId)
    setExpandedOptions(prev => {
      const next = new Set(prev)
      if (next.has(itemId)) next.delete(itemId)
      else next.add(itemId)
      return next
    })
    if (isOpening) loadOptionGroups(itemId)
  }

  async function addOptionGroup(itemId, name, required, minSelect, maxSelect) {
    await api.post(`/menu/items/${itemId}/option-groups`, {
      name, required, min_select: minSelect, max_select: maxSelect,
    })
    loadOptionGroups(itemId)
  }

  async function deleteOptionGroup(itemId, groupId) {
    await api.delete(`/menu/items/${itemId}/option-groups/${groupId}`)
    loadOptionGroups(itemId)
  }

  async function addOption(itemId, groupId, name) {
    await api.post(`/menu/items/${itemId}/option-groups/${groupId}/options`, { name })
    loadOptionGroups(itemId)
  }

  async function deleteOption(itemId, groupId, optionId) {
    await api.delete(`/menu/items/${itemId}/option-groups/${groupId}/options/${optionId}`)
    loadOptionGroups(itemId)
  }

  return (
    <div className="flex gap-6 h-full">
      {/* Categories panel */}
      <div className="w-56 shrink-0">
        <h2 className="text-lg font-bold text-brand-text mb-3">Categories</h2>
        <div className="space-y-1 mb-4">
          {categories.map(cat => (
            <div
              key={cat.id}
              className={`flex items-center justify-between rounded-lg px-3 py-2 cursor-pointer ${
                selected?.id === cat.id ? 'bg-brand-100 text-brand-800' : 'hover:bg-gray-100'
              }`}
              onClick={() => setSelected(cat)}
            >
              <span className={`text-sm font-medium ${!cat.active ? 'line-through text-gray-400' : ''}`}>
                {cat.name}
              </span>
              <button
                onClick={e => { e.stopPropagation(); toggleCategory(cat) }}
                className="text-xs text-gray-400 hover:text-gray-700"
              >
                {cat.active ? 'Hide' : 'Show'}
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-1">
          <input
            value={newCatName}
            onChange={e => setNewCatName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addCategory()}
            placeholder="New category"
            className="flex-1 min-w-0 border rounded px-2 py-1 text-sm"
          />
          <button onClick={addCategory} className="bg-brand-600 text-white rounded px-2 py-1 text-sm">+</button>
        </div>
      </div>

      {/* Items panel */}
      <div className="flex-1">
        {!selected ? (
          <p className="text-gray-400 mt-8 text-center">Select a category</p>
        ) : (
          <>
            <h2 className="text-lg font-bold text-brand-text mb-3">{selected.name} — Items</h2>
            <div className="space-y-3 mb-6">
              {selected.items?.map(item => (
                <div key={item.id} className="bg-brand-surface rounded-lg shadow p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className={`font-medium ${!item.active ? 'line-through text-gray-400' : ''}`}>
                        {item.name}
                      </span>
                      {item.description && (
                        <p className="text-xs text-gray-500">{item.description}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => toggleItem(item)} className="text-xs text-gray-500 hover:text-gray-800">
                        {item.active ? 'Hide' : 'Show'}
                      </button>
                      <button onClick={() => deleteItem(item)} className="text-xs text-red-500 hover:text-red-700">
                        Delete
                      </button>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-gray-500 mb-1">Ingredients</p>
                    <div className="flex flex-wrap gap-2 mb-1">
                      {ingredients.map(ing => {
                        const linked = item.item_ingredients?.find(ii => ii.ingredient.id === ing.id)
                        const chipClass = !linked
                          ? 'bg-white text-gray-500 border-gray-300 hover:border-brand-400'
                          : linked.is_default
                            ? 'bg-brand-600 text-white border-brand-600'
                            : 'bg-brand-50 text-brand-700 border-brand-400'
                        return (
                          <button
                            key={ing.id}
                            onClick={() => toggleIngredient(item, ing.id, linked)}
                            title={!linked ? 'Click to add as optional topping' : linked.is_default ? 'Pre-selected — click to remove' : 'Optional topping — click to make pre-selected'}
                            className={`text-xs px-2 py-1 rounded-full border transition-colors ${chipClass}`}
                          >
                            {ing.name}
                          </button>
                        )
                      })}
                    </div>
                    <p className="text-xs text-gray-400">
                      Gray = not added · <span className="text-brand-600">Outlined</span> = optional topping · <span className="text-brand-600 font-semibold">Filled</span> = pre-selected
                    </p>
                  </div>

                  <div className="mt-3 border-t pt-3">
                    <button
                      onClick={() => toggleOptions(item.id)}
                      className="text-xs font-semibold text-gray-500 hover:text-brand-600"
                    >
                      Options {expandedOptions.has(item.id) ? '▲' : '▼'}
                    </button>
                    {expandedOptions.has(item.id) && (
                      <OptionGroupsPanel
                        itemId={item.id}
                        groups={itemOptions[item.id] || []}
                        onAdd={addOptionGroup}
                        onDelete={deleteOptionGroup}
                        onAddOption={addOption}
                        onDeleteOption={deleteOption}
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-brand-surface rounded-lg shadow p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Add item to {selected.name}</h3>
              <div className="flex gap-2">
                <input
                  value={newItemName}
                  onChange={e => setNewItemName(e.target.value)}
                  placeholder="Item name"
                  className="flex-1 border rounded px-3 py-2 text-sm"
                />
                <input
                  value={newItemDesc}
                  onChange={e => setNewItemDesc(e.target.value)}
                  placeholder="Description (optional)"
                  className="flex-1 border rounded px-3 py-2 text-sm"
                />
                <button
                  onClick={addItem}
                  className="bg-brand-600 text-white rounded px-4 py-2 text-sm font-medium"
                >
                  Add
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
