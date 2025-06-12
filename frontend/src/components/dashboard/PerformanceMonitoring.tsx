"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  LineChart, 
  Activity, 
  Users, 
  MousePointer, 
  Target,
  Zap,
  RefreshCw,
  Download,
  Calendar,
  Filter
} from "lucide-react"

interface PerformanceData {
  model_name: string
  version: string
  metrics: {
    click_through_rate: number
    engagement_rate: number
    conversion_rate: number
    response_time: number
    accuracy: number
    recall: number
    precision: number
  }
  historical_data: Array<{
    timestamp: string
    metrics: Record<string, number>
  }>
  comparisons: Record<string, {
    value: number
    change: number
    trend: 'up' | 'down' | 'stable'
  }>
}

interface PerformanceMonitoringProps {
  selectedModel?: string
}

export default function PerformanceMonitoring({ selectedModel }: PerformanceMonitoringProps) {
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('7d')
  const [selectedMetric, setSelectedMetric] = useState('click_through_rate')

  useEffect(() => {
    fetchPerformanceData()
  }, [timeRange, selectedModel])

  const fetchPerformanceData = async () => {
    try {
      const params = new URLSearchParams({ 
        time_range: timeRange,
        ...(selectedModel && { model: selectedModel })
      })
      const response = await fetch(`/api/v1/performance?${params}`)
      const data = await response.json()
      setPerformanceData(data.performance_data || [])
    } catch (error) {
      console.error('Failed to fetch performance data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatMetricName = (metric: string) => {
    return metric.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ')
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-green-600" />
      case 'down':
        return <TrendingDown className="h-4 w-4 text-red-600" />
      default:
        return <Activity className="h-4 w-4 text-neutral-600" />
    }
  }

  const formatChange = (change: number) => {
    const sign = change > 0 ? '+' : ''
    return `${sign}${(change * 100).toFixed(1)}%`
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
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Performance Monitoring</h2>
          <p className="text-neutral-600 dark:text-neutral-400">
            Real-time analytics and performance metrics for your recommendation models
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <select
            value={timeRange}
            onChange={e => setTimeRange(e.target.value)}
            className="px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
          
          <button
            onClick={fetchPerformanceData}
            className="btn-secondary flex items-center"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </button>
          
          <button className="btn-secondary flex items-center">
            <Download className="mr-2 h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {/* Key Metrics Overview */}
      {performanceData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(performanceData[0]?.comparisons || {}).slice(0, 4).map(([metric, data]) => (
            <div key={metric} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    {formatMetricName(metric)}
                  </p>
                  <p className="text-2xl font-bold">
                    {metric.includes('rate') ? `${(data.value * 100).toFixed(1)}%` : data.value.toFixed(3)}
                  </p>
                  <div className="flex items-center space-x-1 mt-1">
                    {getTrendIcon(data.trend)}
                    <span className={`text-xs font-medium ${
                      data.change > 0 ? 'text-green-600' : 
                      data.change < 0 ? 'text-red-600' : 'text-neutral-600'
                    }`}>
                      {formatChange(data.change)}
                    </span>
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-primary/10">
                  {metric.includes('click') && <MousePointer className="h-6 w-6 text-primary" />}
                  {metric.includes('engagement') && <Users className="h-6 w-6 text-primary" />}
                  {metric.includes('conversion') && <Target className="h-6 w-6 text-primary" />}
                  {metric.includes('response') && <Zap className="h-6 w-6 text-primary" />}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Model Performance Comparison */}
      <div className="card">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold">Model Performance Comparison</h3>
          <select
            value={selectedMetric}
            onChange={e => setSelectedMetric(e.target.value)}
            className="px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
          >
            <option value="click_through_rate">Click Through Rate</option>
            <option value="engagement_rate">Engagement Rate</option>
            <option value="conversion_rate">Conversion Rate</option>
            <option value="response_time">Response Time</option>
            <option value="accuracy">Accuracy</option>
            <option value="precision">Precision</option>
            <option value="recall">Recall</option>
          </select>
        </div>

        <div className="space-y-4">
          {performanceData.map((model, index) => (
            <motion.div
              key={`${model.model_name}-${model.version}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">{model.model_name} v{model.version}</h4>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    Current {formatMetricName(selectedMetric)}: {
                      selectedMetric.includes('rate') 
                        ? `${(model.metrics[selectedMetric as keyof typeof model.metrics] * 100).toFixed(1)}%`
                        : selectedMetric === 'response_time'
                        ? `${model.metrics[selectedMetric as keyof typeof model.metrics].toFixed(0)}ms`
                        : model.metrics[selectedMetric as keyof typeof model.metrics].toFixed(3)
                    }
                  </p>
                </div>
                
                <div className="flex items-center space-x-4">
                  {model.comparisons[selectedMetric] && (
                    <div className="flex items-center space-x-2">
                      {getTrendIcon(model.comparisons[selectedMetric].trend)}
                      <span className={`text-sm font-medium ${
                        model.comparisons[selectedMetric].change > 0 ? 'text-green-600' : 
                        model.comparisons[selectedMetric].change < 0 ? 'text-red-600' : 'text-neutral-600'
                      }`}>
                        {formatChange(model.comparisons[selectedMetric].change)}
                      </span>
                    </div>
                  )}
                  
                  {/* Progress Bar */}
                  <div className="w-32">
                    <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
                      <div 
                        className="bg-primary h-2 rounded-full transition-all duration-300"
                        style={{ 
                          width: `${Math.min(100, (model.metrics[selectedMetric as keyof typeof model.metrics] / Math.max(...performanceData.map(m => m.metrics[selectedMetric as keyof typeof m.metrics]))) * 100)}%` 
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Historical Trends Chart Placeholder */}
      <div className="card">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold">Historical Trends</h3>
          <div className="flex space-x-2">
            <button className="btn-secondary text-xs">
              <LineChart className="h-3 w-3 mr-1" />
              Line Chart
            </button>
            <button className="btn-secondary text-xs">
              <BarChart3 className="h-3 w-3 mr-1" />
              Bar Chart
            </button>
          </div>
        </div>
        
        <div className="h-64 flex items-center justify-center border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg">
          <div className="text-center">
            <LineChart className="h-12 w-12 mx-auto text-neutral-400" />
            <p className="mt-2 text-neutral-500">Chart visualization would appear here</p>
            <p className="text-xs text-neutral-400">Integration with Chart.js or similar library</p>
          </div>
        </div>
      </div>

      {/* Detailed Metrics Table */}
      <div className="card">
        <h3 className="text-lg font-bold mb-4">Detailed Metrics</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-neutral-200 dark:border-neutral-700">
                <th className="text-left py-2 px-4 font-medium text-sm">Model</th>
                <th className="text-right py-2 px-4 font-medium text-sm">CTR</th>
                <th className="text-right py-2 px-4 font-medium text-sm">Engagement</th>
                <th className="text-right py-2 px-4 font-medium text-sm">Conversion</th>
                <th className="text-right py-2 px-4 font-medium text-sm">Response Time</th>
                <th className="text-right py-2 px-4 font-medium text-sm">Accuracy</th>
                <th className="text-right py-2 px-4 font-medium text-sm">Precision</th>
                <th className="text-right py-2 px-4 font-medium text-sm">Recall</th>
              </tr>
            </thead>
            <tbody>
              {performanceData.map((model, index) => (
                <tr key={`${model.model_name}-${model.version}`} className="border-b border-neutral-100 dark:border-neutral-800">
                  <td className="py-3 px-4">
                    <div>
                      <div className="font-medium">{model.model_name}</div>
                      <div className="text-xs text-neutral-500">v{model.version}</div>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right">{(model.metrics.click_through_rate * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 text-right">{(model.metrics.engagement_rate * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 text-right">{(model.metrics.conversion_rate * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 text-right">{model.metrics.response_time.toFixed(0)}ms</td>
                  <td className="py-3 px-4 text-right">{model.metrics.accuracy.toFixed(3)}</td>
                  <td className="py-3 px-4 text-right">{model.metrics.precision.toFixed(3)}</td>
                  <td className="py-3 px-4 text-right">{model.metrics.recall.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {performanceData.length === 0 && (
        <div className="text-center py-12 border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg">
          <BarChart3 className="h-12 w-12 mx-auto text-neutral-400" />
          <h3 className="mt-4 text-lg font-medium">No performance data available</h3>
          <p className="mt-2 text-neutral-500">
            Performance metrics will appear here once you start running models.
          </p>
        </div>
      )}
    </div>
  )
} 