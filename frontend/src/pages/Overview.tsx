import { lazy, useState, useRef, memo, useEffect, Suspense } from 'react'
const ActivityHelix = lazy(() => import('@/three/ActivityHelix').then(m => ({ default: m.ActivityHelix })))
import { motion } from 'framer-motion'
import { Shield, Zap, Lock, Globe, ArrowRight, Clock, Activity, Unlock, ScanLine, Layers } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useStore } from '@/store/useStore'
import { fireInitRipple } from '@/components/DashboardLayout'
import { stegoApi } from '@/services/api'
import { DecryptTitle } from '@/components/effects/DecryptTitle'

const TRANSITION = { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const }

const FEATURES = [
  { title: "Hide Message", desc: "Securely hide secret text or files inside an image", icon: Lock, link: "/embed", color: "text-cyan-400", border: "border-cyan-500/30", bg: "bg-cyan-500/10" },
  { title: "Find Message", desc: "Recover hidden information from an image", icon: Unlock, link: "/extract", color: "text-purple-400", border: "border-purple-500/30", bg: "bg-purple-500/10" },
  { title: "AI Scanner", desc: "Smart detection to find hidden secrets in images", icon: ScanLine, link: "/analyze", color: "text-orange-400", border: "border-orange-500/30", bg: "bg-orange-500/10" },
  { title: "Bulk Action", desc: "Hide or find data in many images at once", icon: Layers, link: "/batch", color: "text-green-400", border: "border-green-500/30", bg: "bg-green-500/10" },
]

// ──────────────────────── Hyper Button ────────────────────────
function HyperButton({ onClick }: { onClick: () => void }) {
  const [progress, setProgress] = useState(0)
  const [filling, setFilling] = useState(false)
  const [complete, setComplete] = useState(false)
  const [clickRipples, setClickRipples] = useState<{ id: number; x: number; y: number }[]>([])
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const btnRef = useRef<HTMLButtonElement>(null)

  // Sonar Ripple components for the button
  const SonarRipples = () => (
    <div className="absolute inset-0 -z-10 pointer-events-none">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute inset-0 rounded-2xl border border-primary/40 bg-primary/5"
          initial={{ opacity: 0, scale: 1 }}
          animate={{ opacity: [0, 0.4, 0], scale: [1, 1.4, 1.8] }}
          transition={{
            duration: 3,
            repeat: Infinity,
            delay: i * 1,
            ease: "easeOut"
          }}
        />
      ))}
    </div>
  )

  const startFill = () => {
    if (complete) return
    setFilling(true)
    if (intervalRef.current) clearInterval(intervalRef.current)
    intervalRef.current = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          if (intervalRef.current) clearInterval(intervalRef.current)
          setComplete(true)
          if (btnRef.current) {
            const r = btnRef.current.getBoundingClientRect()
            fireInitRipple(r.left + r.width / 2, r.top + r.height / 2)
          }
          setTimeout(onClick, 500)
          return 100
        }
        return p + 2.5 // Slightly smoother
      })
    }, 16)
  }

  const stopFill = () => {
    if (complete) return
    setFilling(false)
    if (intervalRef.current) clearInterval(intervalRef.current)
    setProgress(0)
  }

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (complete) return
    
    // Immediate activation on click if not already complete
    if (intervalRef.current) clearInterval(intervalRef.current)
    setComplete(true)
    setProgress(100)
    
    const rect = (e.currentTarget as HTMLButtonElement).getBoundingClientRect()
    const id = Date.now()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    setClickRipples(prev => [...prev, { id, x, y }])
    
    fireInitRipple(rect.left + rect.width / 2, rect.top + rect.height / 2)
    setTimeout(onClick, 400)
  }

  return (
    <motion.div
      className="relative inline-block"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...TRANSITION, delay: 0.8 }}
      whileHover={!complete ? {
        x: [0, -1.5, 1.5, -0.5, 0.5, 0],
        transition: { duration: 0.6, ease: 'easeInOut' }
      } : {}}
    >
      <button
        ref={btnRef}
        onMouseEnter={startFill}
        onMouseLeave={stopFill}
        onClick={handleClick}
        className="group relative overflow-hidden rounded-2xl border border-primary/40 bg-primary/10 px-14 py-5 text-sm font-black tracking-[0.4em] uppercase text-[var(--fg)] transition-all duration-300"
        style={{
          boxShadow: complete
            ? '0 0 60px var(--primary-glow)'
            : filling ? '0 0 30px var(--primary-glow)' : '0 0 15px rgba(0,242,255,0.05)',
        }}
      >
        {/* Click ripples */}
        {clickRipples.map(r => (
          <motion.span
            key={r.id}
            initial={{ opacity: 0.6, scale: 0 }}
            animate={{ opacity: 0, scale: 4 }}
            transition={{ duration: 0.65, ease: 'easeOut' }}
            className="absolute rounded-full bg-primary/30 pointer-events-none"
            style={{ left: r.x, top: r.y, width: 40, height: 40, translateX: '-50%', translateY: '-50%' }}
          />
        ))}

        {/* Fill Background */}
        <motion.div
          className="absolute inset-0 bg-primary/40 pointer-events-none"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: progress / 100 }}
          style={{ originX: 0 }}
          transition={{ duration: 0.1, ease: "linear" }}
        />
        
        {/* Progress Bar (Visible Edge) */}
        <motion.div
          className="absolute bottom-0 left-0 h-1 w-full bg-primary shadow-[0_0_15px_var(--primary-glow)] pointer-events-none"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: progress / 100 }}
          style={{ originX: 0 }}
          transition={{ duration: 0.1, ease: "linear" }}
        />

        {complete && <div className="absolute inset-0 bg-primary/30 animate-pulse" />}

        <SonarRipples />

        <span className="relative z-10 flex items-center gap-4">
          INITIALIZE SYSTEM
          <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-2" />
        </span>
      </button>
    </motion.div>
  )
}

// ─────────────────────── Feature Cards ───────────────────────
const highlights = [
  { icon: Shield, title: 'AI Scanner', desc: 'Securely check images for hidden data.' },
  { icon: Lock, title: 'Secure Hiding', desc: 'Hide data that stays invisible to others.' },
  { icon: Zap, title: 'Fast Results', desc: 'Instant encryption and processing.' },
  { icon: Globe, title: 'Works Everywhere', desc: 'Unified dashboard for all your needs.' },
]

// ─────────────────────── Page ───────────────────────
export const Overview = memo(function Overview() {
  const systemInitialized = useStore(s => s.systemInitialized)
  const setSystemInitialized = useStore(s => s.setSystemInitialized)
  const isAuthenticated = useStore(s => s.isAuthenticated)
  const theme = useStore(s => s.theme)
  const isLight = theme === 'light'

  // Auto-initialize if authenticated
  useEffect(() => {
    if (isAuthenticated && !systemInitialized) {
      setSystemInitialized(true)
    }
  }, [isAuthenticated, systemInitialized, setSystemInitialized])

  const [data, setData] = useState<{ analysis: any[]; files: any[]; activity: any[]; globalStats: any }>({ analysis: [], files: [], activity: [], globalStats: { total_scans: 0, threats_found: 0 } })
  const [isLoading, setIsLoading] = useState(false)

  const fetchDashboardData = async (isBackground = false) => {
    if (!isBackground) setIsLoading(true)
    try {
        const [filesRes, analysisRes, activityRes, statsRes] = await Promise.all([
            stegoApi.getFiles(),
            stegoApi.getAnalysisList(),
            stegoApi.getActivity(),
            stegoApi.getGlobalStats()
        ])
        setData({
            files: filesRes.data.success ? filesRes.data.data : [],
            analysis: analysisRes.data.success ? analysisRes.data.data : [],
            activity: activityRes.data.success ? activityRes.data.data : [],
            globalStats: statsRes.data.success ? statsRes.data.data : { total_scans: 0, threats_found: 0 }
        })
    } catch (err) {
        console.error("Dashboard fetch failed:", err)
    } finally {
        if (!isBackground) setIsLoading(false)
    }
  }

  useEffect(() => {
    let interval: any;
    if (isAuthenticated && systemInitialized) {
        interval = setInterval(() => {
            fetchDashboardData(true); // Background refresh (no loader)
        }, 10000);
    }
    return () => clearInterval(interval);
  }, [isAuthenticated, systemInitialized]);

  useEffect(() => {
    if (isAuthenticated && systemInitialized) {
        fetchDashboardData()
    }
  }, [isAuthenticated, systemInitialized])

  // Compute stats
  const totalScans = data.globalStats?.total_scans || 0
  const threatsDetected = data.globalStats?.threats_found || 0
  const recentActivity = data.activity.slice(0, 5) // Now pulling from Unified DB logs

  return (
    <div className="relative min-h-screen w-full bg-transparent" style={{ zIndex: 3 }}>
      <div className={`relative ${isAuthenticated ? 'pt-24' : 'pt-28'} flex min-h-screen flex-col items-center justify-center px-4 text-center`} style={{ zIndex: 5 }}>

        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-10 inline-flex items-center gap-3 rounded-full border border-primary/20 bg-primary/10 px-6 py-2.5 backdrop-blur-xl"
        >
          <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
          <span className="text-[10px] font-semibold tracking-wide text-primary">
            v3.1 Obsidian — Production
          </span>
        </motion.div>


        <div className="relative px-2" style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 900,
              letterSpacing: '-0.04em',
              textShadow: '4px 4px 8px rgba(0,0,0,0.2)',
              color: 'var(--fg-title)'
        }}>
          <DecryptTitle text="DEEPSTEGAI" className="text-5xl sm:text-7xl md:text-9xl select-none" />
        </div>

        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...TRANSITION, delay: 0.45 }}
          className="mt-8 max-w-xl text-sm sm:text-base font-medium leading-relaxed tracking-wide text-[var(--fg)] text-shadow-lg opacity-80"
        >
          Advanced steganography intelligence suite powered by AI forensic analysis.
        </motion.p>


        <div className="mt-14 w-full max-w-6xl">
          {!systemInitialized ? (
            <HyperButton onClick={() => setSystemInitialized(true)} />
          ) : (
            <div className="space-y-12">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={TRANSITION}
                    className="flex flex-wrap justify-center gap-4 sm:gap-6 px-4"
                >
                {!isAuthenticated ? (
                    <Link to="/auth" className="w-full sm:w-auto">
                        <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        className="w-full sm:w-auto rounded-2xl bg-primary px-12 py-5 text-sm font-bold tracking-wide text-[var(--btn-text)] shadow-[0_0_20px_rgba(0,242,255,0.3)] flex items-center justify-center gap-3 mx-auto"
                        >
                        <div className="bg-white p-1 rounded-lg">
                            <svg viewBox="0 0 24 24" className="w-4 h-4">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                            </svg>
                        </div>
                        Continue with Google
                        <ArrowRight className="h-4 w-4" />
                        </motion.button>
                    </Link>
                ) : (
                    <>
                    <style>{`
                      @keyframes marquee {
                        0% { transform: translateX(0); }
                        100% { transform: translateX(-50%); }
                      }
                      .animate-marquee {
                        animation: marquee 30s linear infinite;
                      }
                      .group:hover .animate-marquee {
                        animation-play-state: paused;
                      }
                      .marquee-mask {
                        mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent);
                        -webkit-mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent);
                      }
                    `}</style>
                    <div className="w-full relative overflow-hidden flex group group/marquee py-4 mt-2 marquee-mask">
                      <div className="flex gap-4 sm:gap-6 px-4 animate-marquee w-max">
                         {[...FEATURES, ...FEATURES, ...FEATURES].map((feat, i) => (
                           <Link key={i} to={feat.link} className="shrink-0 w-[240px] sm:w-[280px] transition-opacity duration-500 group-hover/marquee:opacity-40 hover:!opacity-100">
                              <div className={`h-full relative p-5 rounded-3xl border ${feat.border} ${feat.bg} backdrop-blur-md overflow-hidden transition-all duration-300 hover:scale-[1.03] hover:shadow-[0_0_30px_rgba(0,0,0,0.3)] hover:z-50 shadow-xl cursor-override`}>
                                 <div className="flex items-center gap-3 mb-2">
                                     <div className={`p-2.5 rounded-xl bg-black/40 ${feat.color}`}>
                                         <feat.icon strokeWidth={2.5} className="w-5 h-5" />
                                     </div>
                                     <h3 className="text-[13px] font-black tracking-[0.1em] text-[var(--fg)]">{feat.title}</h3>
                                 </div>
                                 <p className="text-xs text-[var(--fg-dim)] font-medium leading-relaxed whitespace-normal">{feat.desc}</p>
                              </div>
                           </Link>
                         ))}
                      </div>
                    </div>
                    </>
                )}
                </motion.div>

                {/* Real-time Stats Section */}
                {/* Fisheye Reverse Stats Marquee */}
                {isAuthenticated && (
                <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ ...TRANSITION, delay: 0.3 }}
                    className="w-full relative overflow-hidden flex flex-col group group/stats-marquee py-8 mb-4 marquee-mask"
                    style={{ perspective: '1200px' }}
                >
                    <style>{`
                      @keyframes marquee-reverse {
                        0% { transform: translateX(-33.333%); }
                        100% { transform: translateX(0); }
                      }
                      .animate-marquee-reverse {
                        animation: marquee-reverse 20s linear infinite;
                      }
                      .fisheye-card {
                        transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
                        transform-origin: center center;
                      }
                      /* Dim sibling cards to 40% */
                      .group-hover\\/stats-marquee .fisheye-card {
                        opacity: 0.4;
                        transform: scale(0.95);
                      }
                      /* Zoom hovered card slightly */
                      .group-hover\\/stats-marquee .fisheye-card:hover {
                        opacity: 1 !important;
                        transform: scale(1.03) !important;
                        z-index: 50;
                        box-shadow: 0 0 40px rgba(0, 242, 255, 0.25) !important;
                      }
                    `}</style>
                    <div className="flex gap-4 sm:gap-6 px-2 animate-marquee-reverse w-max items-center" style={{ transformStyle: 'preserve-3d' }}>
                        {(() => {
                            const baseStats = [
                                { label: 'Total Scans', val: isLoading ? '—' : totalScans.toString(), icon: Activity, color: 'text-primary' },
                                { label: 'Threats Found', val: isLoading ? '—' : threatsDetected.toString(), icon: Shield, color: threatsDetected > 0 ? 'text-red-500' : 'text-primary' },
                                { label: 'AI Accuracy', val: '99.98%', icon: Zap, color: 'text-primary' },
                                { label: 'System Status', val: 'Online', icon: Globe, color: 'text-green-500' },
                            ];
                            const defaultShadowLight = '0 10px 30px -15px rgba(0,184,196,0.3)';
                            const defaultShadowDark = '0 10px 30px -15px rgba(0,0,0,0.5)';
                            
                            return [...baseStats, ...baseStats, ...baseStats].map((s: any, i: number) => (
                                <div
                                    key={i}
                                    className={`fisheye-card shrink-0 w-[240px] sm:w-[280px] rounded-3xl px-8 py-8 border ${isLight ? 'bg-[#dff6ff]/80 border-primary/20' : 'bg-[var(--bg-card)]/80 border-[var(--border)]'} backdrop-blur-xl cursor-override`}
                                    style={{ '--default-shadow': isLight ? defaultShadowLight : defaultShadowDark } as any}
                                >
                                    <div className="flex items-center justify-between mb-4 text-[var(--fg-dim)]/50">
                                        <s.icon className={`h-5 w-5 ${s.color}`} />
                                        <span className="text-[10px] font-black tracking-widest uppercase">{s.label}</span>
                                    </div>
                                    <div className={`text-5xl font-black italic tracking-tighter ${s.color} ${!isLight && s.color === 'text-primary' ? 'glow-text' : ''}`}>{s.val}</div>
                                </div>
                            ))
                        })()}
                    </div>
                </motion.div>
                )}

                {/* Latest Activity Feed */}
                {isAuthenticated && (
                <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ ...TRANSITION, delay: 0.5 }}
                    className="px-4 text-left"
                >
                    <div className="flex items-center justify-between mb-6 px-2">
                        <div className="flex items-center gap-3">
                            <Clock className="h-4 w-4 text-primary" />
                            <h3 className="text-sm font-semibold tracking-wide text-[var(--fg)]">Recent Activity</h3>
                        </div>
                    </div>

                    {isLoading ? (
                        <div className={`p-6 rounded-[1.5rem] border ${isLight ? 'bg-white/60 border-primary/20 shadow-sm' : 'bg-[var(--bg-card)]/50 border-[var(--border)] shadow-md'} backdrop-blur-md`}>
                            <div className="flex flex-col gap-6">
                                {[1,2,3].map(i => (
                                    <div key={i} className="flex items-center gap-6">
                                        <div className="skeleton h-11 w-11 rounded-[14px] shrink-0" />
                                        <div className="flex-1 space-y-3">
                                            <div className="skeleton h-3 w-1/3 rounded" />
                                            <div className="skeleton h-2 w-1/4 rounded" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : recentActivity.length > 0 ? (
                        <Suspense fallback={
                            <div className={`h-[420px] rounded-3xl animate-pulse ${isLight ? 'bg-primary/5' : 'bg-white/[0.02]'}`} />
                        }>
                            <ActivityHelix activities={recentActivity} isLight={isLight} />
                        </Suspense>
                    ) : (
                        <div className={`flex flex-col items-center justify-center py-20 rounded-[1.5rem] border ${isLight ? 'bg-white/60 border-primary/20 shadow-sm' : 'bg-[var(--bg-card)]/50 border-[var(--border)] shadow-md'} backdrop-blur-md opacity-20`}>
                            <Activity className="h-12 w-12 mx-auto mb-6" />
                            <h3 className="text-sm font-black italic tracking-tight uppercase">No active telemetry data.</h3>
                            <p className="text-[9px] font-bold uppercase tracking-[0.2em] mt-2">Initialize forensic scan to begin monitoring.</p>
                        </div>
                    )}
                </motion.div>
                )}

                {/* Highlights (only shown if not authenticated or scrolled down) */}
                {!isAuthenticated && (
                  <div className="pb-24">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-4xl mx-auto">
                        {highlights.map((h, i) => (
                        <motion.div
                            key={i}
                            whileHover={{ y: -5 }}
                            className="group flex gap-6 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-8 text-left backdrop-blur-xl hover:bg-[var(--fg)]/5 transition-all shadow-xl"
                        >
                            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg)] group-hover:border-primary/50 group-hover:bg-primary/10 transition-all shadow-sm">
                            <h.icon className="h-7 w-7 text-[var(--fg-dim)] group-hover:text-primary transition-colors" />
                            </div>
                            <div>
                            <h3 className="text-sm font-black italic tracking-tight text-[var(--fg)] uppercase tracking-wider">{h.title}</h3>
                            <p className="mt-2 text-xs font-bold uppercase tracking-[0.15em] leading-relaxed text-[var(--fg-dim)]/60">{h.desc}</p>
                            </div>
                        </motion.div>
                        ))}
                    </div>

                    {/* Integrated Navigation Bridge: High-Visibility Cyan Theme */}
                    <motion.div 
                      initial={{ opacity: 0, y: 15 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      className="mt-12 flex flex-col items-center gap-6"
                    >
                      <div className={`w-px h-12 bg-gradient-to-b ${isLight ? 'from-cyan-500' : 'from-[#00f2ff]/50'} to-transparent`} />
                      <Link 
                        to="/about"
                        className={`
                          group relative px-10 py-4 rounded-2xl border-2 transition-all duration-300 overflow-hidden
                          ${isLight ? 'border-cyan-500 bg-white hover:bg-cyan-50 shadow-[0_10px_30px_rgba(6,182,212,0.15)]' : 'border-[#00f2ff]/30 bg-[#00f2ff]/5 hover:bg-[#00f2ff]/10'}
                        `}
                      >
                        <div className={`absolute inset-0 translate-y-full group-hover:translate-y-0 transition-transform duration-500 ${isLight ? 'bg-cyan-500/10' : 'bg-[#00f2ff]/10'}`} />
                        <span className={`
                          relative z-10 font-black tracking-[0.3em] uppercase text-xs flex items-center gap-3 transition-colors
                          ${isLight ? 'text-cyan-700 group-hover:text-cyan-800' : 'text-[#00f2ff]/80 group-hover:text-[#00f2ff]'}
                        `}>
                          Project Manifest
                          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </span>
                      </Link>
                      <p className={`text-[10px] font-mono uppercase tracking-[0.4em] ${isLight ? 'text-slate-500' : 'text-white/20'}`}>
                        DeepStegAI _ Intelligence Protocol v3.1
                      </p>
                    </motion.div>
                  </div>
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
})
