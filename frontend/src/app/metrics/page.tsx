"use client"

import { useState, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BarChart3, PieChart, TrendingUp, Server, RefreshCw, AlertCircle } from "lucide-react"

export default function MetricsPage() {
  const [activeTab, setActiveTab] = useState("dashboard")
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [grafanaAvailable, setGrafanaAvailable] = useState(false)
  const [checkingGrafana, setCheckingGrafana] = useState(true)

  const handleRefresh = () => {
    setIsRefreshing(true)
    checkGrafanaAvailability()
    setTimeout(() => setIsRefreshing(false), 1000)
  }

  // Use Grafana on port 3001 to avoid conflict with Next.js frontend on 3000
  const grafanaUrl = process.env.NEXT_PUBLIC_GRAFANA_URL || "http://localhost:3001"
  const dashboardUid = "a56b21d6-feb5-47c1-adf2-9e0e65219334"
  const grafanaDashboardUrl = `${grafanaUrl}/d/${dashboardUid}/corgi-recommender-dashboard?orgId=1&refresh=5s&kiosk`

  const checkGrafanaAvailability = async () => {
    try {
      // Try to fetch from Grafana API to check if it's available
      const response = await fetch(`${grafanaUrl}/api/health`, { 
        method: 'GET',
        mode: 'no-cors' // Allow CORS for this check
      })
      setGrafanaAvailable(true)
    } catch (error) {
      console.warn('Grafana not available:', error)
      setGrafanaAvailable(false)
    } finally {
      setCheckingGrafana(false)
    }
  }

  useEffect(() => {
    checkGrafanaAvailability()
  }, [])

  const renderGrafanaContent = (iframeSrc: string, title: string) => {
    if (checkingGrafana) {
      return (
        <div className="flex items-center justify-center h-[400px] bg-neutral-50 dark:bg-neutral-800 rounded-lg">
          <RefreshCw className="h-8 w-8 animate-spin text-primary mr-3" />
          <span className="text-lg">Checking Grafana availability...</span>
        </div>
      )
    }

    if (!grafanaAvailable) {
      return (
        <div className="flex flex-col items-center justify-center h-[400px] bg-neutral-50 dark:bg-neutral-800 rounded-lg">
          <AlertCircle className="h-12 w-12 text-amber-500 mb-4" />
          <h3 className="text-xl font-semibold mb-2">Grafana Dashboard Not Available</h3>
          <p className="text-neutral-600 dark:text-neutral-400 text-center max-w-md mb-4">
            The Grafana monitoring dashboard is not currently running. To enable metrics visualization:
          </p>
          <div className="bg-neutral-100 dark:bg-neutral-700 p-4 rounded-lg font-mono text-sm">
            <p className="mb-2">1. Start the monitoring stack:</p>
            <code className="text-primary">docker-compose -f docker-compose-monitoring.yml up -d</code>
            <p className="mt-2 mb-2">2. Or access Grafana directly at:</p>
            <code className="text-primary">{grafanaUrl}</code>
          </div>
          <button
            onClick={checkGrafanaAvailability}
            className="mt-4 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
          >
            Check Again
          </button>
        </div>
      )
    }

    return (
      <iframe 
        src={iframeSrc}
        className="w-full h-[800px] border-0"
        title={title}
        onError={() => setGrafanaAvailable(false)}
      />
    )
  }

  return (
    <div className="container mx-auto">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold mb-2">Metrics Dashboard</h1>
          <p className="text-lg text-neutral-700 dark:text-neutral-300">
            Monitor system performance and recommendation statistics.
          </p>
        </div>
        <button
          onClick={handleRefresh}
          className="btn-secondary flex items-center"
          disabled={isRefreshing}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card flex items-center p-6">
          <div className="h-12 w-12 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center mr-4">
            <BarChart3 className="h-6 w-6 text-blue-600 dark:text-blue-300" />
          </div>
          <div>
            <p className="text-sm text-neutral-500 font-medium">API Requests</p>
            <h3 className="text-2xl font-bold">12.4k</h3>
          </div>
        </div>
        
        <div className="card flex items-center p-6">
          <div className="h-12 w-12 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center mr-4">
            <PieChart className="h-6 w-6 text-green-600 dark:text-green-300" />
          </div>
          <div>
            <p className="text-sm text-neutral-500 font-medium">Success Rate</p>
            <h3 className="text-2xl font-bold">99.8%</h3>
          </div>
        </div>
        
        <div className="card flex items-center p-6">
          <div className="h-12 w-12 rounded-full bg-amber-100 dark:bg-amber-900 flex items-center justify-center mr-4">
            <TrendingUp className="h-6 w-6 text-amber-600 dark:text-amber-300" />
          </div>
          <div>
            <p className="text-sm text-neutral-500 font-medium">Avg. Response</p>
            <h3 className="text-2xl font-bold">124ms</h3>
          </div>
        </div>
        
        <div className="card flex items-center p-6">
          <div className="h-12 w-12 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center mr-4">
            <Server className="h-6 w-6 text-purple-600 dark:text-purple-300" />
          </div>
          <div>
            <p className="text-sm text-neutral-500 font-medium">System Load</p>
            <h3 className="text-2xl font-bold">0.42</h3>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="mb-8">
          <TabsTrigger value="dashboard" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Main Dashboard
          </TabsTrigger>
          <TabsTrigger value="recommendations" className="flex items-center gap-2">
            <PieChart className="h-4 w-4" />
            Recommendations
          </TabsTrigger>
          <TabsTrigger value="system" className="flex items-center gap-2">
            <Server className="h-4 w-4" />
            System Metrics
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="dashboard" className="mt-0">
          <div className="card overflow-hidden p-0">
            {renderGrafanaContent(grafanaDashboardUrl, "Grafana Dashboard")}
          </div>
        </TabsContent>
        
        <TabsContent value="recommendations" className="mt-0">
          <div className="card overflow-hidden p-0">
            {renderGrafanaContent(`${grafanaDashboardUrl}&viewPanel=4`, "Recommendation Metrics")}
          </div>
        </TabsContent>
        
        <TabsContent value="system" className="mt-0">
          <div className="card overflow-hidden p-0">
            {renderGrafanaContent(`${grafanaDashboardUrl}&viewPanel=6`, "System Metrics")}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}