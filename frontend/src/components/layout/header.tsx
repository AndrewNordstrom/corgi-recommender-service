"use client"

import { useState } from 'react'
import { useTheme } from 'next-themes'
import { Moon, Sun, Search, Github, User } from 'lucide-react'
import Link from 'next/link'

export default function Header() {
  const { theme, setTheme } = useTheme()
  const [searchQuery, setSearchQuery] = useState('')

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light')
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    // Implement search functionality
    console.log('Search for:', searchQuery)
  }

  return (
    <header className="sticky top-0 z-30 w-full border-b bg-background-light dark:bg-background-dark border-neutral-200 dark:border-neutral-800 backdrop-blur-sm">
      <div className="flex h-16 items-center px-6">
        <div className="flex flex-1 items-center">
          <form onSubmit={handleSearch} className="relative w-full max-w-md">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-neutral-500" />
            <input
              type="search"
              placeholder="Search documentation..."
              className="w-full rounded-md border border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-800 py-2 pl-9 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </form>
        </div>

        <div className="flex items-center space-x-4">
          <a 
            href="https://github.com/yourusername/corgi-recommender-service" 
            target="_blank" 
            rel="noopener noreferrer"
            className="hover:text-primary"
          >
            <Github className="h-5 w-5" />
            <span className="sr-only">GitHub</span>
          </a>

          <button
            onClick={toggleTheme}
            className="flex items-center justify-center h-9 w-9 rounded-md border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
          >
            {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            <span className="sr-only">Toggle theme</span>
          </button>

          <Link
            href="/dashboard"
            className="flex items-center justify-center h-9 w-9 rounded-md border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
          >
            <User className="h-5 w-5" />
            <span className="sr-only">User dashboard</span>
          </Link>
        </div>
      </div>
    </header>
  )
}