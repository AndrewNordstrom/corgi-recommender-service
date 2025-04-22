"use client"

import { useState } from "react"

type JsonViewerProps = {
  data: any;
  expanded?: boolean;
  name?: string;
}

export default function JsonViewer({ data, expanded = false, name = "root" }: JsonViewerProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Format JSON with syntax highlighting using a basic approach rather than react-json-view
  const formatJSON = (json: any) => {
    const jsonStr = JSON.stringify(json, null, 2)
    return jsonStr.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (match) => {
        let cls = 'text-blue-600 dark:text-blue-400' // number or boolean
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'text-neutral-800 dark:text-neutral-300 font-bold' // key
          } else {
            cls = 'text-green-600 dark:text-green-400' // string
          }
        } else if (/true|false/.test(match)) {
          cls = 'text-amber-600 dark:text-amber-400' // boolean
        } else if (/null/.test(match)) {
          cls = 'text-red-600 dark:text-red-400' // null
        }
        return `<span class="${cls}">${match}</span>`
      }
    )
  }

  return (
    <div className="rounded-md overflow-hidden">
      <div className="bg-neutral-100 dark:bg-neutral-800 px-4 py-2 flex justify-between items-center">
        <span className="text-sm font-mono">{name}</span>
        <button 
          onClick={handleCopy}
          className="text-xs px-2 py-1 bg-neutral-200 dark:bg-neutral-700 rounded hover:bg-neutral-300 dark:hover:bg-neutral-600 transition-colors"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <div className="bg-white dark:bg-neutral-900 p-4 overflow-auto max-h-[500px]">
        <pre 
          className="font-mono text-sm" 
          dangerouslySetInnerHTML={{ __html: formatJSON(data) }}
        />
      </div>
    </div>
  )
}