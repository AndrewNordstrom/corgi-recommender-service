"use client"

import React, { useState, useEffect } from "react"
import { X, Plus, Trash2 } from "lucide-react"
import VariantConfigurator from "./VariantConfigurator"

interface ExperimentCreationModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated?: () => void // callback to refresh list after creation
}

export default function ExperimentCreationModal({ isOpen, onClose, onCreated }: ExperimentCreationModalProps) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [variants, setVariants] = useState<Array<{ model_variant_id: string; traffic_allocation: number }>>([
    { model_variant_id: "", traffic_allocation: 0.5 },
    { model_variant_id: "", traffic_allocation: 0.5 }
  ])
  const [availableModels, setAvailableModels] = useState<any[]>([])
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  // Fetch available models when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchAvailableModels()
    }
  }, [isOpen])

  const fetchAvailableModels = async () => {
    try {
      const res = await fetch("/api/v1/analytics/models")
      const data = await res.json()
      setAvailableModels(data.models || [])
    } catch (e) {
      console.error("Failed to fetch models", e)
    }
  }

  const totalAllocation = variants.reduce((sum, v) => sum + (Number(v.traffic_allocation) || 0), 0)

  const validate = () => {
    if (!name.trim()) {
      setError("Experiment name is required")
      return false
    }
    if (variants.length === 0) {
      setError("At least one variant is required")
      return false
    }
    if (Math.abs(totalAllocation - 1) > 0.0001) {
      setError("Traffic allocations must sum to 100%")
      return false
    }
    for (const v of variants) {
      if (!v.model_variant_id) {
        setError("Each variant must select a model")
        return false
      }
    }
    return true
  }

  const handleSubmit = async () => {
    setError("")
    if (!validate()) return

    setIsLoading(true)
    try {
      const payload = {
        name,
        description,
        variants: variants.map(v => ({
          model_variant_id: Number(v.model_variant_id),
          traffic_allocation: Number(v.traffic_allocation)
        }))
      }

      const res = await fetch("/api/v1/analytics/experiments", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": "admin-key"
        },
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        if (onCreated) onCreated()
        onClose()
      } else {
        const data = await res.json()
        setError(data.error || "Failed to create experiment")
      }
    } catch (e) {
      console.error("Failed to create experiment", e)
      setError("Unexpected error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-lg w-full max-w-2xl p-6 relative">
        <button
          className="absolute top-3 right-3 text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
          onClick={onClose}
        >
          <X className="h-5 w-5" />
        </button>

        <h2 className="text-xl font-semibold mb-4">Create New A/B Experiment</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Experiment Name</label>
            <input
              type="text"
              className="w-full input"
              value={name}
              onChange={e => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              className="w-full textarea min-h-[80px]"
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
          </div>

          <VariantConfigurator
            variants={variants}
            setVariants={setVariants}
            availableModels={availableModels}
          />

          {error && <div className="text-red-600 text-sm">{error}</div>}
        </div>

        <div className="mt-6 flex justify-end space-x-3">
          <button className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancel</button>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={isLoading || !!error}
          >
            {isLoading ? "Saving..." : "Create Experiment"}
          </button>
        </div>
      </div>
    </div>
  )
} 