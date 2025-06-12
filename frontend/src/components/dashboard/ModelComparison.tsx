'use client';

import React, { useState, useEffect } from 'react';
// Using project's existing design system instead of shadcn/ui components
import { Loader2, TrendingUp, TrendingDown, Minus, Trophy, BarChart3, Clock, Users, MousePointer, Heart } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine
} from 'recharts';

interface ModelVariant {
  id: number;
  name: string;
  description: string;
  algorithm: string;
}

interface ComparisonMetrics {
  value_a: number;
  value_b: number;
  lift_percent: number;
  winner: string;
  winner_id?: number;
  statistical_significance: {
    test: string;
    p_value?: number;
    is_significant: boolean;
    confidence_level?: number;
    sample_size_a: number;
    sample_size_b: number;
  };
}

interface VariantComparison {
  variant_a: { id: number; name: string };
  variant_b: { id: number; name: string };
  metrics: {
    avg_engagement_rate: ComparisonMetrics;
    avg_response_time: ComparisonMetrics;
    total_interactions: ComparisonMetrics;
    total_impressions: ComparisonMetrics;
  };
}

interface TimeSeriesPoint {
  timestamp: string;
  impressions: number;
  likes: number;
  clicks: number;
  bookmarks: number;
  reblogs: number;
  engagement_rate: number;
  avg_response_time: number;
  total_users: number;
  unique_posts: number;
}

interface ComparisonData {
  status: string;
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  variants: Record<number, ModelVariant>;
  time_series: Record<number, TimeSeriesPoint[]>;
  summary: Record<number, any>;
  comparisons: Record<string, VariantComparison>;
  best_variant?: {
    variant_id: number;
    name: string;
    score: number;
    metrics: any;
    reasoning: string;
  };
}

const MODEL_VARIANTS: ModelVariant[] = [
  { id: 1, name: 'Collaborative Filtering', description: 'User-based collaborative filtering', algorithm: 'collaborative' },
  { id: 2, name: 'Neural Collaborative', description: 'Deep learning collaborative filtering', algorithm: 'neural_collaborative' },
  { id: 3, name: 'Content-Based', description: 'Content similarity matching', algorithm: 'content_based' },
  { id: 4, name: 'Multi-Armed Bandit', description: 'Exploration vs exploitation', algorithm: 'bandit' },
  { id: 5, name: 'Hybrid Ensemble', description: 'Combined multiple algorithms', algorithm: 'hybrid' },
  { id: 6, name: 'Graph Neural Network', description: 'Social graph-based recommendations', algorithm: 'graph_neural' }
];

export default function ModelComparison() {
  const [selectedVariants, setSelectedVariants] = useState<number[]>([]);
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState(7);

  const handleVariantToggle = (variantId: number) => {
    setSelectedVariants(prev => {
      if (prev.includes(variantId)) {
        return prev.filter(id => id !== variantId);
      } else if (prev.length < 4) { // Limit to 4 for readability
        return [...prev, variantId];
      }
      return prev;
    });
  };

  const fetchComparisonData = async () => {
    if (selectedVariants.length < 2) {
      setError('Please select at least 2 models to compare');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      selectedVariants.forEach(id => params.append('ids', id.toString()));
      params.append('days', timeRange.toString());

      const response = await fetch(`/api/v1/analytics/comparison?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken') || 'demo-token'}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setComparisonData(data);
    } catch (err) {
      console.error('Error fetching comparison data:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch comparison data');
    } finally {
      setLoading(false);
    }
  };

  const formatMetricValue = (metric: string, value: number): string => {
    switch (metric) {
      case 'avg_engagement_rate':
        return `${(value * 100).toFixed(2)}%`;
      case 'avg_response_time':
        return `${value.toFixed(0)}ms`;
      case 'total_interactions':
      case 'total_impressions':
        return value.toLocaleString();
      default:
        return value.toString();
    }
  };

  const getMetricIcon = (metric: string) => {
    switch (metric) {
      case 'avg_engagement_rate':
        return <Heart className="w-4 h-4" />;
      case 'avg_response_time':
        return <Clock className="w-4 h-4" />;
      case 'total_interactions':
        return <MousePointer className="w-4 h-4" />;
      case 'total_impressions':
        return <BarChart3 className="w-4 h-4" />;
      default:
        return <BarChart3 className="w-4 h-4" />;
    }
  };

  const getMetricName = (metric: string): string => {
    switch (metric) {
      case 'avg_engagement_rate':
        return 'Engagement Rate';
      case 'avg_response_time':
        return 'Response Time';
      case 'total_interactions':
        return 'Total Interactions';
      case 'total_impressions':
        return 'Total Impressions';
      default:
        return metric;
    }
  };

  const preparechartData = (timeSeriesData: Record<number, TimeSeriesPoint[]>) => {
    if (!timeSeriesData || Object.keys(timeSeriesData).length === 0) return [];

    // Get all unique timestamps
    const allTimestamps = new Set<string>();
    Object.values(timeSeriesData).forEach(series => {
      series.forEach(point => allTimestamps.add(point.timestamp));
    });

    // Sort timestamps
    const sortedTimestamps = Array.from(allTimestamps).sort();

    return sortedTimestamps.map(timestamp => {
      const point: any = { timestamp };
      
      Object.entries(timeSeriesData).forEach(([variantId, series]) => {
        const dataPoint = series.find(p => p.timestamp === timestamp);
        const variantName = comparisonData?.variants[parseInt(variantId)]?.name || `Model ${variantId}`;
        
        point[`${variantName}_engagement`] = dataPoint ? dataPoint.engagement_rate * 100 : 0;
        point[`${variantName}_response_time`] = dataPoint ? dataPoint.avg_response_time : 0;
        point[`${variantName}_interactions`] = dataPoint ? (dataPoint.likes + dataPoint.clicks + dataPoint.bookmarks + dataPoint.reblogs) : 0;
      });

      return point;
    });
  };

  const chartData = comparisonData ? preparechartData(comparisonData.time_series) : [];

  const getVariantColor = (index: number): string => {
    const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1', '#d084d0'];
    return colors[index % colors.length];
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Model Performance Comparison</h2>
          <p className="text-neutral-500 dark:text-neutral-400">
            Compare the real-world performance of different recommendation models
          </p>
        </div>
      </div>

      {/* Model Selection */}
      <div className="card">
        <div className="mb-6">
          <h2 className="text-xl font-bold mb-2">Select Models to Compare</h2>
          <p className="text-neutral-500 dark:text-neutral-400">
            Choose 2-4 models to analyze their performance side-by-side. 
            Currently selected: {selectedVariants.length}/4
          </p>
        </div>
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {MODEL_VARIANTS.map((variant) => (
              <div
                key={variant.id}
                className={`p-4 border rounded-lg cursor-pointer transition-all ${
                  selectedVariants.includes(variant.id)
                    ? 'border-primary bg-primary/5'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => handleVariantToggle(variant.id)}
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{variant.name}</h3>
                  {selectedVariants.includes(variant.id) && (
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-primary text-white">
                      Selected
                    </span>
                  )}
                </div>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{variant.description}</p>
                <span className="inline-block mt-2 px-2 py-1 text-xs font-semibold rounded-full bg-neutral-200 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100">
                  {variant.algorithm}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <div>
              <label className="text-sm font-medium">Time Range:</label>
              <select 
                value={timeRange} 
                onChange={(e) => setTimeRange(parseInt(e.target.value))}
                className="ml-2 border border-neutral-300 dark:border-neutral-600 rounded px-2 py-1 bg-white dark:bg-neutral-800"
              >
                <option value={1}>Last 24 hours</option>
                <option value={3}>Last 3 days</option>
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
              </select>
            </div>

            <button 
              onClick={fetchComparisonData}
              disabled={selectedVariants.length < 2 || loading}
              className="btn btn-primary disabled:opacity-50"
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {loading ? 'Analyzing...' : 'Compare Models'}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-4 border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950 rounded-lg">
              <p className="text-red-800 dark:text-red-200">{error}</p>
            </div>
          )}
        </div>
      </div>

      {/* Comparison Results */}
      {comparisonData && (
        <>
          {/* Best Performing Model */}
          {comparisonData.best_variant && (
            <div className="card">
              <div className="mb-4">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <Trophy className="w-5 h-5 text-yellow-500" />
                  Best Performing Model
                </h2>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-semibold">{comparisonData.best_variant.name}</h3>
                  <p className="text-neutral-500 dark:text-neutral-400">Score: {comparisonData.best_variant.score}/1.0</p>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                    {comparisonData.best_variant.reasoning}
                  </p>
                </div>
                <span className="px-3 py-1 text-lg font-semibold rounded-full bg-primary text-white">
                  Winner 🏆
                </span>
              </div>
            </div>
          )}

          {/* Time Series Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <div className="mb-4">
                <h3 className="text-lg font-bold">Engagement Rate Over Time</h3>
                <p className="text-neutral-500 dark:text-neutral-400">Percentage of users who interacted with recommendations</p>
              </div>
              <div>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis label={{ value: 'Engagement %', angle: -90, position: 'insideLeft' }} />
                    <Tooltip 
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                      formatter={(value: any) => [`${value.toFixed(2)}%`, 'Engagement Rate']}
                    />
                    <Legend />
                    {selectedVariants.map((variantId, index) => {
                      const variantName = comparisonData.variants[variantId]?.name || `Model ${variantId}`;
                      return (
                        <Line
                          key={variantId}
                          type="monotone"
                          dataKey={`${variantName}_engagement`}
                          stroke={getVariantColor(index)}
                          strokeWidth={2}
                          name={variantName}
                        />
                      );
                    })}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card">
              <div className="mb-4">
                <h3 className="text-lg font-bold">Response Time Over Time</h3>
                <p className="text-neutral-500 dark:text-neutral-400">Average response time for generating recommendations</p>
              </div>
              <div>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis label={{ value: 'Response Time (ms)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip 
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                      formatter={(value: any) => [`${value.toFixed(0)}ms`, 'Response Time']}
                    />
                    <Legend />
                    {selectedVariants.map((variantId, index) => {
                      const variantName = comparisonData.variants[variantId]?.name || `Model ${variantId}`;
                      return (
                        <Line
                          key={variantId}
                          type="monotone"
                          dataKey={`${variantName}_response_time`}
                          stroke={getVariantColor(index)}
                          strokeWidth={2}
                          name={variantName}
                        />
                      );
                    })}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Statistical Comparisons */}
          <div className="card">
            <div className="mb-6">
              <h3 className="text-lg font-bold">Statistical Comparisons</h3>
              <p className="text-neutral-500 dark:text-neutral-400">
                Pairwise statistical analysis with significance testing
              </p>
            </div>
            <div>
              <div className="space-y-6">
                {Object.entries(comparisonData.comparisons).map(([comparisonKey, comparison]) => (
                  <div key={comparisonKey} className="border rounded-lg p-4">
                    <h3 className="text-lg font-semibold mb-4">
                      {comparison.variant_a.name} vs {comparison.variant_b.name}
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      {Object.entries(comparison.metrics).map(([metric, data]) => (
                        <div key={metric} className="border rounded p-3">
                          <div className="flex items-center gap-2 mb-2">
                            {getMetricIcon(metric)}
                            <span className="font-medium text-sm">{getMetricName(metric)}</span>
                          </div>
                          
                          <div className="space-y-1">
                            <div className="text-xs text-neutral-500 dark:text-neutral-400">
                              {comparison.variant_a.name}: {formatMetricValue(metric, data.value_a)}
                            </div>
                            <div className="text-xs text-neutral-500 dark:text-neutral-400">
                              {comparison.variant_b.name}: {formatMetricValue(metric, data.value_b)}
                            </div>
                            
                            <div className="flex items-center gap-1 mt-2">
                              {data.lift_percent > 5 ? (
                                <TrendingUp className="w-3 h-3 text-green-500" />
                              ) : data.lift_percent < -5 ? (
                                <TrendingDown className="w-3 h-3 text-red-500" />
                              ) : (
                                <Minus className="w-3 h-3 text-gray-500" />
                              )}
                              <span className={`text-xs font-medium ${
                                data.lift_percent > 5 ? 'text-green-600' : 
                                data.lift_percent < -5 ? 'text-red-600' : 'text-gray-600'
                              }`}>
                                {data.lift_percent > 0 ? '+' : ''}{data.lift_percent.toFixed(1)}%
                              </span>
                            </div>
                            
                            <div className="mt-2">
                              <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                                data.winner === 'tie' 
                                  ? 'bg-neutral-200 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100' 
                                  : 'bg-primary text-white'
                              }`}>
                                {data.winner === 'tie' ? 'Tie' : `${data.winner} wins`}
                              </span>
                              
                              {data.statistical_significance.is_significant && (
                                <span className="ml-1 px-2 py-1 text-xs font-semibold rounded-full border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300">
                                  Significant (p&lt;0.05)
                                </span>
                              )}
                            </div>
                            
                            {data.statistical_significance.confidence_level && (
                              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                                {data.statistical_significance.confidence_level.toFixed(1)}% confidence
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Summary Table */}
          <div className="card">
            <div className="mb-6">
              <h3 className="text-lg font-bold">Performance Summary</h3>
              <p className="text-neutral-500 dark:text-neutral-400">
                Overall performance metrics for the selected time period
              </p>
            </div>
            <div>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse border border-gray-200">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="border border-gray-200 px-4 py-2 text-left">Model</th>
                      <th className="border border-gray-200 px-4 py-2 text-center">Engagement Rate</th>
                      <th className="border border-gray-200 px-4 py-2 text-center">Total Interactions</th>
                      <th className="border border-gray-200 px-4 py-2 text-center">Avg Response Time</th>
                      <th className="border border-gray-200 px-4 py-2 text-center">Total Impressions</th>
                      <th className="border border-gray-200 px-4 py-2 text-center">Unique Users</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedVariants.map((variantId) => {
                      const variant = comparisonData.variants[variantId];
                      const summary = comparisonData.summary[variantId];
                      const isBest = comparisonData.best_variant?.variant_id === variantId;
                      
                      return (
                        <tr key={variantId} className={isBest ? 'bg-yellow-50' : ''}>
                          <td className="border border-gray-200 px-4 py-2 font-medium">
                            {variant?.name}
                            {isBest && <Trophy className="inline w-4 h-4 ml-1 text-yellow-500" />}
                          </td>
                          <td className="border border-gray-200 px-4 py-2 text-center">
                            {(summary?.avg_engagement_rate * 100 || 0).toFixed(2)}%
                          </td>
                          <td className="border border-gray-200 px-4 py-2 text-center">
                            {summary?.total_interactions?.toLocaleString() || '0'}
                          </td>
                          <td className="border border-gray-200 px-4 py-2 text-center">
                            {summary?.avg_response_time?.toFixed(0) || '0'}ms
                          </td>
                          <td className="border border-gray-200 px-4 py-2 text-center">
                            {summary?.total_impressions?.toLocaleString() || '0'}
                          </td>
                          <td className="border border-gray-200 px-4 py-2 text-center">
                            {summary?.total_unique_users?.toLocaleString() || '0'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
} 