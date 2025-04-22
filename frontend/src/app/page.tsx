import Link from 'next/link'
import Image from 'next/image'
import { 
  ShieldCheck, 
  Code, 
  BarChart3, 
  Zap, 
  Cpu, 
  Users 
} from 'lucide-react'

const features = [
  {
    title: 'Privacy-First Design',
    description: 'User preferences and data handling fully transparent and configurable.',
    icon: ShieldCheck,
  },
  {
    title: 'Developer-Friendly API',
    description: 'Comprehensive API with Swagger documentation and example integrations.',
    icon: Code,
  },
  {
    title: 'Performance Metrics',
    description: 'Full visibility into system performance with Grafana dashboards.',
    icon: BarChart3,
  },
  {
    title: 'Fast Integration',
    description: 'Drop-in integration with Mastodon and other Fediverse platforms.',
    icon: Zap,
  },
  {
    title: 'Intelligent Recommendations',
    description: 'Advanced algorithms that respect user preferences and privacy.',
    icon: Cpu,
  },
  {
    title: 'Community Focused',
    description: 'Built for and with the Fediverse community for better engagement.',
    icon: Users,
  },
]

export default function Home() {
  return (
    <div className="container mx-auto">
      {/* Hero Section */}
      <section className="flex flex-col lg:flex-row items-center justify-between py-12 lg:py-24 gap-8">
        <div className="lg:w-1/2">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            A Privacy-Aware Recommender for the Fediverse
          </h1>
          <p className="text-xl mb-8 text-neutral-700 dark:text-neutral-300">
            Small body. Big brain. The Corgi Recommender Service provides intelligent content recommendations while respecting user privacy and preferences.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link href="/docs/quickstart" className="btn-primary px-6 py-3">
              Get Started
            </Link>
            <Link href="/api" className="btn-secondary px-6 py-3">
              API Documentation
            </Link>
          </div>
        </div>
        <div className="lg:w-1/2 flex justify-center">
          <div className="relative animate-pulse">
            <Image 
              src="/assets/corgi-hero.png" 
              alt="Corgi Mascot" 
              width={400} 
              height={300}
              priority
              className="object-contain"
            />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-12 bg-neutral-50 dark:bg-neutral-900 rounded-lg px-6">
        <h2 className="text-3xl font-bold text-center mb-12">Key Features</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <div key={index} className="card flex flex-col items-start">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <Icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="text-xl font-bold mb-2">{feature.title}</h3>
                <p className="text-neutral-700 dark:text-neutral-300">{feature.description}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* Getting Started Section */}
      <section className="py-12">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Start Using Corgi Today</h2>
          <p className="text-xl text-neutral-700 dark:text-neutral-300 max-w-3xl mx-auto">
            Following our quick setup guide to integrate the Corgi Recommender Service with your Fediverse application.
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-6">
          <Link href="/docs" className="card w-full md:w-64 text-center hover:border-primary transition-colors">
            <h3 className="text-lg font-bold mb-2">Read the Docs</h3>
            <p className="text-sm text-neutral-700 dark:text-neutral-300">Comprehensive documentation to get you started</p>
          </Link>
          
          <Link href="/api" className="card w-full md:w-64 text-center hover:border-primary transition-colors">
            <h3 className="text-lg font-bold mb-2">API Reference</h3>
            <p className="text-sm text-neutral-700 dark:text-neutral-300">Explore the API endpoints with Swagger UI</p>
          </Link>
          
          <Link href="/dashboard" className="card w-full md:w-64 text-center hover:border-primary transition-colors">
            <h3 className="text-lg font-bold mb-2">Get API Access</h3>
            <p className="text-sm text-neutral-700 dark:text-neutral-300">Create an account and get your API key</p>
          </Link>
        </div>
      </section>
    </div>
  )
}