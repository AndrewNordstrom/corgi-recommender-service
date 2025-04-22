"use client"

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import Image from 'next/image'
import { 
  BookOpen, 
  Code, 
  Home, 
  LayoutDashboard, 
  FileJson, 
  BarChart3, 
  GitBranch,
  Play,
  FileText
} from 'lucide-react'

const navItems = [
  { name: 'Home', href: '/', icon: Home },
  { name: 'Documentation', href: '/docs', icon: BookOpen },
  { name: 'API Reference', href: '/api', icon: Code },
  { name: 'Timeline Explorer', href: '/explore', icon: FileJson },
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Metrics', href: '/metrics', icon: BarChart3 },
]

const resourceLinks = [
  { name: 'GitHub Repository', href: 'https://github.com/yourusername/corgi-recommender-service', icon: GitBranch },
  { name: 'Live Demo', href: '/demo', icon: Play },
  { name: 'Quickstart Guide', href: '/docs/quickstart', icon: FileText },
]

export default function Sidebar() {
  const pathname = usePathname()

  const isActive = (path: string) => {
    if (path === '/') {
      return pathname === '/'
    }
    return pathname.startsWith(path)
  }

  return (
    <aside className="sidebar overflow-y-auto py-6 transition-all duration-200 ease-in-out">
      <div className="px-6 pb-6 mb-6 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center space-x-3">
          <div className="relative h-10 w-10 animate-bounce">
            <Image 
              src="/assets/corgi-mascot.png" 
              alt="Corgi Mascot"
              width={40}
              height={40}
            />
          </div>
          <div>
            <h1 className="text-lg font-bold">Corgi</h1>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">Recommender Service</p>
          </div>
        </div>
      </div>

      <nav className="px-2 space-y-1">
        <div className="mb-4">
          <h2 className="px-4 mb-2 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
            Main Navigation
          </h2>
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`nav-link flex items-center px-4 py-2.5 text-sm mb-1 rounded-md ${
                  isActive(item.href) ? 'active' : ''
                }`}
              >
                <Icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            )
          })}
        </div>

        <div className="pt-4 border-t border-neutral-200 dark:border-neutral-700">
          <h2 className="px-4 mb-2 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
            Resources
          </h2>
          {resourceLinks.map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                href={item.href}
                className="nav-link flex items-center px-4 py-2.5 text-sm mb-1 rounded-md"
              >
                <Icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            )
          })}
        </div>
      </nav>
    </aside>
  )
}