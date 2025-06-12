"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { 
  Brain, 
  Plus, 
  Settings, 
  TrendingUp, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  ExternalLink,
  Upload,
  Tag,
  User,
  Calendar,
  Activity,
  Zap,
  Database,
  GitBranch,
  AlertCircle,
  Trash2,
  Edit3,
  Copy,
  Play,
  Pause,
  Archive,
  BookOpen,
  Code,
  HelpCircle
} from "lucide-react"

interface Model {
  name: string
  version: string
  type: string
  status: string
  author: string
  description: string
  capabilities: string[]
  performance_metrics: Record<string, number>
  created_at: string
  updated_at: string
}

interface ModelRegistryProps {
  onTabChange?: (tab: string) => void
}

// Demo data for immediate research value
const demoModels = [
  {
    id: "1",
    name: "simple_collaborative_filtering",
    version: "1.0",
    type: "collaborative_filtering",
    status: "production",
    author: "research@university.edu",
    description: "Classic user-item collaborative filtering using matrix factorization. Good baseline for comparison studies.",
    accuracy: 0.85,
    precision: 0.78,
    recall: 0.72,
    f1Score: 0.75,
    responseTime: 45,
    lastUpdated: "2024-06-07T10:30:00Z",
    tags: ["baseline", "collaborative", "matrix-factorization"],
    codeReference: "models.collaborative.SimpleCollaborativeFiltering",
    paperReference: "https://doi.org/10.1145/1864708.1864721",
    hyperparameters: {
      embedding_dim: 128,
      learning_rate: 0.001,
      regularization: 0.01
    }
  },
  {
    id: "2", 
    name: "neural_collaborative_filtering",
    version: "1.0",
    type: "neural_collaborative",
    status: "staging",
    author: "deeplearning@lab.edu",
    description: "Deep neural network for collaborative filtering with embedding layers and multi-layer perceptrons. State-of-the-art performance.",
    accuracy: 0.91,
    precision: 0.85,
    recall: 0.79,
    f1Score: 0.82,
    responseTime: 89,
    lastUpdated: "2024-06-08T15:45:00Z",
    tags: ["neural", "deep-learning", "embedding"],
    codeReference: "models.neural.NeuralCollaborativeFiltering",
    paperReference: "https://doi.org/10.1145/3038912.3052569",
    hyperparameters: {
      embedding_dim: 256,
      hidden_layers: [512, 256, 128],
      dropout: 0.2,
      learning_rate: 0.0001
    }
  },
  {
    id: "3",
    name: "content_based_semantic",
    version: "2.1",
    type: "content_based", 
    status: "experimental",
    author: "nlp@research.org",
    description: "Content-based filtering using BERT embeddings and semantic similarity. Excellent for cold start scenarios.",
    accuracy: 0.88,
    precision: 0.75,
    recall: 0.65,
    f1Score: 0.70,
    responseTime: 156,
    lastUpdated: "2024-06-09T09:15:00Z",
    tags: ["content", "bert", "semantic", "nlp"],
    codeReference: "models.content.SemanticContentFiltering",
    paperReference: "https://doi.org/10.18653/v1/D19-1671",
    hyperparameters: {
      bert_model: "bert-base-uncased",
      similarity_threshold: 0.75,
      max_sequence_length: 512
    }
  },
  {
    id: "4",
    name: "multi_armed_bandit_thompson",
    version: "1.3",
    type: "multi_armed_bandit",
    status: "staging",
    author: "bandits@stanford.edu", 
    description: "Thompson Sampling bandit algorithm for exploration-exploitation balance. Ideal for real-time learning.",
    accuracy: 0.82,
    precision: 0.83,
    recall: 0.84,
    f1Score: 0.83,
    responseTime: 23,
    lastUpdated: "2024-06-08T14:20:00Z", 
    tags: ["bandit", "thompson-sampling", "exploration", "online-learning"],
    codeReference: "models.bandits.ThompsonSamplingBandit",
    paperReference: "https://doi.org/10.1007/s10994-013-5358-2",
    hyperparameters: {
      alpha_prior: 1.0,
      beta_prior: 1.0,
      exploration_rate: 0.1
    }
  },
  {
    id: "5",
    name: "hybrid_ensemble_v2",
    version: "2.0",
    type: "ensemble",
    status: "production",
    author: "ensemble@mit.edu",
    description: "Ensemble combining collaborative filtering, content-based, and popularity models with learned weights.",
    accuracy: 0.93,
    precision: 0.87,
    recall: 0.81,
    f1Score: 0.84,
    responseTime: 67,
    lastUpdated: "2024-06-09T11:00:00Z",
    tags: ["ensemble", "hybrid", "meta-learning"],
    codeReference: "models.ensemble.HybridEnsemble", 
    paperReference: "https://doi.org/10.1145/2043932.2043955",
    hyperparameters: {
      collaborative_weight: 0.5,
      content_weight: 0.3,
      popularity_weight: 0.2,
      meta_learning_rate: 0.01
    }
  },
  {
    id: "6",
    name: "graph_neural_network",
    version: "1.0", 
    type: "graph_neural",
    status: "experimental",
    author: "graph@cmu.edu",
    description: "Graph Neural Network leveraging user-item interaction graphs with node2vec embeddings. Research-grade implementation.",
    accuracy: 0.90,
    precision: 0.86,
    recall: 0.83,
    f1Score: 0.84,
    responseTime: 134,
    lastUpdated: "2024-06-09T13:30:00Z",
    tags: ["graph", "gnn", "node2vec", "research"],
    codeReference: "models.graph.GraphNeuralRecommender",
    paperReference: "https://doi.org/10.1145/3292500.3330673",
    hyperparameters: {
      embedding_dim: 128,
      walk_length: 10,
      num_walks: 200,
      gnn_layers: 3
    }
  }
]

const statusColors = {
  experimental: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
  staging: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300", 
  production: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  deprecated: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  archived: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300"
}

const statusIcons = {
  experimental: <AlertCircle className="h-4 w-4" />,
  staging: <Clock className="h-4 w-4" />,
  production: <CheckCircle className="h-4 w-4" />,
  deprecated: <Archive className="h-4 w-4" />,
  archived: <Archive className="h-4 w-4" />
}

const typeColors = {
  collaborative_filtering: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  neural_collaborative: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300",
  content_based: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
  multi_armed_bandit: "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300",
  ensemble: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-300",
  graph_neural: "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-300",
  custom: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300"
}

interface TooltipProps {
  children: React.ReactNode
  content: string
  className?: string
}

function Tooltip({ children, content, className = "" }: TooltipProps) {
  return (
    <div className={`group relative ${className}`}>
      {children}
      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-black dark:bg-white text-white dark:text-black text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50">
        {content}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-black dark:border-t-white"></div>
      </div>
    </div>
  )
}

export default function ModelRegistry({ onTabChange }: ModelRegistryProps) {
  const [models, setModels] = useState(demoModels)
  const [selectedModel, setSelectedModel] = useState(null)
  const [showRegistrationForm, setShowRegistrationForm] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [typeFilter, setTypeFilter] = useState("all")
  const [activeModelId, setActiveModelId] = useState<string | null>(null)
  const [activatingModelId, setActivatingModelId] = useState<string | null>(null)

  // Load active model on component mount
  useEffect(() => {
    fetchActiveModel()
  }, [])

  const fetchActiveModel = async () => {
    try {
      // This would be replaced with actual API call to get user's active model
      // For demo purposes, we'll use localStorage
      const savedActiveModel = localStorage.getItem('activeModelId')
      if (savedActiveModel) {
        setActiveModelId(savedActiveModel)
      }
    } catch (error) {
      console.error('Failed to fetch active model:', error)
    }
  }

  const activateModel = async (modelId: string) => {
    setActivatingModelId(modelId)
    
    try {
      // Make API call to activate the model
      const response = await fetch(`/api/v1/analytics/models/variants/${modelId}/activate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for authentication
      })

      if (response.ok) {
        const data = await response.json()
        setActiveModelId(modelId)
        
        // Save to localStorage for demo persistence
        localStorage.setItem('activeModelId', modelId)
        
        // Show success notification (you could add a toast notification here)
        console.log('Model activated successfully:', data)
        
        // Optional: Show a temporary success message
        const modelName = models.find(m => m.id === modelId)?.name || 'Model'
        alert(`✅ ${modelName} is now active for your recommendations!`)
        
      } else {
        const errorData = await response.json()
        console.error('Failed to activate model:', errorData)
        alert(`❌ Failed to activate model: ${errorData.error || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Error activating model:', error)
      alert('❌ Network error while activating model. Please try again.')
    } finally {
      setActivatingModelId(null)
    }
  }

  const filteredModels = models.filter(model => {
    const matchesSearch = model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         model.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         model.author.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === "all" || model.status === statusFilter
    const matchesType = typeFilter === "all" || model.type === typeFilter
    return matchesSearch && matchesStatus && matchesType
  })

  const getPerformanceScore = (model) => {
    return Math.round((model.accuracy + model.precision + model.recall + model.f1Score) / 4 * 100)
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div id="quick-start-section" className="space-y-6">
      {/* Header with Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold mb-2">Model Registry</h2>
          <div className="flex items-center space-x-4">
            <p className="text-neutral-600 dark:text-neutral-400">
              Manage and deploy your recommendation algorithms
            </p>
            {activeModelId && (
              <div className="flex items-center space-x-2 px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300 rounded-full text-sm">
                <Zap className="h-4 w-4" />
                <span>
                  Active: {models.find(m => m.id === activeModelId)?.name || 'Unknown Model'}
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <Tooltip content="Learn about model management best practices">
            <button className="btn-secondary flex items-center">
              <BookOpen className="mr-2 h-4 w-4" />
              Documentation
            </button>
          </Tooltip>
          <button 
            onClick={() => setShowRegistrationForm(true)}
            className="btn-primary flex items-center"
          >
            <Plus className="mr-2 h-4 w-4" />
            Register Model
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-neutral-800 p-4 rounded-lg border border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">Total Models</p>
              <p className="text-2xl font-bold">{models.length}</p>
            </div>
            <Brain className="h-8 w-8 text-primary" />
          </div>
        </div>
        <div className="bg-white dark:bg-neutral-800 p-4 rounded-lg border border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">In Production</p>
              <p className="text-2xl font-bold text-green-600">
                {models.filter(m => m.status === 'production').length}
              </p>
            </div>
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
        </div>
        <div className="bg-white dark:bg-neutral-800 p-4 rounded-lg border border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">Staging</p>
              <p className="text-2xl font-bold text-blue-600">
                {models.filter(m => m.status === 'staging').length}
              </p>
            </div>
            <Clock className="h-8 w-8 text-blue-600" />
          </div>
        </div>
        <div className="bg-white dark:bg-neutral-800 p-4 rounded-lg border border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">Experimental</p>
              <p className="text-2xl font-bold text-yellow-600">
                {models.filter(m => m.status === 'experimental').length}
              </p>
            </div>
            <AlertCircle className="h-8 w-8 text-yellow-600" />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search models by name, description, or author..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-base w-full"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input-base"
        >
          <option value="all">All Statuses</option>
          <option value="experimental">Experimental</option>
          <option value="staging">Staging</option> 
          <option value="production">Production</option>
          <option value="deprecated">Deprecated</option>
          <option value="archived">Archived</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="input-base"
        >
          <option value="all">All Types</option>
          <option value="collaborative_filtering">Collaborative Filtering</option>
          <option value="neural_collaborative">Neural Collaborative</option>
          <option value="content_based">Content-Based</option>
          <option value="multi_armed_bandit">Multi-Armed Bandit</option>
          <option value="ensemble">Ensemble</option>
          <option value="graph_neural">Graph Neural</option>
        </select>
      </div>

      {/* Models Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredModels.map((model) => (
          <motion.div
            key={model.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white dark:bg-neutral-800 p-6 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:shadow-lg transition-shadow"
          >
            {/* Model Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <h3 className="font-semibold text-lg">{model.name}</h3>
                  <span className="text-sm text-neutral-500">v{model.version}</span>
                </div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
                  {model.description}
                </p>
              </div>
            </div>

            {/* Status and Type */}
            <div className="flex items-center space-x-2 mb-4">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[model.status]}`}>
                {statusIcons[model.status]}
                <span className="ml-1 capitalize">{model.status}</span>
              </span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${typeColors[model.type]}`}>
                {model.type.replace('_', ' ')}
              </span>
            </div>

            {/* Performance Metrics */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <Tooltip content="Overall performance score based on accuracy, precision, recall, and F1">
                <div className="text-center p-2 bg-neutral-50 dark:bg-neutral-700 rounded">
                  <p className="text-lg font-bold text-primary">{getPerformanceScore(model)}%</p>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400">Score</p>
                </div>
              </Tooltip>
              <Tooltip content="Average response time for predictions">
                <div className="text-center p-2 bg-neutral-50 dark:bg-neutral-700 rounded">
                  <p className="text-lg font-bold">{model.responseTime}ms</p>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400">Response</p>
                </div>
              </Tooltip>
            </div>

            {/* Tags */}
            <div className="flex flex-wrap gap-1 mb-4">
              {model.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center px-2 py-1 rounded text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400"
                >
                  <Tag className="mr-1 h-3 w-3" />
                  {tag}
                </span>
              ))}
              {model.tags.length > 3 && (
                <span className="text-xs text-neutral-500">+{model.tags.length - 3} more</span>
              )}
            </div>

            {/* Author and Date */}
            <div className="flex items-center justify-between text-sm text-neutral-500 mb-4">
              <div className="flex items-center">
                <User className="mr-1 h-4 w-4" />
                {model.author}
              </div>
              <div className="flex items-center">
                <Clock className="mr-1 h-4 w-4" />
                {formatDate(model.lastUpdated)}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center space-x-2">
              {/* Activation Button */}
              {activeModelId === model.id ? (
                <Tooltip content="This model is currently active for your recommendations">
                  <button className="btn-primary flex-1 text-sm flex items-center justify-center cursor-default">
                    <CheckCircle className="mr-1 h-4 w-4" />
                    Active
                  </button>
                </Tooltip>
              ) : (
                <Tooltip content="Activate this model for your live recommendations">
                  <button 
                    onClick={() => activateModel(model.id)}
                    disabled={activatingModelId === model.id}
                    className="btn-secondary flex-1 text-sm flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary hover:text-white transition-colors"
                  >
                    {activatingModelId === model.id ? (
                      <>
                        <div className="animate-spin mr-1 h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                        Activating...
                      </>
                    ) : (
                      <>
                        <Zap className="mr-1 h-4 w-4" />
                        Activate
                      </>
                    )}
                  </button>
                </Tooltip>
              )}
              
              <Tooltip content="View detailed metrics and configuration">
                <button 
                  onClick={() => setSelectedModel(model)}
                  className="btn-secondary text-sm flex items-center justify-center"
                >
                  <Activity className="h-4 w-4" />
                </button>
              </Tooltip>
              <Tooltip content="View source code implementation">
                <button className="btn-secondary text-sm flex items-center justify-center">
                  <Code className="h-4 w-4" />
                </button>
              </Tooltip>
              <Tooltip content="View research paper">
                <button className="btn-secondary text-sm flex items-center justify-center">
                  <ExternalLink className="h-4 w-4" />
                </button>
              </Tooltip>
            </div>
          </motion.div>
        ))}
      </div>

      {filteredModels.length === 0 && (
        <div className="text-center py-12">
          <Brain className="mx-auto h-12 w-12 text-neutral-400 mb-4" />
          <h3 className="text-lg font-medium text-neutral-600 dark:text-neutral-400 mb-2">
            No models found
          </h3>
          <p className="text-neutral-500 mb-4">
            Try adjusting your search criteria or register a new model.
          </p>
          <button 
            onClick={() => setShowRegistrationForm(true)}
            className="btn-primary"
          >
            Register Your First Model
          </button>
        </div>
      )}

      {/* Model Details Modal */}
      {selectedModel && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="p-6 border-b border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold mb-2">{selectedModel.name}</h2>
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[selectedModel.status]}`}>
                      {statusIcons[selectedModel.status]}
                      <span className="ml-1 capitalize">{selectedModel.status}</span>
                    </span>
                    <span className="text-neutral-500">v{selectedModel.version}</span>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedModel(null)}
                  className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Description */}
              <div>
                <h3 className="font-semibold mb-2">Description</h3>
                <p className="text-neutral-600 dark:text-neutral-400">{selectedModel.description}</p>
              </div>

              {/* Performance Metrics */}
              <div>
                <h3 className="font-semibold mb-4">Performance Metrics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
                    <p className="text-2xl font-bold text-blue-600">{(selectedModel.accuracy * 100).toFixed(1)}%</p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Accuracy</p>
                  </div>
                  <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
                    <p className="text-2xl font-bold text-green-600">{(selectedModel.precision * 100).toFixed(1)}%</p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Precision</p>
                  </div>
                  <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
                    <p className="text-2xl font-bold text-orange-600">{(selectedModel.recall * 100).toFixed(1)}%</p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Recall</p>
                  </div>
                  <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
                    <p className="text-2xl font-bold text-purple-600">{(selectedModel.f1Score * 100).toFixed(1)}%</p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">F1 Score</p>
                  </div>
                </div>
              </div>

              {/* Hyperparameters */}
              <div>
                <h3 className="font-semibold mb-4">Hyperparameters</h3>
                <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
                  <pre className="text-sm text-neutral-700 dark:text-neutral-300">
                    {JSON.stringify(selectedModel.hyperparameters, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Tags */}
              <div>
                <h3 className="font-semibold mb-2">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedModel.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400"
                    >
                      <Tag className="mr-1 h-4 w-4" />
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* References */}
              <div>
                <h3 className="font-semibold mb-4">References</h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
                    <div className="flex items-center">
                      <Code className="mr-2 h-4 w-4" />
                      <span className="text-sm">Code Reference</span>
                    </div>
                    <code className="text-sm text-neutral-600 dark:text-neutral-400">{selectedModel.codeReference}</code>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
                    <div className="flex items-center">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      <span className="text-sm">Paper Reference</span>
                    </div>
                    <button className="text-blue-600 hover:text-blue-700 text-sm">
                      View Paper
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
} 