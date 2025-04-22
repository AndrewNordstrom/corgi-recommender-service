"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Loader } from "lucide-react"

export default function DocsPage() {
  const params = useParams()
  const router = useRouter()
  const [loading, setLoading] = useState(true)

  // Build the path to the MkDocs content
  const getDocsPath = () => {
    // The base MkDocs URL - read from environment variable
    const baseDocsUrl = process.env.NEXT_PUBLIC_DOCS_URL || "http://localhost:8000"
    
    if (!params.slug || params.slug.length === 0) {
      return baseDocsUrl
    }
    
    // Join slug parts to create path
    const path = Array.isArray(params.slug) ? params.slug.join('/') : params.slug
    return `${baseDocsUrl}/${path}`
  }

  // Handle iframe load event
  const handleIframeLoad = () => {
    setLoading(false)
  }

  // Log the URL being loaded
  const docsUrl = getDocsPath()
  
  return (
    <div className="container mx-auto">
      {loading && (
        <div className="flex justify-center items-center h-64">
          <Loader className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-lg">Loading documentation from {docsUrl}...</span>
        </div>
      )}
      
      <div className={`card overflow-hidden p-0 ${loading ? 'opacity-0' : 'opacity-100'}`}>
        <iframe
          id="docs-iframe"
          src={docsUrl}
          onLoad={handleIframeLoad}
          className="w-full min-h-[800px] border-0 transition-opacity duration-300"
          title="Documentation"
        />
      </div>
      
      {/* Optional: Fallback for when iframe cannot be loaded */}
      {!loading && (
        <div className="mt-6 text-center">
          <p className="text-neutral-600 dark:text-neutral-400">
            If the documentation doesn't load correctly, you can visit the{" "}
            <a
              href={docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:text-primary-dark"
            >
              standalone documentation site
            </a>
            .
          </p>
        </div>
      )}
    </div>
  )
}