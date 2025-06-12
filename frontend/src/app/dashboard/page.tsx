"use client"

import { useState, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Key, 
  User, 
  Settings, 
  BarChart, 
  Copy, 
  RefreshCw,
  Plus,
  Trash,
  ExternalLink,
  Brain,
  Beaker,
  TrendingUp,
  BookOpen,
  GitCompare
} from "lucide-react"
import { motion } from "framer-motion"
import ModelRegistry from "@/components/dashboard/ModelRegistry"
import PerformanceMonitoring from "@/components/dashboard/PerformanceMonitoring"
import ABTestingExperiments from "@/components/dashboard/ABTestingExperiments"
import ModelComparison from "@/components/dashboard/ModelComparison"
import OnboardingTour from "@/components/dashboard/OnboardingTour"

// Mock API keys for demo
const initialApiKeys = [
  { 
    id: "key_1", 
    name: "Development Key", 
    key: "ck_DEMO1234567890abcdef", 
    created: "2023-01-15T12:00:00Z",
    lastUsed: "2023-04-02T09:15:00Z"
  },
  { 
    id: "key_2", 
    name: "Production Key", 
    key: "ck_PROD1234567890abcdef", 
    created: "2023-02-20T14:30:00Z",
    lastUsed: "2023-04-10T16:45:00Z"
  }
]

export default function DashboardPage() {
  const [apiKeys, setApiKeys] = useState(initialApiKeys)
  const [activeTab, setActiveTab] = useState("keys")
  const [copied, setCopied] = useState<string | null>(null)
  const [newKeyName, setNewKeyName] = useState("")
  const [showOnboarding, setShowOnboarding] = useState(false)

  // Check if user has completed onboarding
  useEffect(() => {
    const hasCompletedOnboarding = localStorage.getItem('dashboard-onboarding-completed')
    if (!hasCompletedOnboarding) {
      setShowOnboarding(true)
    }
  }, [])
  
  const handleCopyKey = (keyId: string, keyValue: string) => {
    navigator.clipboard.writeText(keyValue)
    setCopied(keyId)
    setTimeout(() => setCopied(null), 2000)
  }
  
  const handleCreateKey = () => {
    if (!newKeyName.trim()) return
    
    const newKey = {
      id: `key_${Date.now()}`,
      name: newKeyName,
      key: `ck_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`,
      created: new Date().toISOString(),
      lastUsed: "Never"
    }
    
    setApiKeys([...apiKeys, newKey])
    setNewKeyName("")
  }
  
  const handleDeleteKey = (keyId: string) => {
    setApiKeys(apiKeys.filter(key => key.id !== keyId))
  }
  
  return (
    <div className="container mx-auto">
      <div className="mb-8" id="dashboard-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-4">ML Research Dashboard</h1>
            <p className="text-lg text-neutral-700 dark:text-neutral-300">
              Comprehensive model management for recommendation systems research.
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowOnboarding(true)}
              className="btn-secondary flex items-center text-sm"
            >
              <BookOpen className="mr-2 h-4 w-4" />
              Take Tour
            </button>
          </div>
        </div>
      </div>

      {/* Onboarding Tour */}
      <OnboardingTour
        isOpen={showOnboarding}
        onClose={() => setShowOnboarding(false)}
        onComplete={() => {
          setShowOnboarding(false)
          setActiveTab("models") // Start with models after onboarding
        }}
      />
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <div className="card sticky top-24">
            <div className="flex items-center space-x-4 mb-6">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Demo User</h2>
                <p className="text-sm text-neutral-500">Free Plan</p>
              </div>
            </div>
            
            <nav className="space-y-1">
              <button
                onClick={() => setActiveTab("keys")}
                className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                  activeTab === "keys" 
                    ? "bg-primary/10 text-primary font-medium" 
                    : "text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                }`}
              >
                <Key className="mr-3 h-5 w-5" />
                API Keys
              </button>
              
              <button
                onClick={() => setActiveTab("account")}
                className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                  activeTab === "account" 
                    ? "bg-primary/10 text-primary font-medium" 
                    : "text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                }`}
              >
                <User className="mr-3 h-5 w-5" />
                Account
              </button>
              
              <button
                onClick={() => setActiveTab("settings")}
                className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                  activeTab === "settings" 
                    ? "bg-primary/10 text-primary font-medium" 
                    : "text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                }`}
              >
                <Settings className="mr-3 h-5 w-5" />
                Settings
              </button>
              
              <button
                onClick={() => setActiveTab("usage")}
                className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                  activeTab === "usage" 
                    ? "bg-primary/10 text-primary font-medium" 
                    : "text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                }`}
              >
                <BarChart className="mr-3 h-5 w-5" />
                Usage Stats
              </button>
              
              <button
                id="models-tab"
                onClick={() => setActiveTab("models")}
                className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                  activeTab === "models" 
                    ? "bg-primary/10 text-primary font-medium" 
                    : "text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                }`}
              >
                <Brain className="mr-3 h-5 w-5" />
                Model Registry
              </button>
              
              <button
                id="experiments-tab"
                onClick={() => setActiveTab("experiments")}
                className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                  activeTab === "experiments" 
                    ? "bg-primary/10 text-primary font-medium" 
                    : "text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                }`}
              >
                <Beaker className="mr-3 h-5 w-5" />
                A/B Testing
              </button>
              
              <button
                id="performance-tab"
                onClick={() => setActiveTab("performance")}
                className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                  activeTab === "performance" 
                    ? "bg-primary/10 text-primary font-medium" 
                    : "text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                }`}
              >
                <TrendingUp className="mr-3 h-5 w-5" />
                Performance
              </button>
              
              <button
                id="comparison-tab"
                onClick={() => setActiveTab("comparison")}
                className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                  activeTab === "comparison" 
                    ? "bg-primary/10 text-primary font-medium" 
                    : "text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                }`}
              >
                <GitCompare className="mr-3 h-5 w-5" />
                Model Comparison
              </button>
            </nav>
          </div>
        </div>
        
        <div className="lg:col-span-3">
          {activeTab === "keys" && (
            <div className="card">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold">API Keys</h2>
                <button
                  onClick={() => setActiveTab("keys")}
                  className="btn-secondary flex items-center text-sm px-3 py-1"
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Refresh
                </button>
              </div>
              
              <div className="mb-6">
                <div className="flex">
                  <input
                    type="text"
                    placeholder="Enter key name..."
                    className="flex-1 px-3 py-2 border border-r-0 border-neutral-200 dark:border-neutral-700 rounded-l-md bg-white dark:bg-neutral-800"
                    value={newKeyName}
                    onChange={e => setNewKeyName(e.target.value)}
                  />
                  <button
                    onClick={handleCreateKey}
                    className="btn-primary flex items-center px-4 py-2 rounded-l-none rounded-r-md"
                    disabled={!newKeyName.trim()}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Create Key
                  </button>
                </div>
              </div>
              
              <div className="space-y-4">
                {apiKeys.map(key => (
                  <motion.div
                    key={key.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-4"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-bold text-lg">{key.name}</h3>
                        <div className="flex items-center mt-2">
                          <code className="bg-neutral-100 dark:bg-neutral-800 px-3 py-1.5 rounded text-sm font-mono">
                            {key.key}
                          </code>
                          <button
                            onClick={() => handleCopyKey(key.id, key.key)}
                            className="ml-2 p-1.5 text-neutral-500 hover:text-primary"
                          >
                            {copied === key.id ? (
                              <span className="text-green-500 text-xs">Copied!</span>
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </div>
                      
                      <button
                        onClick={() => handleDeleteKey(key.id)}
                        className="text-red-500 hover:text-red-700 p-1"
                      >
                        <Trash className="h-5 w-5" />
                      </button>
                    </div>
                    
                    <div className="flex mt-3 text-sm text-neutral-500">
                      <span>Created: {new Date(key.created).toLocaleDateString()}</span>
                      <span className="ml-4">
                        Last used: {key.lastUsed === "Never" ? "Never" : new Date(key.lastUsed).toLocaleDateString()}
                      </span>
                    </div>
                  </motion.div>
                ))}
                
                {apiKeys.length === 0 && (
                  <div className="text-center py-12 border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg">
                    <Key className="h-12 w-12 mx-auto text-neutral-400" />
                    <h3 className="mt-4 text-lg font-medium">No API keys</h3>
                    <p className="mt-2 text-neutral-500">
                      Create an API key to start using the Corgi Recommender Service.
                    </p>
                  </div>
                )}
              </div>
              
              <div className="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-700">
                <h3 className="text-lg font-bold mb-4">Using Your API Key</h3>
                <div className="bg-neutral-100 dark:bg-neutral-800 p-4 rounded-md">
                  <code className="block mb-2 text-sm font-mono">
                    # Example request with API key
                  </code>
                  <code className="block text-sm font-mono">
                    curl -H "Authorization: Bearer YOUR_API_KEY" \<br />
                    &nbsp;&nbsp;https://api.corgi-recommender.io/api/v1/recommendations
                  </code>
                </div>
                <p className="mt-4 text-sm text-neutral-500">
                  Include your API key in all requests to authenticate with the Corgi Recommender Service API.
                </p>
                <div className="mt-4">
                  <a
                    href="/api"
                    className="text-primary hover:text-primary-dark flex items-center text-sm font-medium"
                  >
                    View API Documentation
                    <ExternalLink className="ml-2 h-4 w-4" />
                  </a>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === "account" && (
            <div className="card">
              <h2 className="text-xl font-bold mb-6">Account Information</h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-8">
                Manage your account details and preferences.
              </p>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium mb-2">Email Address</label>
                  <input
                    type="email"
                    value="demo@example.com"
                    className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
                    readOnly
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Full Name</label>
                  <input
                    type="text"
                    placeholder="Your name"
                    className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Organization</label>
                  <input
                    type="text"
                    placeholder="Your organization"
                    className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
                  />
                </div>
                
                <div className="pt-4">
                  <button className="btn-primary px-4 py-2">
                    Save Changes
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === "settings" && (
            <div className="card">
              <h2 className="text-xl font-bold mb-6">Integration Settings</h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-8">
                Configure how the Corgi Recommender Service integrates with your application.
              </p>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium mb-2">Default Injection Strategy</label>
                  <select className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800">
                    <option>Uniform</option>
                    <option>Tag Match</option>
                    <option>First Only</option>
                    <option>After N</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Default Injection Rate</label>
                  <input
                    type="number"
                    min="0.05"
                    max="0.5"
                    step="0.05"
                    defaultValue="0.2"
                    className="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
                  />
                  <p className="mt-1 text-xs text-neutral-500">
                    Percentage of timeline posts that will be recommendations (5-50%)
                  </p>
                </div>
                
                <div>
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium">Cold Start Strategy</label>
                    <span className="px-2 py-0.5 text-xs bg-primary/10 text-primary rounded">Beta</span>
                  </div>
                  <select className="w-full mt-2 px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800">
                    <option>Popular Posts</option>
                    <option>Topic Sampling</option>
                    <option>User Clustering</option>
                  </select>
                  <p className="mt-1 text-xs text-neutral-500">
                    Strategy to use for new users with no interaction history
                  </p>
                </div>
                
                <div className="pt-4">
                  <button className="btn-primary px-4 py-2">
                    Save Settings
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === "usage" && (
            <div className="card">
              <h2 className="text-xl font-bold mb-6">Usage Statistics</h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-8">
                View your API usage and performance metrics.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div className="bg-neutral-100 dark:bg-neutral-800 p-4 rounded-md">
                  <h3 className="text-sm font-medium text-neutral-500 mb-1">API Calls (30 days)</h3>
                  <p className="text-2xl font-bold">12,435</p>
                </div>
                
                <div className="bg-neutral-100 dark:bg-neutral-800 p-4 rounded-md">
                  <h3 className="text-sm font-medium text-neutral-500 mb-1">Recommendations</h3>
                  <p className="text-2xl font-bold">3,842</p>
                </div>
                
                <div className="bg-neutral-100 dark:bg-neutral-800 p-4 rounded-md">
                  <h3 className="text-sm font-medium text-neutral-500 mb-1">Avg. Response Time</h3>
                  <p className="text-2xl font-bold">124ms</p>
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-bold mb-4">Monthly Usage</h3>
                <div className="h-64 bg-neutral-100 dark:bg-neutral-800 rounded-md flex items-center justify-center">
                  <p className="text-neutral-500">
                    Usage graphs available in the metrics dashboard
                  </p>
                </div>
                
                <div className="mt-4 flex justify-end">
                  <a
                    href="/metrics"
                    className="text-primary hover:text-primary-dark flex items-center text-sm font-medium"
                  >
                    View Full Metrics Dashboard
                    <ExternalLink className="ml-2 h-4 w-4" />
                  </a>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === "models" && (
            <ModelRegistry onTabChange={setActiveTab} />
          )}
          
          {activeTab === "experiments" && (
            <ABTestingExperiments onTabChange={setActiveTab} />
          )}
          
          {activeTab === "performance" && (
            <PerformanceMonitoring />
          )}
          
          {activeTab === "comparison" && (
            <ModelComparison />
          )}
        </div>
      </div>
    </div>
  )
}