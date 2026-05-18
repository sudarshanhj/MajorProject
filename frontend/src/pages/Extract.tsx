import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Shield, FileDown, AlertTriangle, CheckCircle, Lock, X, Eye, EyeOff } from 'lucide-react'
import { stegoApi } from '@/services/api'
import { useStore } from '@/store/useStore'

function PowerBar({ progress, active }: { progress: number; active: boolean }) {
  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex gap-1.5 h-16 items-end">
        {[...Array(12)].map((_, i) => {
          const threshold = (i / 11) * 100
          const isActive = active && progress >= threshold
          return (
            <motion.div
              key={i}
              className={`w-1.5 rounded-sm transition-all duration-300 ${isActive ? 'bg-primary shadow-[0_0_12px_var(--primary-glow)]' : 'bg-[var(--border)]'}`}
              animate={{ height: isActive ? '100%' : '20%', opacity: isActive ? [0.7, 1, 0.8] : 0.3 }}
              transition={isActive ? { repeat: Infinity, duration: 0.2 } : {}}
            />
          )
        })}
      </div>
      <div className="font-mono text-2xl font-black text-primary tracking-tighter tabular-nums">
        {active ? `${progress.toFixed(0)}%` : 'READY'}
      </div>
    </div>
  )
}

export function Extract() {
  const [stego, setStego] = useState<File | null>(null)
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [token, setToken] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)
  const setStatus = useStore(s => s.setStatus)

  const onDrop = useCallback((f: File[]) => { 
    if (isProcessing) return;
    setStego(f[0]); setError(null); setIsSuccess(false); setProgress(0) 
  }, [isProcessing])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { 'image/*': [] }, multiple: false })

  const handleExtract = async () => {
    if (!stego) return

    if (!window.confirm('Extracting a payload costs 2 Neural Credits. Proceed?')) return

    setIsProcessing(true)
    setStatus('PROCESSING')
    setError(null); setIsSuccess(false); setProgress(0)
    
    const timer = setInterval(() => {
        setProgress(p => {
            if (p < 50) return p + Math.random() * 5
            if (p < 98) return p + Math.random() * 0.5
            return p
        })
    }, 150)

    const fd = new FormData()
    fd.append('stego', stego); fd.append('password', password); fd.append('recovery_token', token)
    
    try {
      const res = await stegoApi.extract(fd)
      clearInterval(timer); setProgress(100)
      
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      const cd = res.headers['content-disposition']
      let filename = 'extracted_payload.bin'
      if (cd) { const m = cd.match(/filename=["']?([^"';\r\n]+)["']?/); if (m) filename = m[1] }
      link.setAttribute('download', filename)
      document.body.appendChild(link); link.click(); link.remove()
      window.URL.revokeObjectURL(url)
      
      setTimeout(() => {
          setIsSuccess(true); setStatus('SECURE')
      }, 500)
    } catch (e: any) {
      clearInterval(timer)
      setError(e?.response?.data?.error || e?.message || 'Extraction aborted.')
      setStatus('READY')
    } finally { setIsProcessing(false) }
  }

  return (
    <div className={`h-full flex flex-col gap-3 max-w-3xl mx-auto`}>
      <div className="text-center px-2">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--fg)] leading-none">Find Hidden Data</h2>
        <p className="text-xs font-medium mt-1 text-[var(--fg-dim)]">Recover the secret file from an image</p>
      </div>

      <div className="flex-1 bg-[var(--bg-card)] border border-[var(--border)] rounded-3xl p-4 space-y-3 flex flex-col min-h-0 overflow-y-auto">
        {/* Drop zone */}
        <div {...getRootProps()} className={`relative h-28 sm:h-32 border border-dashed rounded-3xl flex flex-col items-center justify-center transition-all lg:cursor-none ${isDragActive ? 'border-primary bg-primary/10' : 'border-[var(--border)] bg-[var(--bg-sidebar)] hover:border-primary/40'}`}>
          <input {...getInputProps()} />
          <AnimatePresence mode="wait">
            {stego ? (
                <motion.div key="file" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="text-center px-4 relative w-full h-full flex flex-col items-center justify-center">
                    <button 
                      onClick={(e) => { e.stopPropagation(); setStego(null); setError(null); setIsSuccess(false); setStatus('READY'); setPassword(''); setToken(''); }}
                      className="absolute top-3 right-3 p-1.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-500 hover:text-white hover:bg-red-500 transition-all shadow-[0_0_10px_rgba(239,68,68,0.2)] z-10"
                    >
                      <X className="h-4 w-4" />
                    </button>
                    <div className="h-12 w-12 sm:h-16 sm:w-16 bg-primary/10 border border-primary/30 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Shield className="h-6 w-6 sm:h-8 sm:w-8 text-primary" />
                    </div>
                    <p className="text-xs sm:text-sm font-black italic text-[var(--fg)] uppercase tracking-tighter truncate max-w-[250px]">{stego.name}</p>
                    <p className="text-[8px] sm:text-[9px] text-primary font-black uppercase tracking-[0.2em] sm:tracking-[0.3em] mt-2">Image Validated ✓</p>
                </motion.div>
            ) : (
                <motion.div key="empty" className="text-center px-4">
                    <Upload className="h-8 w-8 sm:h-10 sm:w-10 mx-auto mb-3 text-[var(--fg-dim)]" />
                    <p className="text-sm font-medium text-[var(--fg-dim)]">Drop image here</p>
                    <p className="text-[10px] text-[var(--fg-dim)]/50 mt-1">Supports PNG, BMP, TIFF</p>
                </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Credentials */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
             <div className="relative group">
                <Lock className="absolute left-5 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--fg-dim)] group-focus-within:text-primary transition-colors" />
                <input type={showPassword ? "text" : "password"} placeholder="Password"
                    className="w-full bg-[var(--bg-sidebar)] border border-[var(--border)] rounded-2xl py-3 pl-14 pr-12 text-sm focus:outline-none focus:border-primary/40 transition-all font-mono text-[var(--fg)] placeholder:text-[var(--fg-dim)]/60"
                    value={password} onChange={e => setPassword(e.target.value)}
                />
                <button 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--fg-dim)] hover:text-primary transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
            </div>
            <div className="relative group">
                <Shield className="absolute left-5 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--fg-dim)] group-focus-within:text-primary transition-colors" />
                <input type="text" placeholder="Recovery token (optional)"
                    className="w-full bg-[var(--bg-sidebar)] border border-[var(--border)] rounded-2xl py-3 pl-14 pr-6 text-sm focus:outline-none focus:border-primary/40 transition-all font-mono text-[var(--fg)] placeholder:text-[var(--fg-dim)]/60"
                    value={token} onChange={e => setToken(e.target.value)}
                />
            </div>
        </div>

        {/* Progress / Status */}
        <div className="flex-1 flex flex-col items-center justify-center py-4">
            <AnimatePresence mode="wait">
                {isProcessing ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                        <PowerBar progress={progress} active={true} />
                    </motion.div>
                ) : isSuccess ? (
                    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex items-center gap-4 bg-primary/10 border border-primary/30 rounded-2xl p-6">
                        <CheckCircle className="h-10 w-10 text-primary" />
                        <div>
                            <p className="text-sm font-bold text-primary">Process Complete</p>
                            <p className="text-xs text-[var(--fg-dim)] font-medium mt-1">File downloaded successfully.</p>
                        </div>
                    </motion.div>
                ) : error ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-4 bg-red-500/10 border border-red-500/20 rounded-2xl p-5 w-full">
                        <AlertTriangle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-red-500 mb-2">Error</p>
                            <p className="text-xs font-bold text-red-500/80 leading-relaxed">{error}</p>
                        </div>
                    </motion.div>
                ) : (
                    <div className="text-center opacity-10">
                         <FileDown className="h-10 w-10 mx-auto mb-2 text-[var(--fg)]" />
                         <span className="text-[9px] font-medium tracking-wide text-[var(--fg)]">Ready</span>
                    </div>
                )}
            </AnimatePresence>
        </div>

        <button disabled={!stego || isProcessing} onClick={handleExtract}
          className="w-full bg-primary text-[var(--btn-text)] font-bold tracking-wide text-sm uppercase rounded-2xl py-3 shadow-[0_0_20px_var(--primary-glow)] hover:opacity-90 transition-all active:scale-[0.98] disabled:opacity-30"
        >
          {isProcessing ? 'Finding...' : 'Find File'}
        </button>
      </div>
    </div>
  )
}
