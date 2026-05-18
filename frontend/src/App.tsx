import { lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { DashboardLayout } from './components/DashboardLayout'
import { Toaster } from './components/Toaster'

// Lazy load pages for performance
const Overview = lazy(() => import('./pages/Overview').then(m => ({ default: m.Overview })))
const Embed    = lazy(() => import('./pages/Embed').then(m => ({ default: m.Embed })))
const Extract  = lazy(() => import('./pages/Extract').then(m => ({ default: m.Extract })))
const Analyze  = lazy(() => import('./pages/Analyze').then(m => ({ default: m.Analyze })))
const Batch    = lazy(() => import('./pages/Batch').then(m => ({ default: m.Batch })))
const Admin    = lazy(() => import('./pages/Admin').then(m => ({ default: m.Admin })))
const Support  = lazy(() => import('./pages/Support').then(m => ({ default: m.Support })))
const About    = lazy(() => import('./pages/About').then(m => ({ default: m.About })))
const Pricing  = lazy(() => import('./pages/Pricing').then(m => ({ default: m.Pricing })))
const Auth     = lazy(() => import('./pages/Auth').then(m => ({ default: m.Auth })))

import { useStore } from './store/useStore'
import { Navigate } from 'react-router-dom'

const TRANSITION = { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const }
const TOOL_PATHS = ['/embed', '/extract', '/analyze', '/batch', '/admin', '/support', '/pricing', '/auth']

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useStore(s => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AnimatedRoutes() {
  const location = useLocation()
  const isToolPage = TOOL_PATHS.includes(location.pathname)

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -16 }}
        transition={TRANSITION}
        className={`h-full ${isToolPage ? 'p-3' : ''}`}
      >
        <Suspense fallback={null}>
          <Routes location={location}>
            <Route path="/" element={<Overview />} />
            <Route path="/about" element={<About />} />
            <Route path="/auth" element={<Auth />} />
            <Route path="/login" element={<Navigate to="/auth" replace />} />
            <Route path="/signup" element={<Navigate to="/auth" replace />} />
            
            {/* Protected Routes */}
            <Route path="/embed"   element={<ProtectedRoute><Embed /></ProtectedRoute>} />
            <Route path="/extract" element={<ProtectedRoute><Extract /></ProtectedRoute>} />
            <Route path="/analyze" element={<ProtectedRoute><Analyze /></ProtectedRoute>} />
            <Route path="/batch"   element={<ProtectedRoute><Batch /></ProtectedRoute>} />
            <Route path="/admin"   element={<ProtectedRoute><Admin /></ProtectedRoute>} />
            <Route path="/support" element={<ProtectedRoute><Support /></ProtectedRoute>} />
            <Route path="/pricing" element={<ProtectedRoute><Pricing /></ProtectedRoute>} />
          </Routes>
        </Suspense>
      </motion.div>
    </AnimatePresence>
  )
}

function App() {
  return (
    <Router>
      <DashboardLayout>
        <AnimatedRoutes />
        <Toaster />
      </DashboardLayout>
    </Router>
  )
}

export default App
