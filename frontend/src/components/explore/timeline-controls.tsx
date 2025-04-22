"use client"

import { useState } from 'react'

type TimelineControlsProps = {
  onFetch: (params: any) => void;
}

export default function TimelineControls({ onFetch }: TimelineControlsProps) {
  const [formState, setFormState] = useState({
    limit: 20,
    strategy: 'uniform',
    injectionRate: 0.2,
    minInjections: 2,
    startPosition: 5,
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    let parsedValue: string | number = value
    
    if (type === 'number') {
      parsedValue = parseFloat(value)
    }
    
    setFormState(prev => ({
      ...prev,
      [name]: parsedValue
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onFetch(formState)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">
          Injection Strategy
        </label>
        <select
          name="strategy"
          value={formState.strategy}
          onChange={handleChange}
          className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
        >
          <option value="uniform">Uniform</option>
          <option value="tag_match">Tag Matching</option>
          <option value="first_only">First Position Only</option>
          <option value="after_n">After N Posts</option>
        </select>
        <p className="mt-1 text-xs text-neutral-500">
          {formState.strategy === 'uniform' && 'Recommended posts are distributed evenly throughout the timeline.'}
          {formState.strategy === 'tag_match' && 'Recommendations are injected after posts with matching tags.'}
          {formState.strategy === 'first_only' && 'A single recommendation is placed at the beginning of the timeline.'}
          {formState.strategy === 'after_n' && 'Recommendation is injected after the Nth post.'}
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">
          Timeline Limit
        </label>
        <input
          type="number"
          name="limit"
          min="5"
          max="40"
          value={formState.limit}
          onChange={handleChange}
          className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
        />
      </div>

      {formState.strategy === 'uniform' && (
        <div>
          <label className="block text-sm font-medium mb-1">
            Injection Rate
          </label>
          <input
            type="number"
            name="injectionRate"
            min="0.05"
            max="0.5"
            step="0.05"
            value={formState.injectionRate}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
          />
          <p className="mt-1 text-xs text-neutral-500">
            Percentage of timeline posts that will be recommendations (5-50%)
          </p>
        </div>
      )}

      {formState.strategy === 'uniform' && (
        <div>
          <label className="block text-sm font-medium mb-1">
            Minimum Injections
          </label>
          <input
            type="number"
            name="minInjections"
            min="1"
            max="10"
            value={formState.minInjections}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
          />
        </div>
      )}

      {formState.strategy === 'after_n' && (
        <div>
          <label className="block text-sm font-medium mb-1">
            Start Position
          </label>
          <input
            type="number"
            name="startPosition"
            min="1"
            max="20"
            value={formState.startPosition}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
          />
          <p className="mt-1 text-xs text-neutral-500">
            Position after which to inject the recommendation
          </p>
        </div>
      )}

      <button
        type="submit"
        className="w-full btn-primary py-2"
      >
        Fetch Timeline
      </button>
    </form>
  )
}