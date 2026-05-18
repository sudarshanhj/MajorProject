
import * as ToastPrimitive from '@radix-ui/react-toast'
import { Zap, X } from 'lucide-react'
import { create } from 'zustand'

export type ToastType = 'default' | 'success' | 'error' | 'credit'

interface Toast {
  id: string
  title: string
  description?: string
  type?: ToastType
}

interface ToastStore {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

export const useToast = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) => set((state) => ({ 
    toasts: [...state.toasts, { ...toast, id: Math.random().toString(36).substr(2, 9) }] 
  })),
  removeToast: (id) => set((state) => ({ 
    toasts: state.toasts.filter((t) => t.id !== id) 
  }))
}))

export const toast = (props: Omit<Toast, 'id'>) => {
  useToast.getState().addToast(props)
}

export function Toaster() {
  const { toasts, removeToast } = useToast()

  return (
    <ToastPrimitive.Provider swipeDirection="right">
      {toasts.map(function ({ id, title, description, type }) {
        const isCredit = type === 'credit'
        return (
          <ToastPrimitive.Root
            key={id}
            onOpenChange={(open) => {
              if (!open) removeToast(id)
            }}
            duration={isCredit ? 4000 : 5000}
            className={`
              group relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-xl border p-4 pr-8 shadow-lg transition-all
              data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full
              ${isCredit ? 'bg-primary/10 border-primary shadow-[0_0_20px_var(--primary-glow)] text-[var(--fg)]' : 'bg-[var(--bg-card)] border-[var(--border)] text-[var(--fg)]'}
            `}
          >
            <div className="flex w-full items-center gap-3">
              {isCredit && <Zap className="h-5 w-5 text-primary animate-pulse" />}
              <div className="flex flex-col gap-1">
                {title && (
                  <ToastPrimitive.Title className={`text-sm font-black italic tracking-widest uppercase ${isCredit ? 'text-primary' : ''}`}>
                    {title}
                  </ToastPrimitive.Title>
                )}
                {description && (
                  <ToastPrimitive.Description className="text-xs font-bold uppercase tracking-wider text-[var(--fg-dim)]/70">
                    {description}
                  </ToastPrimitive.Description>
                )}
              </div>
            </div>
            
            <ToastPrimitive.Close className="absolute right-2 top-2 rounded-md p-1 bg-transparent text-[var(--fg-dim)]/50 opacity-0 transition-opacity hover:text-[var(--fg)] focus:opacity-100 group-hover:opacity-100">
              <X className="h-4 w-4" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        )
      })}
      
      <ToastPrimitive.Viewport className="fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]" />
    </ToastPrimitive.Provider>
  )
}
