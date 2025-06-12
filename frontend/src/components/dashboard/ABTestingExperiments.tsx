"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { 
  Beaker, 
  Plus, 
  Play, 
  Pause, 
  Stop, 
  TrendingUp, 
  Users, 
  Target, 
  Calendar,
  BarChart3,
  CheckCircle,
  Clock,
  AlertCircle,
  Eye,
  Zap,
  Percent,
  ArrowUp,
  ArrowDown,
  Minus
} from "lucide-react"

interface Experiment {
  id: string
  name: string
  description: string
  status: 'draft' | 'running' | 'paused' | 'completed' | 'failed'
  control_model: {
    name: string
    version: string
  }
  treatment_models: Array<{
    name: string
    version: string
    traffic_percent: number
  }>
  total_traffic: number
  start_date: string
  end_date?: string
  metrics: {
    participants: number
    conversions: number
    click_through_rate: number
    engagement_rate: number
    statistical_significance: number
  }
  performance_comparison: Record<string, {
    control: number
    treatment: number
    lift: number
    significance: number
  }>
}

interface ABTestingExperimentsProps {
  onTabChange?: (tab: string) => void
}

export default function ABTestingExperiments({ onTabChange }: ABTestingExperimentsProps) {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [models, setModels] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedExperiment, setSelectedExperiment] = useState<Experiment | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newExperiment, setNewExperiment] = useState({
    name: "",
    description: "",
    control_model: "",
    treatment_models: [{ model: "", traffic_percent: 50 }],
    total_traffic: 100,
    duration_days: 7
  })

  useEffect(() => {
    fetchExperiments()
    fetchModels()
  }, [])

  const fetchExperiments = async () => {
    try {
      const response = await fetch('/api/v1/experiments')
      const data = await response.json()
      setExperiments(data.experiments || [])
    } catch (error) {
      console.error('Failed to fetch experiments:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/v1/models')
      const data = await response.json()
      setModels(data.models || [])
    } catch (error) {
      console.error('Failed to fetch models:', error)
    }
  }

  const createExperiment = async () => {
    try {
      const response = await fetch('/api/v1/experiments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newExperiment)
      })
      
      if (response.ok) {
        await fetchExperiments()
        setShowCreateForm(false)
        setNewExperiment({
          name: "",
          description: "",
          control_model: "",
          treatment_models: [{ model: "", traffic_percent: 50 }],
          total_traffic: 100,
          duration_days: 7
        })
      }
    } catch (error) {
      console.error('Failed to create experiment:', error)
    }
  }

  const updateExperimentStatus = async (id: string, status: string) => {
    try {
      const response = await fetch(`/api/v1/experiments/${id}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status })
      })
      
      if (response.ok) {
        await fetchExperiments()
      }
    } catch (error) {
      console.error('Failed to update experiment status:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
        return 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-300'
      case 'completed':
        return 'text-blue-600 bg-blue-100 dark:bg-blue-900 dark:text-blue-300'
      case 'paused':
        return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-300'
      case 'failed':
        return 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-300'
      default:
        return 'text-gray-600 bg-gray-100 dark:bg-gray-900 dark:text-gray-300'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
        return <Play className="h-4 w-4" />
      case 'completed':
        return <CheckCircle className="h-4 w-4" />
      case 'paused':
        return <Pause className="h-4 w-4" />
      case 'failed':
        return <AlertCircle className="h-4 w-4" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const addTreatmentModel = () => {
    setNewExperiment({
      ...newExperiment,
      treatment_models: [
        ...newExperiment.treatment_models,
        { model: "", traffic_percent: 25 }
      ]
    })
  }

  const removeTreatmentModel = (index: number) => {
    setNewExperiment({
      ...newExperiment,
      treatment_models: newExperiment.treatment_models.filter((_, i) => i !== index)
    })
  }

  const updateTreatmentModel = (index: number, field: string, value: any) => {
    const updated = [...newExperiment.treatment_models]
    updated[index] = { ...updated[index], [field]: value }
    setNewExperiment({ ...newExperiment, treatment_models: updated })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">A/B Testing Experiments</h2>
          <p className="text-neutral-600 dark:text-neutral-400">
            Design and monitor controlled experiments to optimize your recommendation models
          </p>
        </div>
        <button className="btn-primary flex items-center">
          <Plus className="mr-2 h-4 w-4" />
          Create Experiment
        </button>
      </div>

      <div className="text-center py-12 border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg">
        <Beaker className="h-12 w-12 mx-auto text-neutral-400" />
        <h3 className="mt-4 text-lg font-medium">A/B Testing Platform</h3>
        <p className="mt-2 text-neutral-500">
          Create sophisticated A/B tests to compare model performance and optimize your recommendation engine.
        </p>
      </div>
    </div>
  )
} 