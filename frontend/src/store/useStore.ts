import { create } from 'zustand'

export type SystemStatus = 'READY' | 'PROCESSING' | 'ANALYZING' | 'SECURE' | 'COMPROMISED'

interface User {
  id: string
  email: string
  credits: number
}

interface SystemState {
  status: SystemStatus
  logs: string[]
  stats: { analyses: number; embedded: number; threats: number }
  systemInitialized: boolean
  isAuthenticated: boolean
  user: User | null
  theme: 'dark' | 'light'
  serverStatus: 'ONLINE' | 'OFFLINE'
  setStatus: (status: SystemStatus) => void
  addLog: (msg: string) => void
  incrementStat: (key: keyof SystemState['stats']) => void
  setSystemInitialized: (val: boolean) => void
  setAuthenticated: (val: boolean) => void
  setUser: (user: User | null) => void
  logout: () => void
  setLogin: (accessToken: string, user: User, remember: boolean) => void
  setTheme: (theme: 'dark' | 'light') => void
  toggleTheme: () => void
  setCredits: (credits: number) => void
  fetchUser: () => Promise<void>
  setServerStatus: (status: 'ONLINE' | 'OFFLINE') => void
}

export const useStore = create<SystemState>((set) => ({
  status: 'READY',
  logs: [`[${new Date().toLocaleTimeString()}] KERNEL_READY: DeepSteg AI Suite v1.0.4 initialized.`],
  stats: { analyses: 4, embedded: 2, threats: 1 },
  systemInitialized: false,
  isAuthenticated: !!(localStorage.getItem('access_token') || sessionStorage.getItem('access_token')),
  user: null,
  theme: (localStorage.getItem('theme') as 'dark' | 'light') || 'dark',
  serverStatus: 'ONLINE',

  setStatus: (status) => set((state) => ({
    status,
    logs: [...state.logs.slice(-49), `[${new Date().toLocaleTimeString()}] SIGNAL_CHANGE → ${status}`]
  })),

  addLog: (msg) => set((state) => ({
    logs: [...state.logs.slice(-49), `[${new Date().toLocaleTimeString()}] ${msg.toUpperCase()}`]
  })),

  incrementStat: (key) => set((state) => ({
    stats: { ...state.stats, [key]: state.stats[key] + 1 }
  })),

  setSystemInitialized: (val) => {
    set({ systemInitialized: val })
  },
  
  setAuthenticated: (val) => set({ isAuthenticated: val }),
  
  setUser: (user) => set({ user }),

  logout: () => {
    localStorage.removeItem('access_token')
    sessionStorage.removeItem('access_token')
    set({ isAuthenticated: false, user: null, systemInitialized: false })
    import('@/services/api').then(({ stegoApi }) => {
      stegoApi.logout().catch(() => {})
    })
  },

  setLogin: (accessToken, user, remember) => {
    if (remember) {
      localStorage.setItem('access_token', accessToken)
    } else {
      sessionStorage.setItem('access_token', accessToken)
    }
    set({ isAuthenticated: true, user })
  },

  setTheme: (theme) => {
    localStorage.setItem('theme', theme)
    set({ theme })
  },

  toggleTheme: () => set((state) => {
    const newTheme = state.theme === 'dark' ? 'light' : 'dark'
    localStorage.setItem('theme', newTheme)
    return { theme: newTheme }
  }),
  setCredits: (credits) => set((state) => ({
    user: state.user ? { ...state.user, credits } : null
  })),
  fetchUser: async () => {
    const { stegoApi } = await import('@/services/api')
    try {
      const res = await stegoApi.getCurrentUser()
      if (res.data.success) {
        set({ user: res.data.data, isAuthenticated: true })
      } else {
        set({ isAuthenticated: false, user: null })
      }
    } catch (err) {
      set({ isAuthenticated: false, user: null })
    }
  },
  setServerStatus: (s) => set({ serverStatus: s })
}))
