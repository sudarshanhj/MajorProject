import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence, useSpring, useMotionValue } from 'framer-motion'
import {
  Layers, Download, Upload,
  Cpu, X, Menu, Activity, Zap, ShieldCheck, Lock as LockIcon, HelpCircle, Users
} from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useStore } from '@/store/useStore'
import { DigitalRain } from '@/components/DigitalRain'
import { ThemeToggle } from '@/components/ThemeToggle'
import api from '@/services/api'
import { Suspense, lazy } from 'react'
import { Canvas } from '@react-three/fiber'
const NeuralSphere = lazy(() => import('@/three/NeuralSphere').then(m => ({ default: m.NeuralSphere })))



const navItems = [
  { path: '/', label: 'Dashboard', icon: Activity },
  { path: '/embed', label: 'Hide Message', icon: Upload },
  { path: '/extract', label: 'Find Hidden Data', icon: Download },
  { path: '/analyze', label: 'AI Image Scanner', icon: ShieldCheck },
  { path: '/batch', label: 'Multi-File Actions', icon: Layers },
  { path: '/admin', label: 'Admin Center', icon: LockIcon },
  { path: '/pricing', label: 'Top-Up Credits', icon: Zap },
  { path: '/support', label: 'Support', icon: HelpCircle },
  { path: '/about', label: 'About Us', icon: Users },
]

const TOOL_PATHS = ['/', '/embed', '/extract', '/analyze', '/batch', '/admin', '/support', '/pricing', '/about']

// ─────────────────────── Global Cursor ───────────────────────
// Ripple is exposed via a global event so Overview's init button can fire it
export function fireInitRipple(x: number, y: number) {
  window.dispatchEvent(new CustomEvent('init-ripple', { detail: { x, y } }))
}


function GlobalCursor() {
  const mouseX = useMotionValue(-100)
  const mouseY = useMotionValue(-100)
  const ringX = useSpring(mouseX, { stiffness: 1200, damping: 50 })
  const ringY = useSpring(mouseY, { stiffness: 1200, damping: 50 })
  
  const [hovered, setHovered] = useState(false)
  const [isClicked, setIsClicked] = useState(false)
  const [ripples, setRipples] = useState<{ id: number; x: number; y: number }[]>([])

  useEffect(() => {
    let rafId: number
    const move = (e: MouseEvent) => { 
      rafId = requestAnimationFrame(() => {
        mouseX.set(e.clientX)
        mouseY.set(e.clientY)
      })
    }
    const onDown = () => setIsClicked(true)
    const onUp   = () => setIsClicked(false)
    
    // Listen for custom ripple event (Initialization)
    const handleInitRipple = ((e: Event) => {
      const { x, y } = (e as any).detail;
      const id = Date.now()
      setRipples(prev => [...prev, { id, x, y }])
      // Secondary echo ripple
      setTimeout(() => {
        setRipples(prev => [...prev, { id: id + 1, x, y }])
      }, 150)
    }) as EventListener;

    // Optimize: mouseover fires only on element entry, not every move
    const onOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.closest('button, a, input, select, textarea, [role="button"]')) {
        setHovered(true)
      } else {
        setHovered(false)
      }
    }

    window.addEventListener('mousemove', move, { passive: true })
    window.addEventListener('mouseover', onOver, { passive: true })
    window.addEventListener('mousedown', onDown)
    window.addEventListener('mouseup', onUp)

    return () => {
      window.removeEventListener('init-ripple', handleInitRipple)
      window.removeEventListener('mousemove', move)
      window.removeEventListener('mouseover', onOver)
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('mouseup', onUp)
      cancelAnimationFrame(rafId)
    }
  }, [mouseX, mouseY])

  return (
    <>
      <AnimatePresence>
        {ripples.map(r => (
          <motion.div
            key={r.id}
            initial={{ opacity: 0.8, scale: 0.2, x: r.x, y: r.y, translateX: '-50%', translateY: '-50%' }}
            animate={{ opacity: 0, scale: 8 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            onAnimationComplete={() => setRipples(p => p.filter(i => i.id !== r.id))}
            className="pointer-events-none fixed top-0 left-0 z-[10001] h-16 w-16 rounded-full border-2 border-primary"
          />
        ))}
      </AnimatePresence>

      {/* Outer Ring — Spring Smoothed */}
      <motion.div
        className="pointer-events-none fixed top-0 left-0 z-[10000] rounded-full hidden md:block"
        style={{ x: ringX, y: ringY, translateX: '-50%', translateY: '-50%', transform: 'translateZ(0)', willChange: 'transform', borderColor: 'var(--primary)' }}
        animate={{
          width:  hovered ? 40 : 22,
          height: hovered ? 40 : 22,
          borderWidth: hovered ? 2 : 1.5,
          opacity: hovered ? 0.9 : 0.6,
          backgroundColor: hovered ? 'var(--primary-glow)' : 'transparent',
          boxShadow: hovered 
            ? '0 0 15px var(--primary-glow)' 
            : '0 2px 8px rgba(0,0,0,0.15)'
        }}
        transition={{ type: 'spring', stiffness: 800, damping: 40 }}
      />

      {/* Inner Dot — Direct Linked (Zero Lag) */}
      <motion.div
        className="pointer-events-none fixed top-0 left-0 z-[10000] rounded-full hidden md:block"
        style={{ x: mouseX, y: mouseY, translateX: '-50%', translateY: '-50%', transform: 'translateZ(0)', willChange: 'transform', backgroundColor: 'var(--primary)' }}
        animate={{ 
          scale: isClicked ? 0.6 : 1,
          width: hovered ? 2 : 4,
          height: hovered ? 2 : 4,
          boxShadow: '0 2px 6px rgba(0,0,0,0.2)'
        }}
      />
    </>
  )
}

// ─────────────────────── Layout ───────────────────────
export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setSidebarOpen] = useState(window.innerWidth >= 1024)
  const [isMobileMenuOpen, setMobileMenuOpen] = useState(false)
  const asideRef = useRef<HTMLElement>(null)
  const location = useLocation()
  const status = useStore((state) => state.status)
  const theme = useStore(s => s.theme)
  const serverStatus = useStore((state) => state.serverStatus)
  const setServerStatus = useStore((state) => state.setServerStatus)
  const systemInitialized = useStore(s => s.systemInitialized)
  const setSystemInitialized = useStore(s => s.setSystemInitialized)
  const isAuthenticated = useStore(s => s.isAuthenticated)
  const user = useStore(s => s.user)
  const logout = useStore(s => s.logout)
  const [pulseColor, setPulseColor] = useState<string | null>(null)

  const isToolPage = TOOL_PATHS.includes(location.pathname)
  // Sidebar only appears AFTER system initialization and successful authentication
  const showSidebar = systemInitialized && isAuthenticated

  const fetchUser = useStore(s => s.fetchUser)

  // Auto-initialize if landing on a tool page directly
  useEffect(() => {
    if (location.pathname !== '/' && !systemInitialized) {
      setSystemInitialized(true)
    }
  }, [location.pathname, systemInitialized, setSystemInitialized])

  // Sync user profile on mount
  useEffect(() => {
    if (isAuthenticated && !user) {
      fetchUser()
    }
  }, [isAuthenticated, user, fetchUser])

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setSidebarOpen(false)
      } else {
        setSidebarOpen(true)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname])

  // Poll /api/health every 30s
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.get('/health')
        setServerStatus('ONLINE')
      } catch (err) {
        setServerStatus('OFFLINE')
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [setServerStatus])

  // Sync sidebar offset for 3D sphere centering using ResizeObserver for precision
  useEffect(() => {
    if (!showSidebar) {
      document.documentElement.style.setProperty('--sidebar-offset', '0px');
      return;
    }

    const updateOffset = () => {
      if (asideRef.current && window.innerWidth >= 1024) {
        const width = asideRef.current.getBoundingClientRect().width;
        document.documentElement.style.setProperty('--sidebar-offset', `${width}px`);
      } else {
        document.documentElement.style.setProperty('--sidebar-offset', '0px');
      }
    };

    updateOffset();
    const observer = new ResizeObserver(updateOffset);
    if (asideRef.current) observer.observe(asideRef.current);
    window.addEventListener('resize', updateOffset);

    return () => {
      observer.disconnect();
      window.removeEventListener('resize', updateOffset);
    };
  }, [showSidebar, isSidebarOpen]);

  // System Status Style (Top Bar)
  const getStatusStyle = useCallback(() => {
    if (serverStatus === 'OFFLINE') return { color: 'text-red-500', hex: '#ef4444' }
    switch (status) {
      case 'ANALYZING':   return { color: 'text-primary',    hex: '#00f2ff' }
      case 'COMPROMISED': return { color: 'text-[#FF3B3B]',  hex: '#FF3B3B' }
      case 'SECURE':      return { color: 'text-[#00FF9C]',  hex: '#00FF9C' }
      case 'PROCESSING':  return { color: 'text-amber-400',  hex: '#fbbf24' }
      default:            return { color: 'text-white/40',   hex: 'transparent' }
    }
  }, [status])

  useEffect(() => {
    if (status !== 'READY') {
      const { hex } = getStatusStyle()
      setPulseColor(hex)
      const t = setTimeout(() => setPulseColor(null), 900)
      return () => clearTimeout(t)
    }
  }, [status, getStatusStyle])

  // Filter nav items: only "aravalli813@gmail.com" can see the Admin Panel
  // and they don't need the Support section as they are the operator
  const filteredNavItems = navItems.filter(item => {
    const isSuperAdmin = ['aravalli813@gmail.com', 'hjsudarshan18@gmail.com'].includes(user?.email || '');
    if (item.path === '/admin') {
      return isSuperAdmin;
    }
    if (item.path === '/support' || item.path === '/pricing') {
      return !isSuperAdmin;
    }
    return true;
  })

  return (
    <div className={`flex h-screen overflow-hidden text-[var(--fg)] relative select-none ${theme} ${window.innerWidth > 768 ? 'cursor-override' : ''}`} style={{ background: 'var(--bg)' }}>
      {/* ── Layer 1: Digital Rain (z-1) ── */}
      <DigitalRain />

      {/* ── Layer 2: Noise overlay (z-2) ── */}
      <div className="noise-overlay" style={{ zIndex: 2 }} />

      {/* ── Global Cursor (z-10000) ── */}
      <GlobalCursor />

      {/* ── Global 3D Background (z-1) ── */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 1 }}>
        <div className="absolute top-1/2 left-1/2 w-full h-screen -translate-x-1/2 -translate-y-1/2 flex items-center justify-center">
          <Suspense fallback={null}>
            <Canvas camera={{ position: [0, 0, 14], fov: 60 }} dpr={[1, 2]} gl={{ antialias: true, stencil: false }}>
              <ambientLight intensity={0.4} />
              <pointLight position={[10, 10, 10]} intensity={1.6} color="#00f2ff" />
              <NeuralSphere />
            </Canvas>
          </Suspense>
        </div>
      </div>

      {/* ── Viewport Edge Status Pulse ── */}
      <AnimatePresence>
        {pulseColor && (
          <motion.div
            key={pulseColor}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, boxShadow: `inset 0 0 80px ${pulseColor}44` }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="pointer-events-none fixed inset-0 z-[9999]"
          />
        )}
      </AnimatePresence>

      {/* ── Landing mode (before boot or unauthenticated) ── */}
      {!showSidebar ? (
        <>
          <div className="absolute top-6 right-6 sm:top-8 sm:right-8 z-[100] cursor-override">
            <ThemeToggle />
          </div>
          <main className="relative flex-1 overflow-y-auto overflow-x-hidden" style={{ zIndex: 3 }}>
            {children}
          </main>
        </>
      ) : (
        <>
          {/* Mobile Overlay */}
          <AnimatePresence>
            {isMobileMenuOpen && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setMobileMenuOpen(false)}
                className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[40] lg:hidden"
              />
            )}
          </AnimatePresence>

          {/* ── Sidebar (z-50 on mobile, z-20 on desktop) ── */}
          <motion.aside
            ref={asideRef}
            initial={false}
            animate={{ 
              x: (isMobileMenuOpen || window.innerWidth >= 1024) ? 0 : -300,
              width: isSidebarOpen ? 260 : (window.innerWidth >= 1024 ? 80 : 260),
              opacity: 1
            }}
            onUpdate={(latest) => {
              // Smooth transition for intermediate states during spring animation
              // @ts-ignore
              const w = latest.width;
              if (typeof w === 'number') {
                document.documentElement.style.setProperty('--sidebar-offset', `${w}px`);
              }
            }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className={`fixed inset-y-0 left-0 lg:relative flex flex-col shrink-0 border-r border-[var(--border)] bg-[var(--bg-sidebar)] z-[50] lg:z-[20] text-sm transition-colors duration-300`}
          >
            {/* Logo — always navigates to / */}
            <div className="flex h-12 items-center px-4 border-b border-[var(--border)]">
              <Link to="/" onClick={() => setSystemInitialized(false)} className="flex items-center gap-4 group lg:cursor-none">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/30 shadow-[0_0_15px_var(--primary-glow)] group-hover:shadow-[0_0_25px_var(--primary-glow)] transition-all">
                  <Cpu className="h-4 w-4 text-primary" />
                </div>
                <AnimatePresence>
                  {(isSidebarOpen || isMobileMenuOpen) && (
                    <motion.span
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -6 }}
                      transition={{ duration: 0.2 }}
                      className="text-lg font-black tracking-tighter glow-text whitespace-nowrap text-[var(--fg)]"
                    >
                      DEEP<span className="text-primary italic">STEG</span>AI
                    </motion.span>
                  )}
                </AnimatePresence>
              </Link>
              
              {/* Mobile Close Button */}
              <button 
                onClick={() => setMobileMenuOpen(false)}
                className="ml-auto p-2 text-[var(--fg-dim)] hover:text-[var(--fg)] lg:hidden"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Neural Credits Display */}
            <AnimatePresence>
              {(isSidebarOpen || isMobileMenuOpen) && user && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="px-4 py-3 border-b border-[var(--border)] bg-primary/5"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Zap className={`h-3 w-3 ${user.credits < 10 ? 'text-red-500 animate-pulse' : 'text-primary'}`} />
                      <span className="text-[10px] font-semibold tracking-wide uppercase opacity-60">Credits</span>
                    </div>
                    <span className={`text-xs font-mono font-bold ${user.credits < 10 ? 'text-red-500' : 'text-primary'}`}>
                      {['aravalli813@gmail.com', 'hjsudarshan18@gmail.com'].includes(user?.email || '') ? '∞' : user.credits}
                    </span>
                  </div>
                  <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: ['aravalli813@gmail.com', 'hjsudarshan18@gmail.com'].includes(user?.email || '') ? '100%' : `${Math.min(100, (user.credits / 50) * 100)}%` }}
                      className={`h-full ${user.credits < 10 ? 'bg-red-500' : 'bg-primary'}`}
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Nav */}
            <nav className="flex-1 space-y-1 p-3 mt-3 overflow-y-auto overflow-x-hidden">
              {filteredNavItems.map(item => {
                const isActive = location.pathname === item.path
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-3 rounded-2xl px-3 py-2 transition-all duration-200 group ${
                      isActive
                        ? 'bg-primary/10 text-primary border border-primary/20 shadow-[0_0_12px_var(--primary-glow)]'
                        : 'text-[var(--text-muted)] hover:text-primary hover:bg-primary/5'
                    }`}
                  >
                    <item.icon className={`h-4 w-4 shrink-0 transition-colors ${isActive ? 'text-primary' : 'text-[var(--text-muted)] group-hover:text-[var(--fg)]'}`} />
                    <AnimatePresence>
                      {(isSidebarOpen || isMobileMenuOpen) && (
                        <motion.span
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="text-sm font-semibold tracking-normal whitespace-nowrap"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </Link>
                )
              })}
            </nav>

            {/* Logout (Bottom of Nav) */}
            <div className="p-3 border-t border-[var(--border)]">
              <button
                onClick={() => {
                  logout()
                  setSystemInitialized(false)
                }}
                className={`flex items-center gap-3 w-full rounded-2xl px-3 py-2 text-red-500 hover:bg-red-500/10 transition-all`}
              >
                <X className="h-4 w-4 shrink-0" />
                <AnimatePresence>
                  {(isSidebarOpen || isMobileMenuOpen) && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-sm font-semibold tracking-normal whitespace-nowrap"
                    >
                      Sign Out
                    </motion.span>
                  )}
                </AnimatePresence>
              </button>
            </div>

            {/* Collapse (Desktop) */}
            <div className="p-3 border-t border-[var(--border)] hidden lg:block">
              <button
                onClick={() => setSidebarOpen(!isSidebarOpen)}
                className="flex w-full items-center justify-center rounded-2xl py-3 border border-[var(--border)] bg-[var(--fg)]/5 text-[var(--fg-dim)] hover:text-primary hover:border-primary/30 transition-all"
              >
                {isSidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              </button>
            </div>
          </motion.aside>

          {/* ── Main ── */}
          <main className="relative flex flex-col flex-1 min-w-0 overflow-hidden" style={{ zIndex: 10 }}>
            {/* Tool header */}
            {(isToolPage || window.innerWidth < 1024) && (
          <header className="flex h-14 sm:h-12 shrink-0 items-center justify-between px-4 lg:px-6 bg-[var(--bg-header)] backdrop-blur-2xl border-b border-[var(--border)]">
                <div className="flex items-center gap-4">
                  {/* Mobile Menu Toggle */}
                  <button 
                    onClick={() => setMobileMenuOpen(true)}
                    className="p-3 -ml-2 text-white/60 hover:text-white lg:hidden active:scale-90 transition-transform"
                    aria-label="Open Menu"
                  >
                    <Menu className="h-6 w-6" />
                  </button>

                  <div className="flex items-center gap-3">
                    <div className={`h-1.5 w-1.5 rounded-full bg-current animate-pulse ${getStatusStyle().color}`} />
                    <h2 className="text-[11px] font-semibold tracking-wide text-[var(--fg)]">
                      {navItems.find(i => i.path === location.pathname)?.label}
                    </h2>
                  </div>
                </div>
                
                <div className="flex items-center gap-4 sm:gap-6">
                  {/* Header Credit Counter (Compact) */}
                  {isAuthenticated && user && (
                    <div className={`flex items-center gap-2 px-2 py-0.5 rounded-md border ${user.credits < 10 ? 'bg-red-500/10 border-red-500/30' : 'bg-primary/5 border-primary/20'}`}>
                      <Zap className={`h-2.5 w-2.5 ${user.credits < 10 ? 'text-red-500' : 'text-primary'}`} />
                      <span className={`text-[10px] font-mono font-bold ${user.credits < 10 ? 'text-red-500' : 'text-primary'}`}>
                        {['aravalli813@gmail.com', 'hjsudarshan18@gmail.com'].includes(user?.email || '') ? 'INF' : user.credits}
                      </span>
                    </div>
                  )}
                  {isAuthenticated && user && (
                    <div className="hidden xl:flex items-center gap-2 px-3 py-1 rounded-full bg-primary/5 border border-primary/20">
                      <span className="text-[8px] font-black tracking-widest text-primary/40 uppercase">Operator</span>
                      <span className="text-[9px] font-mono font-bold text-primary truncate max-w-[120px]">
                        {user.email}
                      </span>
                    </div>
                  )}
                  <span className={`text-[10px] font-mono font-semibold tracking-wide hidden sm:inline-block ${getStatusStyle().color}`}>
                    {serverStatus === 'OFFLINE' ? 'Offline' : (status ? status.charAt(0) + status.slice(1).toLowerCase() : 'Ready')}
                  </span>
                  <div className="h-6 w-px bg-[var(--border)] hidden sm:block" />
                  <ThemeToggle />
                </div>
              </header>
            )}

            <div className="flex-1 overflow-y-auto overflow-x-hidden">
              {children}
            </div>
          </main>
        </>
      )}
    </div>
  )
}
