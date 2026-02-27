import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { menuApi, orderApi } from '../lib/api'

const STEPS = { NAME: 'name', CATEGORY: 'category', ITEM: 'item', CUSTOMISE: 'customise', BASKET: 'basket', CONFIRM: 'confirm' }

export default function Order() {
  const navigate = useNavigate()
  const [step, setStep] = useState(STEPS.NAME)
  const [name, setName] = useState('')
  const [categories, setCategories] = useState([])
  const [selectedCat, setSelectedCat] = useState(null)
  const [selectedItem, setSelectedItem] = useState(null)
  const [customIngredients, setCustomIngredients] = useState({}) // ingredient_id -> included bool
  const [basket, setBasket] = useState([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    menuApi.get('/categories/').then(({ data }) => setCategories(data))
  }, [])

  function startCustomise(item) {
    setSelectedItem(item)
    const defaults = {}
    item.item_ingredients.forEach(ii => {
      defaults[ii.ingredient.id] = { name: ii.ingredient.name, included: ii.is_default }
    })
    setCustomIngredients(defaults)
    setStep(STEPS.CUSTOMISE)
  }

  function addToBasket() {
    const ing = Object.entries(customIngredients).map(([id, v]) => ({
      ingredient_id: parseInt(id),
      ingredient_name: v.name,
      included: v.included,
    }))
    setBasket(prev => [...prev, {
      menu_item_id: selectedItem.id,
      menu_item_name: selectedItem.name,
      ingredients: ing,
      options: [],
    }])
    setStep(STEPS.BASKET)
  }

  function removeFromBasket(idx) {
    setBasket(prev => prev.filter((_, i) => i !== idx))
  }

  async function placeOrder() {
    if (basket.length === 0) return
    setSubmitting(true)
    try {
      const { data } = await orderApi.post('/orders/', { customer_name: name, items: basket })
      navigate(`/track/${data.id}`)
    } catch (err) {
      alert('Failed to place order. Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-orange-600 text-white px-4 py-4 flex items-center gap-3">
        {step !== STEPS.NAME && (
          <button onClick={() => {
            if (step === STEPS.CATEGORY) setStep(STEPS.NAME)
            else if (step === STEPS.ITEM) setStep(STEPS.CATEGORY)
            else if (step === STEPS.CUSTOMISE) setStep(STEPS.ITEM)
            else if (step === STEPS.BASKET) setStep(STEPS.CATEGORY)
          }} className="text-white text-xl">←</button>
        )}
        <h1 className="text-xl font-bold">ByteOrder</h1>
        {basket.length > 0 && step !== STEPS.BASKET && (
          <button
            onClick={() => setStep(STEPS.BASKET)}
            className="ml-auto bg-white text-orange-600 font-bold px-3 py-1 rounded-lg text-sm"
          >
            Basket ({basket.length})
          </button>
        )}
      </header>

      <div className="max-w-lg mx-auto px-4 py-6">

        {/* Step: Enter name */}
        {step === STEPS.NAME && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-1">What's your name?</h2>
            <p className="text-gray-500 mb-6">So we can call you when your order is ready</p>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && name.trim() && setStep(STEPS.CATEGORY)}
              placeholder="Your name"
              autoFocus
              className="w-full border-2 border-gray-200 focus:border-orange-500 rounded-xl px-4 py-3 text-lg outline-none mb-4"
            />
            <button
              onClick={() => setStep(STEPS.CATEGORY)}
              disabled={!name.trim()}
              className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-40 text-white font-bold py-3 rounded-xl text-lg transition-colors"
            >
              Let's order!
            </button>
          </div>
        )}

        {/* Step: Choose category */}
        {step === STEPS.CATEGORY && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Hi {name}! What are you having?</h2>
            <div className="grid grid-cols-2 gap-3">
              {categories.map(cat => (
                <button
                  key={cat.id}
                  onClick={() => { setSelectedCat(cat); setStep(STEPS.ITEM) }}
                  className="bg-white rounded-2xl shadow p-6 text-left hover:shadow-md hover:border-orange-300 border-2 border-transparent transition-all"
                >
                  <p className="font-bold text-gray-900 text-lg">{cat.name}</p>
                  {cat.description && <p className="text-gray-500 text-sm mt-1">{cat.description}</p>}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step: Choose item */}
        {step === STEPS.ITEM && selectedCat && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">{selectedCat.name}</h2>
            <div className="space-y-3">
              {selectedCat.items?.map(item => (
                <button
                  key={item.id}
                  onClick={() => startCustomise(item)}
                  className="w-full bg-white rounded-2xl shadow px-5 py-4 text-left hover:shadow-md border-2 border-transparent hover:border-orange-300 transition-all"
                >
                  <p className="font-bold text-gray-900 text-lg">{item.name}</p>
                  {item.description && <p className="text-gray-500 text-sm mt-0.5">{item.description}</p>}
                  {item.item_ingredients?.length > 0 && (
                    <p className="text-xs text-gray-400 mt-1">
                      {item.item_ingredients.filter(ii => ii.is_default).map(ii => ii.ingredient.name).join(', ')}
                    </p>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step: Customise */}
        {step === STEPS.CUSTOMISE && selectedItem && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-1">{selectedItem.name}</h2>
            <p className="text-gray-500 mb-6">Tap ingredients to add or remove them</p>

            <div className="bg-white rounded-2xl shadow p-5 mb-6">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Ingredients</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(customIngredients).map(([id, { name: ingName, included }]) => (
                  <button
                    key={id}
                    onClick={() => setCustomIngredients(prev => ({
                      ...prev,
                      [id]: { ...prev[id], included: !included },
                    }))}
                    className={`px-4 py-2 rounded-full font-medium text-sm border-2 transition-all ${
                      included
                        ? 'bg-orange-600 border-orange-600 text-white'
                        : 'bg-white border-gray-300 text-gray-400 line-through'
                    }`}
                  >
                    {ingName}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={addToBasket}
              className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold py-3 rounded-xl text-lg transition-colors"
            >
              Add to order
            </button>
          </div>
        )}

        {/* Step: Basket */}
        {step === STEPS.BASKET && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Your order</h2>

            {basket.length === 0 ? (
              <p className="text-gray-400 text-center py-8">Your basket is empty</p>
            ) : (
              <div className="space-y-3 mb-6">
                {basket.map((item, i) => (
                  <div key={i} className="bg-white rounded-2xl shadow px-5 py-4">
                    <div className="flex justify-between items-start">
                      <p className="font-bold text-gray-900">{item.menu_item_name}</p>
                      <button onClick={() => removeFromBasket(i)} className="text-red-400 text-sm hover:text-red-600">
                        Remove
                      </button>
                    </div>
                    {item.ingredients.filter(i => i.included).length > 0 && (
                      <p className="text-sm text-gray-500 mt-1">
                        With: {item.ingredients.filter(i => i.included).map(i => i.ingredient_name).join(', ')}
                      </p>
                    )}
                    {item.ingredients.filter(i => !i.included).length > 0 && (
                      <p className="text-sm text-red-400 mt-0.5">
                        No: {item.ingredients.filter(i => !i.included).map(i => i.ingredient_name).join(', ')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setStep(STEPS.CATEGORY)}
                className="flex-1 bg-white border-2 border-orange-200 text-orange-600 font-bold py-3 rounded-xl transition-colors hover:bg-orange-50"
              >
                Add more
              </button>
              <button
                onClick={placeOrder}
                disabled={basket.length === 0 || submitting}
                className="flex-1 bg-orange-600 hover:bg-orange-700 disabled:opacity-40 text-white font-bold py-3 rounded-xl transition-colors"
              >
                {submitting ? 'Placing…' : 'Place Order'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
