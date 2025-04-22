"use client"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useState } from "react"
import { Code, FileText, ExternalLink } from "lucide-react"

export default function ApiPage() {
  const [activeTab, setActiveTab] = useState("overview")

  return (
    <div className="container mx-auto">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-4">API Documentation</h1>
        <p className="text-lg text-neutral-700 dark:text-neutral-300">
          Explore and test the Corgi Recommender Service API using interactive documentation.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="mb-8">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="swagger" className="flex items-center gap-2">
            <Code className="h-4 w-4" />
            Swagger UI
          </TabsTrigger>
          <TabsTrigger value="redoc" className="flex items-center gap-2">
            <ExternalLink className="h-4 w-4" />
            ReDoc
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="mt-0">
          <div className="card">
            <h2 className="text-2xl font-bold mb-4">API Overview</h2>
            <p className="mb-4">
              The Corgi Recommender Service provides a RESTful API for integrating recommendation features into your Fediverse application.
            </p>

            <h3 className="text-xl font-bold mt-6 mb-3">Authentication</h3>
            <p className="mb-4">
              API requests require authentication using Bearer tokens. You can obtain a token from the dashboard.
            </p>
            <pre className="bg-neutral-100 dark:bg-neutral-800 p-4 rounded-md overflow-x-auto">
              {`Authorization: Bearer YOUR_API_TOKEN`}
            </pre>

            <h3 className="text-xl font-bold mt-6 mb-3">Base URL</h3>
            <p className="mb-4">
              All API endpoints are prefixed with <code>/api/v1</code>.
            </p>

            <h3 className="text-xl font-bold mt-6 mb-3">Available Endpoints</h3>
            <div className="space-y-4">
              <div className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-md">
                <div className="flex items-center">
                  <span className="px-2 py-1 mr-3 text-xs font-bold bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded">GET</span>
                  <code>/api/v1/recommendations</code>
                </div>
                <p className="mt-2 text-sm">Get personalized recommendations for a user.</p>
              </div>

              <div className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-md">
                <div className="flex items-center">
                  <span className="px-2 py-1 mr-3 text-xs font-bold bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">POST</span>
                  <code>/api/v1/interactions</code>
                </div>
                <p className="mt-2 text-sm">Record user interactions with content.</p>
              </div>

              <div className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-md">
                <div className="flex items-center">
                  <span className="px-2 py-1 mr-3 text-xs font-bold bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded">GET</span>
                  <code>/api/v1/timelines/home</code>
                </div>
                <p className="mt-2 text-sm">Get a user's timeline with injected recommendations.</p>
              </div>
            </div>

            <div className="mt-8">
              <p className="text-sm text-neutral-500">
                For detailed documentation, use the Swagger UI or ReDoc tabs.
              </p>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="swagger" className="mt-0">
          <div className="card overflow-hidden p-0">
            <iframe 
              src="/api/v1/docs" 
              className="w-full h-[800px] border-0"
              title="Swagger UI Documentation"
            />
          </div>
        </TabsContent>

        <TabsContent value="redoc" className="mt-0">
          <div className="card overflow-hidden p-0">
            <iframe 
              src="/api/v1/docs/redoc" 
              className="w-full h-[800px] border-0"
              title="ReDoc API Documentation"
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}