"use client"

import React from "react"
import { Plus, Trash2 } from "lucide-react"

interface Variant {
  model_variant_id: string
  traffic_allocation: number
}

interface VariantConfiguratorProps {
  variants: Variant[]
  setVariants: (v: Variant[]) => void
  availableModels: any[]
}

export default function VariantConfigurator({ variants, setVariants, availableModels }: VariantConfiguratorProps) {
  const addVariant = () => {
    setVariants([...variants, { model_variant_id: "", traffic_allocation: 0 }])
  }

  const removeVariant = (idx: number) => {
    setVariants(variants.filter((_, i) => i !== idx))
  }

  const updateVariant = (idx: number, field: keyof Variant, value: string | number) => {
    const updated = [...variants]
    // @ts-ignore
    updated[idx][field] = value
    setVariants(updated)
  }

  const totalAllocation = variants.reduce((sum, v) => sum + (Number(v.traffic_allocation) || 0), 0)

  return (
    <div className="space-y-3">
      <h3 className="font-medium">Variants</h3>
      {variants.map((v, idx) => (
        <div key={idx} className="flex items-center space-x-3">
          <select
            className="select w-full max-w-xs"
            value={v.model_variant_id}
            onChange={e => updateVariant(idx, "model_variant_id", e.target.value)}
          >
            <option value="" disabled>Select Model</option>
            {availableModels.map((m: any) => (
              <option key={m.id} value={m.id}>{`${m.name} v${m.version}`}</option>
            ))}
          </select>
          <input
            type="number"
            min="0"
            max="1"
            step="0.01"
            className="input w-24"
            value={v.traffic_allocation}
            onChange={e => updateVariant(idx, "traffic_allocation", Number(e.target.value))}
          />
          <span className="text-sm">= {(Number(v.traffic_allocation) * 100).toFixed(0)}%</span>
          <button className="text-red-600" onClick={() => removeVariant(idx)}>
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ))}

      <div className="flex items-center justify-between mt-2">
        <button className="btn-secondary flex items-center" onClick={addVariant}>
          <Plus className="h-4 w-4 mr-1" /> Add Variant
        </button>
        <div className={`text-sm font-medium ${Math.abs(totalAllocation - 1) < 0.001 ? "text-green-600" : "text-red-600"}`}>
          Total: {(totalAllocation * 100).toFixed(0)}%
        </div>
      </div>
    </div>
  )
} 