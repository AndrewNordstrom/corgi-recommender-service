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
import ExperimentCreationModal from "./ExperimentCreationModal"

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
  const [showModal, setShowModal] = useState(false)
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
      const response = await fetch('/api/v1/analytics/experiments', {
        headers: {
          'X-API-Key': 'admin-key'
        }
      })
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

  const updateStatus = async (id: string, action: 'start' | 'stop') => {
    try {
      const resp = await fetch(`/api/v1/analytics/experiments/${id}/${action}`, {
        method: 'POST',
        headers: {
          'X-API-Key': 'admin-key'
        }
      })
      if (resp.ok) {
        await fetchExperiments()
      }
    } catch (e) {
      console.error('Failed to update experiment status', e)
    }
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
        <button
          className="btn-primary flex items-center"
          onClick={() => setShowModal(true)}
        >
          <Plus className="mr-2 h-4 w-4" />
          Create Experiment
        </button>
      </div>

      {showModal && (
        <ExperimentCreationModal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          onCreated={fetchExperiments}
        />
      )}

      {/* Experiments Table */}
      {experiments.length === 0 ? (
        <div className="text-center py-12 border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg">
          <Beaker className="h-12 w-12 mx-auto text-neutral-400" />
          <h3 className="mt-4 text-lg font-medium">A/B Testing Platform</h3>
          <p className="mt-2 text-neutral-500">
            Create sophisticated A/B tests to compare model performance and optimize your recommendation engine.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto border rounded-lg">
          <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700 text-sm">
            <thead className="bg-neutral-50 dark:bg-neutral-800">
              <tr>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Created</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
              {experiments.map((exp) => (
                <tr key={exp.id}>
                  <td className="px-4 py-2 font-medium">{exp.name}</td>
                  <td className="px-4 py-2">{new Date(exp.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-2">
                    <span className={`${getStatusColor(exp.status)} px-2 py-1 rounded text-xs inline-flex items-center space-x-1`}>
                      {getStatusIcon(exp.status)}
                      <span className="capitalize">{exp.status.toLowerCase()}</span>
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">
                    {exp.status === 'DRAFT' && (
                      <button className="btn-primary btn-sm" onClick={() => updateStatus(exp.id, 'start')}>Start</button>
                    )}
                    {exp.status === 'RUNNING' && (
                      <button className="btn-secondary btn-sm" onClick={() => updateStatus(exp.id, 'stop')}>Stop</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
} 