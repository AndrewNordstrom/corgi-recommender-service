"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { 
  X, 
  ArrowRight, 
  ArrowLeft, 
  CheckCircle, 
  Brain, 
  Beaker, 
  TrendingUp,
  Lightbulb,
  BookOpen,
  Zap
} from "lucide-react"

interface OnboardingStep {
  id: string
  title: string
  description: string
  target: string
  icon: React.ReactNode
  action?: string
}

const onboardingSteps: OnboardingStep[] = [
  {
    id: "welcome",
    title: "Welcome to Your ML Research Platform",
    description: "This is your comprehensive model management dashboard. Think of it as your research lab's mission control for recommendation systems.",
    target: "dashboard-header",
    icon: <Brain className="h-6 w-6" />,
    action: "Let's explore the key features that will streamline your research workflow."
  },
  {
    id: "model-registry",
    title: "Model Registry - Your Algorithm Library",
    description: "Register all your recommendation algorithms here. From simple collaborative filtering to complex neural networks - track versions, performance, and metadata.",
    target: "models-tab",
    icon: <Brain className="h-6 w-6" />,
    action: "Click to see how to register your first model."
  },
  {
    id: "ab-testing",
    title: "A/B Testing - Scientific Validation",
    description: "Design statistically rigorous experiments to compare models. Set up control groups, treatment groups, and track significance.",
    target: "experiments-tab", 
    icon: <Beaker className="h-6 w-6" />,
    action: "Essential for validating your research hypotheses."
  },
  {
    id: "performance",
    title: "Performance Analytics - Real-time Insights",
    description: "Monitor model performance with metrics like CTR, engagement, precision, and recall. Track trends and identify regressions.",
    target: "performance-tab",
    icon: <TrendingUp className="h-6 w-6" />,
    action: "Your research metrics dashboard."
  },
  {
    id: "quick-start",
    title: "Ready to Start?",
    description: "We've pre-loaded some demo models and sample data. You can start experimenting immediately or register your own algorithms.",
    target: "quick-start-section",
    icon: <Zap className="h-6 w-6" />,
    action: "Let's get you started with your first model!"
  }
]

interface OnboardingTourProps {
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
}

export default function OnboardingTour({ isOpen, onClose, onComplete }: OnboardingTourProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setIsVisible(true)
      setCurrentStep(0)
    }
  }, [isOpen])

  const handleNext = () => {
    if (currentStep < onboardingSteps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleComplete()
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleComplete = () => {
    setIsVisible(false)
    onComplete()
    // Mark as completed in localStorage
    localStorage.setItem('dashboard-onboarding-completed', 'true')
  }

  const handleSkip = () => {
    setIsVisible(false) 
    onClose()
  }

  if (!isVisible) return null

  const step = onboardingSteps[currentStep]

  return (
    <AnimatePresence>
      {isVisible && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            {/* Tour Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="w-full max-w-lg max-h-[90vh] overflow-y-auto"
            >
              <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700">
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-neutral-200 dark:border-neutral-700">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    {step.icon}
                  </div>
                  <div>
                    <h3 className="text-lg font-bold">{step.title}</h3>
                    <p className="text-sm text-neutral-500">
                      Step {currentStep + 1} of {onboardingSteps.length}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleSkip}
                  className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Content */}
              <div className="p-4 sm:p-6">
                <p className="text-neutral-700 dark:text-neutral-300 leading-relaxed mb-4 text-sm sm:text-base">
                  {step.description}
                </p>
                
                {step.action && (
                  <div className="p-3 sm:p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500 mb-4">
                    <div className="flex items-start space-x-2">
                      <Lightbulb className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                      <p className="text-xs sm:text-sm text-blue-800 dark:text-blue-300">
                        <strong>Research Tip:</strong> {step.action}
                      </p>
                    </div>
                  </div>
                )}

                {/* Progress Bar */}
                <div className="mt-4 sm:mt-6">
                  <div className="flex justify-between text-xs text-neutral-500 mb-2">
                    <span>Progress</span>
                    <span>{Math.round(((currentStep + 1) / onboardingSteps.length) * 100)}%</span>
                  </div>
                  <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
                    <motion.div 
                      className="bg-primary h-2 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${((currentStep + 1) / onboardingSteps.length) * 100}%` }}
                      transition={{ duration: 0.5, ease: "easeInOut" }}
                    />
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between p-4 sm:p-6 border-t border-neutral-200 dark:border-neutral-700">
                <button
                  onClick={handleSkip}
                  className="text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 text-xs sm:text-sm"
                >
                  Skip Tour
                </button>

                <div className="flex items-center space-x-2 sm:space-x-3">
                  {currentStep > 0 && (
                    <button
                      onClick={handlePrevious}
                      className="btn-secondary flex items-center text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-2"
                    >
                      <ArrowLeft className="h-3 w-3 sm:h-4 sm:w-4 mr-1" />
                      Previous
                    </button>
                  )}
                  
                  <button
                    onClick={handleNext}
                    className="btn-primary flex items-center text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-2"
                  >
                    {currentStep === onboardingSteps.length - 1 ? (
                      <>
                        <CheckCircle className="h-3 w-3 sm:h-4 sm:w-4 mr-1" />
                        Get Started
                      </>
                    ) : (
                      <>
                        Next
                        <ArrowRight className="h-3 w-3 sm:h-4 sm:w-4 ml-1" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
} 