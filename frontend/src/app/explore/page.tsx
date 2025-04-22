"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader, RefreshCw, Code, Search } from "lucide-react"
import TimelinePost from "@/components/explore/timeline-post"
import TimelineControls from "@/components/explore/timeline-controls"
import JsonViewer from "@/components/explore/json-viewer"

// Example post types - these would match your API structure
type Post = {
  id: string;
  account: {
    id: string;
    username: string;
    display_name: string;
    avatar: string;
  };
  content: string;
  created_at: string;
  media_attachments: any[];
  favourites_count: number;
  reblogs_count: number;
  replies_count: number;
  tags: string[];
  is_recommendation?: boolean;
}

export default function ExplorePage() {
  const [loading, setLoading] = useState(false)
  const [posts, setPosts] = useState<Post[]>([])
  const [rawJsonVisible, setRawJsonVisible] = useState(false)
  const [activeTab, setActiveTab] = useState("visualization")
  const [injectionStrategy, setInjectionStrategy] = useState("uniform")

  // Mock function to fetch timeline - would be replaced with actual API call
  const fetchTimeline = async (params: any) => {
    setLoading(true)
    
    try {
      // In a real implementation, this would call your API
      // const response = await fetch('/api/v1/timelines/home', { params })
      // const data = await response.json()
      
      // For now, we'll use mock data
      setTimeout(() => {
        const mockPosts = generateMockPosts(params.strategy || 'uniform')
        setPosts(mockPosts)
        setLoading(false)
      }, 1000)
    } catch (error) {
      console.error('Error fetching timeline:', error)
      setLoading(false)
    }
  }

  // Generate mock posts for demo
  const generateMockPosts = (strategy: string): Post[] => {
    const posts: Post[] = []
    
    for (let i = 1; i <= 20; i++) {
      const isRecommendation = 
        strategy === 'uniform' ? i % 5 === 0 : 
        strategy === 'first_only' ? i === 1 :
        strategy === 'after_n' ? i === 5 :
        false
      
      posts.push({
        id: `post-${i}`,
        account: {
          id: `account-${i}`,
          username: `user${i}`,
          display_name: `User ${i}`,
          avatar: `https://i.pravatar.cc/150?u=${i}`
        },
        content: `This is a sample post #${i} with some content. It might contain #hashtags and @mentions.`,
        created_at: new Date(Date.now() - i * 600000).toISOString(),
        media_attachments: [],
        favourites_count: Math.floor(Math.random() * 50),
        reblogs_count: Math.floor(Math.random() * 20),
        replies_count: Math.floor(Math.random() * 10),
        tags: ['sample', i % 3 === 0 ? 'technology' : 'corgi'],
        is_recommendation: isRecommendation
      })
    }
    
    return posts
  }

  const handleFetchTimeline = (params: any) => {
    setInjectionStrategy(params.strategy || 'uniform')
    fetchTimeline(params)
  }

  return (
    <div className="container mx-auto">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-4">Timeline Explorer</h1>
        <p className="text-lg text-neutral-700 dark:text-neutral-300">
          Visualize and test timeline injection with different strategies.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <div className="card sticky top-24">
            <h2 className="text-xl font-bold mb-4">Controls</h2>
            <TimelineControls onFetch={handleFetchTimeline} />
            
            {posts.length > 0 && (
              <div className="mt-6 pt-6 border-t border-neutral-200 dark:border-neutral-700">
                <button
                  onClick={() => setRawJsonVisible(!rawJsonVisible)}
                  className="flex items-center text-sm font-medium text-accent hover:text-accent-dark"
                >
                  <Code className="mr-2 h-4 w-4" />
                  {rawJsonVisible ? 'Hide' : 'Show'} Raw JSON
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-3">
          <Tabs 
            value={activeTab} 
            onValueChange={setActiveTab}
            className="w-full"
          >
            <TabsList>
              <TabsTrigger value="visualization">
                Visualization
              </TabsTrigger>
              <TabsTrigger value="json">
                JSON View
              </TabsTrigger>
            </TabsList>

            <TabsContent value="visualization" className="mt-6">
              <div className="card">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-bold">Timeline Preview</h2>
                  
                  {posts.length > 0 && (
                    <button
                      onClick={() => fetchTimeline({ strategy: injectionStrategy })}
                      className="btn-secondary flex items-center text-sm px-3 py-1"
                      disabled={loading}
                    >
                      {loading ? (
                        <Loader className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="mr-2 h-4 w-4" />
                      )}
                      Refresh
                    </button>
                  )}
                </div>

                {loading ? (
                  <div className="flex justify-center items-center h-64">
                    <Loader className="h-8 w-8 animate-spin text-primary" />
                    <span className="ml-3 text-lg">Loading timeline...</span>
                  </div>
                ) : posts.length > 0 ? (
                  <div className="space-y-4">
                    {posts.map(post => (
                      <TimelinePost key={post.id} post={post} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg">
                    <Search className="h-12 w-12 mx-auto text-neutral-400" />
                    <h3 className="mt-4 text-lg font-medium">No timeline data</h3>
                    <p className="mt-2 text-neutral-500">
                      Use the controls to fetch a timeline with recommendations.
                    </p>
                  </div>
                )}
              </div>
              
              {rawJsonVisible && posts.length > 0 && (
                <div className="mt-6 card">
                  <h3 className="text-lg font-bold mb-4">Raw JSON Response</h3>
                  <JsonViewer data={posts} />
                </div>
              )}
            </TabsContent>

            <TabsContent value="json" className="mt-6">
              <div className="card">
                <h2 className="text-xl font-bold mb-4">JSON Data</h2>
                {posts.length > 0 ? (
                  <JsonViewer data={posts} expanded={true} />
                ) : (
                  <div className="text-center py-12 border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg">
                    <Code className="h-12 w-12 mx-auto text-neutral-400" />
                    <p className="mt-4 text-neutral-500">
                      Fetch a timeline to view the JSON data.
                    </p>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}