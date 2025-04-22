"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BarChart3, PieChart, TrendingUp, Server, RefreshCw } from "lucide-react"

export default function MetricsPage() {
  const [activeTab, setActiveTab] = useState("dashboard")
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = () => {
    setIsRefreshing(true)
    setTimeout(() => setIsRefreshing(false), 1000)
  }

  // Grafana dashboard URL (would come from env in production)
  const grafanaUrl = process.env.NEXT_PUBLIC_GRAFANA_URL || "http://localhost:3000"
  const dashboardUid = "a56b21d6-feb5-47c1-adf2-9e0e65219334"
  const grafanaDashboardUrl = `${grafanaUrl}/d/${dashboardUid}/corgi-recommender-dashboard?orgId=1&refresh=5s&kiosk`

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
            <iframe 
              src={grafanaDashboardUrl}
              className="w-full h-[800px] border-0"
              title="Grafana Dashboard"
            />
          </div>
        </TabsContent>
        
        <TabsContent value="recommendations" className="mt-0">
          <div className="card overflow-hidden p-0">
            <iframe 
              src={`${grafanaDashboardUrl}&viewPanel=4`}
              className="w-full h-[800px] border-0"
              title="Recommendation Metrics"
            />
          </div>
        </TabsContent>
        
        <TabsContent value="system" className="mt-0">
          <div className="card overflow-hidden p-0">
            <iframe 
              src={`${grafanaDashboardUrl}&viewPanel=6`}
              className="w-full h-[800px] border-0"
              title="System Metrics"
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}