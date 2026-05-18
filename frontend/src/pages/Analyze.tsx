import { useState, useCallback, Suspense, memo, Component, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Canvas } from '@react-three/fiber'
import { Scanner3D } from '@/three/Scanner3D'
import { Search, Activity, BarChart, X, Brain, Info } from 'lucide-react'
import HeatmapViewer from '@/components/HeatmapViewer'
import { stegoApi } from '@/services/api'
import { useStore } from '@/store/useStore'
import { toast } from '@/components/Toaster'

// Error Boundary to prevent Canvas crashes from blanking the whole page
class CanvasErrorBoundary extends Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: any) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex items-center justify-center h-full text-[var(--fg-dim)] text-xs font-bold uppercase tracking-widest">
          3D Renderer unavailable
        </div>
      )
    }
    return this.props.children
  }
}

// ───────────────────────── Power Bar ─────────────────────────
function PowerBar({ progress, active }: { progress: number; active: boolean }) {
  const displayPct = Math.round(progress)

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex gap-1.5 h-14 items-end">
        {[...Array(12)].map((_, i) => {
          const threshold = (i / 11) * 100
          const isActive = active && progress >= threshold
          return (
            <motion.div
              key={i}
              className={`w-1.5 rounded-sm ${isActive ? 'bg-primary' : 'bg-[var(--border)]'}`}
              animate={{
                height: isActive ? '100%' : '18%',
                boxShadow: isActive ? '0 0 10px var(--primary-glow)' : 'none',
                opacity: isActive ? [0.75, 1, 0.8] : 0.2,
              }}
              transition={isActive ? { repeat: Infinity, duration: 0.3, ease: 'easeInOut' } : { duration: 0.3 }}
            />
          )
        })}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-xl font-black text-primary" style={{ textShadow: '0 0 12px var(--primary-glow)' }}>
          {active ? displayPct : '—'}
        </span>
        {active && <span className="font-mono text-xs font-bold text-primary/60">%</span>}
        <span className="font-mono text-[9px] font-black text-[var(--fg-dim)] tracking-widest ml-1">
          {active ? 'SCANNING' : 'STANDBY'}
        </span>
      </div>
    </div>
  )
}


export const Analyze = memo(function Analyze() {
  const [image, setImage] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<any | null>(null)
  const [showRing, setShowRing] = useState(false)
  const setStatus = useStore(state => state.setStatus)

  // Cleanup object URLs to prevent memory leaks
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (isScanning) return;
    const file = acceptedFiles[0]
    setImage(file)
    if (preview) URL.revokeObjectURL(preview)
    const newPreview = URL.createObjectURL(file)
    setPreview(newPreview)
    setResult(null); setProgress(0); setShowRing(false)
  }, [preview])

  const { getRootProps, getInputProps } = useDropzone({ onDrop, accept: { 'image/*': [] }, multiple: false })

  const handleClear = () => {
    if (preview) URL.revokeObjectURL(preview)
    setImage(null)
    setPreview(null)
    setResult(null)
    setShowRing(false)
    setIsScanning(false)
    setProgress(0)
    setStatus('READY')
  }

  const handleScan = async () => {
    if (!image) return

    if (!window.confirm('Executing a neural scan costs 2 Neural Credits. Proceed?')) return

    setIsScanning(true); setStatus('ANALYZING'); setProgress(0); setShowRing(false)
    
    // Smoother scan progress
    const timer = setInterval(() => {
        setProgress(p => {
          if (p < 45) return p + (Math.random() * 3 + 1.5)
          if (p < 80) return p + (Math.random() * 1 + 0.5)
          if (p < 98) return p + (Math.random() * 0.1)
          return p
        })
    }, 120)

    const formData = new FormData()
    formData.append('image', image)

    try {
      const res = await stegoApi.analyze(formData)
      clearInterval(timer); setProgress(100)
      
      // Delay result slightly to allow progress bar to be seen at 100%
      setTimeout(() => {
          const analysisData = res.data.success ? res.data.data : res.data
          setResult(analysisData)
          
          const isCompromised = analysisData.verdict !== 'CLEAN'
          setStatus(isCompromised ? 'COMPROMISED' : 'SECURE')
          setIsScanning(false)
          setShowRing(true)
          setTimeout(() => setShowRing(false), 2000)
      }, 600)
    } catch (err: any) {
      clearInterval(timer); setStatus('READY')
      setIsScanning(false)
      toast({
        title: "ANALYSIS FAILED",
        description: err.message || "An error occurred during AI analysis. Please try again.",
        type: "error"
      })
    }
  }

  const fetchGradCam = async () => {
    if (!image) throw new Error("Missing image");

    // If the scan verdict is CLEAN, there is no hidden data — show nothing.
    if (result && result.verdict === 'CLEAN') {
      throw new Error("__NO_SIGNAL__");
    }

    const fd = new FormData();
    fd.append('image', image);

    const response = await stegoApi.getGradCamHeatmap(fd);

    if (!response.data.success) {
      throw new Error(response.data.error || "Explainability synthesis failed");
    }

    // Backend returns null heatmap_b64 when it determines the image is clean
    if (!response.data.heatmap_b64) {
      throw new Error("__NO_SIGNAL__");
    }

    return "data:image/png;base64," + response.data.heatmap_b64;
  };


  return (
    <div className="h-full flex flex-col gap-2 max-w-7xl mx-auto overflow-y-auto pr-2 custom-scrollbar">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between w-full">
            <div>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--fg)] leading-none">AI Scanner</h2>
              <p className="text-xs font-medium mt-1 text-[var(--fg-dim)]">Check if an image has hidden data</p>
            </div>
            {preview && (
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                onClick={handleClear}
                className="mt-4 sm:mt-0 px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-xs font-semibold text-red-400 hover:bg-red-500/20 transition-all flex items-center justify-center gap-2"
              >
                <Search className="h-3 w-3 rotate-45" /> Reset Scanner
              </motion.button>
            )}
        </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 pb-4 pt-2">
        {/* LEFT PANEL (60%) */}
        <div className="md:col-span-3 flex flex-col gap-6 min-h-0 order-2 md:order-1">
          {!preview && (
            <div {...getRootProps()} className="lg:cursor-none">
              <input {...getInputProps()} />
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-[var(--bg-card)] border border-dashed border-[var(--border)] rounded-3xl p-6 flex flex-col items-center justify-center transition-all hover:bg-[var(--fg)]/[0.04] group min-h-[120px]"
              >
                <Search className="h-10 w-10 mb-3 text-[var(--fg-dim)]" />
                <p className="text-sm font-medium text-[var(--fg-dim)]">Drop image to scan</p>
              </motion.div>
            </div>
          )}

          <div className={`bg-[var(--bg-card)] border border-[var(--border)] rounded-3xl overflow-hidden min-h-[180px] md:min-h-0 flex-1 relative transition-all duration-700 ${
            result 
              ? (result.verdict !== 'CLEAN' 
                  ? 'shadow-[inset_0_0_50px_rgba(255,59,59,0.3)] border-red-500/50' 
                  : 'shadow-[inset_0_0_50px_rgba(0,255,156,0.3)] border-[#00FF9C]/50')
              : ''
          }`}>
            {preview && (
              <button 
                onClick={handleClear}
                className="absolute top-4 right-4 z-[100] p-1.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-500 hover:text-white hover:bg-red-500 transition-all lg:cursor-none shadow-[0_0_15px_rgba(239,68,68,0.3)]"
              >
                <X className="h-4 w-4" />
              </button>
            )}

            <CanvasErrorBoundary fallback={
              preview ? (
                <div className="flex items-center justify-center h-full p-4">
                  <img src={preview} alt="Preview" className="max-w-full max-h-full object-contain rounded-xl" />
                </div>
              ) : null
            }>
              <Suspense fallback={null}>
                <Canvas camera={{ position: [0, 0, 15] }}>
                  <ambientLight intensity={0.5} />
                  <pointLight position={[10, 10, 10]} intensity={1} color="#00f2ff" />
                  <Scanner3D image={preview || undefined} scanning={isScanning} />
                </Canvas>
              </Suspense>
            </CanvasErrorBoundary>

            {/* Glowing feedback ring - moved after canvas for stacking */}
            <AnimatePresence>
              {showRing && result && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.02 }}
                  key="result-ring"
                  className={`absolute inset-0 z-[50] pointer-events-none rounded-3xl border-[3px] transition-colors duration-700 ${
                    result.verdict !== 'CLEAN' ? 'border-red-500' : 'border-[#00FF9C]'
                  }`}
                  style={{
                    boxShadow: result.verdict !== 'CLEAN'
                      ? 'inset 0 0 80px rgba(255,59,59,0.5), 0 0 40px rgba(255,59,59,0.3)' 
                      : 'inset 0 0 80px rgba(0,255,156,0.5), 0 0 40px rgba(0,255,156,0.3)'
                  }}
                >
                  <motion.div 
                    animate={{ opacity: [0.3, 0.6, 0.3] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                    className={`absolute inset-0 rounded-3xl ${result.verdict !== 'CLEAN' ? 'bg-red-500/10' : 'bg-[#00FF9C]/10'}`}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {isScanning && (
                <div className="absolute top-4 left-4 sm:top-8 sm:left-8 z-[60]">
                    <PowerBar progress={progress} active={true} />
                </div>
            )}
          </div>

          {preview && !result && !isScanning && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
                <button onClick={handleScan} className="bg-primary hover:opacity-90 text-black px-12 py-4 rounded-2xl font-bold tracking-wide text-sm shadow-[0_0_20px_var(--primary-glow)] transition-all active:scale-95 w-full sm:w-auto">
                  Run AI Scan
                </button>
            </motion.div>
          )}
        </div>

        {/* RIGHT PANEL (40%) */}
        <div className="md:col-span-2 flex flex-col justify-center gap-6 min-h-0 order-1 md:order-2">
          <AnimatePresence mode="wait">
            {result ? (
              <motion.div
                key="result"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                 className="bg-[var(--bg-card)] border border-[var(--border)] rounded-3xl p-4 space-y-4"
              >
                <div>
                  <h4 className="text-[9px] font-semibold tracking-wide uppercase mb-4 text-[var(--fg-dim)]/50">Scan Result</h4>
                  <div className={`px-6 py-3 rounded-2xl border text-xs font-black tracking-[0.2em] italic uppercase text-center transition-all duration-500 ${
                    ! (result.verdict !== 'CLEAN')
                    ? 'bg-[#00FF9C]/10 border-[#00FF9C]/30 text-[#00FF9C] shadow-[0_0_20px_rgba(0,255,156,0.1)]'
                    : 'bg-[#FF3B3B]/10 border-[#FF3B3B]/30 text-[#FF3B3B] shadow-[0_0_20px_rgba(255,59,59,0.2)]'
                  }`}>
                      {result.verdict !== 'CLEAN' ? 'Hidden Secret Found' : 'No Secret Found'}
                  </div>
                </div>

                <div className="h-px bg-[var(--border)]" />

                <div>
                  <div className="flex justify-between items-end mb-3">
                    <span className="text-[9px] font-semibold tracking-wide uppercase text-[var(--fg-dim)]/70">AI Confidence</span>
                    <span className={`text-sm font-mono font-black ${result.verdict !== 'CLEAN' ? 'text-[#FF3B3B]' : 'text-[#00FF9C]'}`}>
                      {(result.ai_score * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-[var(--border)] rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${result.ai_score * 100}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        className={`h-full ${result.verdict !== 'CLEAN' ? 'bg-[#FF3B3B]' : 'bg-[#00FF9C]'}`}
                      />
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-[var(--fg)]/[0.03] border border-[var(--border)]">
                  <p className="text-[8px] font-semibold text-[var(--fg-dim)]/20 uppercase mb-2 tracking-wide">Details</p>
                  <p className={`text-[10px] font-bold italic leading-relaxed ${result.verdict !== 'CLEAN' ? 'text-[#FF3B3B]' : 'text-[var(--fg-dim)]'}`}>
                    {result.details?.extra?.description || "No anomalies detected."}
                  </p>
                </div>
              </motion.div>
            ) : (
                <div className="space-y-4">
                  <div className="glass-panel rounded-3xl p-4 bg-[var(--bg-sidebar)]">
                    <h4 className="text-[10px] font-black tracking-[0.4em] text-[var(--fg-dim)]/30 uppercase mb-6 flex items-center gap-2 italic">
                      <Activity className="h-4 w-4 text-primary" /> System Status
                    </h4>
                    <div className="space-y-4">
                      {[
                    { label: 'AI Engine', val: 'V4.2_ONLINE', color: 'text-primary' },
                        { label: 'Status', val: 'Online', color: 'text-[#00FF9C]' },
                        { label: 'Monitoring', val: 'Active', color: 'text-primary' },
                      ].map((item, idx) => (
                        <div key={idx} className="flex justify-between items-center text-[10px] pb-3 border-b border-[var(--border)] last:border-0 last:pb-0">
                           <span className="font-bold uppercase tracking-widest text-[var(--fg-dim)]/70">{item.label}</span>
                          <span className={`${item.color} font-mono font-black`}>{item.val}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-3xl p-4">
                    <h4 className="text-[10px] font-black tracking-[0.4em] text-[var(--fg-dim)]/30 uppercase mb-6 flex items-center gap-2 italic">
                      <BarChart className="h-4 w-4 text-accent" /> Monitoring
                    </h4>
                    <p className="text-[10px] text-[var(--fg-dim)]/20 font-bold italic leading-relaxed uppercase tracking-widest leading-relaxed">
                        Awaiting carrier analysis. Forensic node operating at full spectral capacity.
                    </p>
                  </div>
                </div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* 🧠 Model Explainability Section */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="mt-12 pt-12 border-t border-white/10 space-y-8 pb-20"
          >
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-blue-500/10 rounded-xl border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]">
                    <Brain className="w-6 h-6 text-blue-400 animate-pulse" />
                  </div>
                  <h2 className="text-3xl font-black italic tracking-tighter text-fg uppercase">Model Explainability</h2>
                </div>
                <p className="text-sm text-fg-dim font-medium max-w-2xl leading-relaxed">
                  Utilize <span className="text-blue-400 font-bold">Grad-CAM (Gradient-weighted Class Activation Mapping)</span> to visualize which regions 
                  of the image the AI model focused on to make its decision. Higher intensity areas indicate high suspicious neural activity.
                </p>
              </div>

              <div className="flex items-center gap-4 bg-white/5 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
                <div className="p-2 bg-purple-500/10 rounded-lg">
                  <Info className="w-4 h-4 text-purple-400" />
                </div>
                <p className="text-[10px] text-fg-dim/80 font-bold uppercase tracking-[0.1em] leading-tight max-w-[180px]">
                  Powered by custom StegoCNN Backpropagation Analysis.
                </p>
              </div>
            </div>

            <div className="max-w-4xl mx-auto">
              {preview && (
                <HeatmapViewer 
                  baseImage={preview} 
                  fetchHeatmap={fetchGradCam} 
                />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
})
