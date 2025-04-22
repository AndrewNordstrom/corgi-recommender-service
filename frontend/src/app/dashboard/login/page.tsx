"use client"

import { useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { Github, Mail, ArrowRight } from "lucide-react"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!email.trim()) {
      setMessage({ type: "error", text: "Please enter a valid email address" })
      return
    }
    
    setIsLoading(true)
    setMessage(null)
    
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false)
      setMessage({ 
        type: "success", 
        text: "Check your email for a login link" 
      })
      setEmail("")
    }, 1500)
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md opacity-0 animate-fade-in-up">
        <div className="card text-center">
          <div className="flex justify-center mb-6">
            <Image 
              src="/assets/corgi-mascot.png" 
              alt="Corgi Mascot" 
              width={80} 
              height={80}
              className="h-20 w-20" 
            />
          </div>
          
          <h1 className="text-2xl font-bold mb-2">Welcome to Corgi</h1>
          <p className="text-neutral-700 dark:text-neutral-300 mb-8">
            Log in to access your dashboard and API keys
          </p>
          
          <div className="space-y-4">
            <button className="w-full btn-secondary flex items-center justify-center py-2.5">
              <Github className="mr-2 h-5 w-5" />
              Continue with GitHub
            </button>
            
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-neutral-200 dark:border-neutral-700" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-2 bg-white dark:bg-neutral-800 text-neutral-500">
                  Or continue with
                </span>
              </div>
            </div>
            
            <form onSubmit={handleEmailSignIn} className="space-y-4">
              <div>
                <label htmlFor="email" className="sr-only">
                  Email address
                </label>
                <div className="relative">
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    placeholder="Enter your email address..."
                    className="w-full px-3 py-2.5 border border-neutral-200 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isLoading}
                  />
                  <div className="absolute inset-y-0 right-0 flex items-center pr-3">
                    <Mail className="h-5 w-5 text-neutral-400" />
                  </div>
                </div>
              </div>
              
              <button
                type="submit"
                className="w-full btn-primary flex items-center justify-center py-2.5"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span>Sending link...</span>
                ) : (
                  <>
                    Sign in with Email
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </button>
            </form>
            
            {message && (
              <div
                className={`p-3 rounded text-sm ${
                  message.type === "success"
                    ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                    : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                }`}
              >
                {message.text}
              </div>
            )}
          </div>
          
          <div className="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-700 text-center">
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              By signing in, you agree to our{" "}
              <Link href="#" className="text-primary hover:text-primary-dark">
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link href="#" className="text-primary hover:text-primary-dark">
                Privacy Policy
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}