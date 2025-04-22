"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"

type ToastProps = {
  id: string
  title: string
  description?: string
  type: "default" | "success" | "error" | "warning"
  duration?: number
  onClose: (id: string) => void
}

type ToastState = Omit<ToastProps, "onClose"> & { visible: boolean }

export const toastStore = {
  toasts: [] as ToastState[],
  listeners: new Set<() => void>(),
  
  getToasts: () => toastStore.toasts,
  
  addToast: (toast: Omit<ToastProps, "id" | "onClose">) => {
    const id = Math.random().toString(36).substring(2, 9)
    
    toastStore.toasts.push({
      id,
      title: toast.title,
      description: toast.description,
      type: toast.type || "default",
      duration: toast.duration || 3000,
      visible: true
    })
    
    toastStore.listeners.forEach(listener => listener())
    
    setTimeout(() => {
      toastStore.dismissToast(id)
    }, toast.duration || 3000)
    
    return id
  },
  
  dismissToast: (id: string) => {
    const index = toastStore.toasts.findIndex(t => t.id === id)
    
    if (index !== -1) {
      toastStore.toasts[index].visible = false
      toastStore.listeners.forEach(listener => listener())
      
      setTimeout(() => {
        toastStore.toasts = toastStore.toasts.filter(t => t.id !== id)
        toastStore.listeners.forEach(listener => listener())
      }, 300)
    }
  },
  
  subscribe: (listener: () => void) => {
    toastStore.listeners.add(listener)
    return () => toastStore.listeners.delete(listener)
  }
}

// Toast component
function Toast({ id, title, description, type, onClose }: ToastProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 50, scale: 0.8 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8, transition: { duration: 0.2 } }}
      transition={{ duration: 0.4, type: "spring" }}
      className={`
        p-4 rounded-lg shadow-lg flex items-start
        ${type === "success" && "bg-green-50 dark:bg-green-900 border-l-4 border-green-500"}
        ${type === "error" && "bg-red-50 dark:bg-red-900 border-l-4 border-red-500"}
        ${type === "warning" && "bg-amber-50 dark:bg-amber-900 border-l-4 border-amber-500"}
        ${type === "default" && "bg-white dark:bg-neutral-800"}
      `}
    >
      <div className="flex-1 pr-3">
        <h3 className={`font-medium
          ${type === "success" && "text-green-800 dark:text-green-200"}
          ${type === "error" && "text-red-800 dark:text-red-200"}
          ${type === "warning" && "text-amber-800 dark:text-amber-200"}
          ${type === "default" && "text-neutral-900 dark:text-neutral-100"}
        `}>
          {title}
        </h3>
        {description && (
          <p className={`mt-1 text-sm
            ${type === "success" && "text-green-700 dark:text-green-300"}
            ${type === "error" && "text-red-700 dark:text-red-300"}
            ${type === "warning" && "text-amber-700 dark:text-amber-300"}
            ${type === "default" && "text-neutral-700 dark:text-neutral-300"}
          `}>
            {description}
          </p>
        )}
      </div>
      <button 
        onClick={() => onClose(id)}
        className={`p-1 rounded-full
          ${type === "success" && "hover:bg-green-100 dark:hover:bg-green-800 text-green-700 dark:text-green-300"}
          ${type === "error" && "hover:bg-red-100 dark:hover:bg-red-800 text-red-700 dark:text-red-300"}
          ${type === "warning" && "hover:bg-amber-100 dark:hover:bg-amber-800 text-amber-700 dark:text-amber-300"}
          ${type === "default" && "hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300"}
        `}
      >
        <X className="h-4 w-4" />
      </button>
    </motion.div>
  )
}

// Toaster component
export function Toaster() {
  const [toasts, setToasts] = useState<ToastState[]>([])
  
  useEffect(() => {
    const unsubscribe = toastStore.subscribe(() => {
      setToasts([...toastStore.getToasts()])
    })
    
    return unsubscribe
  }, [])
  
  return (
    <div className="fixed bottom-0 right-0 p-4 mb-4 mr-4 w-full max-w-sm space-y-3 z-50 pointer-events-none">
      <AnimatePresence>
        {toasts.filter(t => t.visible).map(toast => (
          <div key={toast.id} className="pointer-events-auto">
            <Toast
              id={toast.id}
              title={toast.title}
              description={toast.description}
              type={toast.type}
              duration={toast.duration}
              onClose={toastStore.dismissToast}
            />
          </div>
        ))}
      </AnimatePresence>
    </div>
  )
}