import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Layers, Upload, CheckCircle, FileText, X, Zap, Key, AlertTriangle, Eye, EyeOff } from 'lucide-react'
import { stegoApi } from '@/services/api'
import { useStore } from '@/store/useStore'

function PowerBar({ progress, active }: { progress: number; active: boolean }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex gap-1 h-12 items-end">
        {[...Array(10)].map((_, i) => {
          const threshold = (i / 9) * 100
          const isActive = active && progress >= threshold
          return (
            <motion.div
              key={i}
              className={`w-1 rounded-sm transition-all duration-300 ${isActive ? 'bg-primary shadow-[0_0_8px_var(--primary-glow)]' : 'bg-[var(--border)]'}`}
              animate={{ height: isActive ? '100%' : '30%', opacity: isActive ? [0.7, 1, 0.8] : 0.2 }}
              transition={isActive ? { repeat: Infinity, duration: 0.25 } : {}}
            />
          )
        })}
      </div>
      <div className="font-mono text-xs font-black text-primary tracking-tighter">
        {active ? `${progress.toFixed(0)}%` : 'BATCH_IDLE'}
      </div>
    </div>
  )
}

export function Batch() {
  const [files, setFiles] = useState<File[]>([])
  const [secret, setSecret] = useState<File | null>(null)
  const [mode, setMode] = useState<'hide' | 'extract' | 'scan'>('hide')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)
  const [batchResults, setBatchResults] = useState<any[] | null>(null)
  const [method, setMethod] = useState<'lsb' | 'adaptive'>('lsb')
  const setStatus = useStore(s => s.setStatus)

  const onDropFiles = useCallback((f: File[]) => { 
    if (isProcessing) return;
    setFiles(p => [...p, ...f].slice(0, 50)); setError(null) 
  }, [isProcessing])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop: onDropFiles, accept: { 'image/*': [] } })
  const { getRootProps: getSecretProps, getInputProps: getSecretInputProps } = useDropzone({ onDrop: f => { if (isProcessing) return; setSecret(f[0]) }, multiple: false })

  const handleBatch = async () => {
    if (files.length === 0 || (mode === 'hide' && !secret)) return

    let promptMsg = ''
    if (mode === 'hide') promptMsg = `Batch embedding will process ${files.length} files. Estimated cost: ${files.length * 2} Neural Credits. Proceed?`
    else if (mode === 'extract') promptMsg = `Batch extraction will process ${files.length} payloads. Estimated cost: ${files.length * 2} Neural Credits. Proceed?`
    else promptMsg = `Batch AI scan will process ${files.length} images. Estimated cost: ${files.length * 2} Neural Credits. Proceed?`

    if (!window.confirm(promptMsg)) return

    setIsProcessing(true); setStatus('PROCESSING'); setError(null); setIsSuccess(false); setProgress(0); setBatchResults(null)
    
    const timer = setInterval(() => {
        setProgress(p => {
          if (p < 50) return p + (Math.random() * 5 + 2)
          if (p < 85) return p + Math.random() * 1
          if (p < 98) return p + Math.random() * 0.1
          return p
        })
    }, 200)

    const fd = new FormData()
    
    try {
      if (mode === 'scan') {
        files.forEach(f => fd.append('images', f))
        const res = await stegoApi.batchAnalyze(fd)
        clearInterval(timer); setProgress(100)
        setBatchResults(res.data.data)
        setIsSuccess(true)
        setStatus('SECURE')
      } else {
        fd.append('mode', mode)
        fd.append('method', method)
        if (mode === 'hide') { 
            fd.append('password', password)
            files.forEach(f => fd.append('covers', f))
            fd.append('secret', secret!) 
        } else { 
            // The backend expects 'batch_keys' for bulk extraction
            fd.append('batch_keys', password)
            files.forEach(f => fd.append('stegos', f)) 
        }
        
        const res = await stegoApi.batch(fd)
        clearInterval(timer); setProgress(100)
        const url = window.URL.createObjectURL(new Blob([res.data]))
        const link = document.createElement('a'); link.href = url
        link.setAttribute('download', `deepsteg_batch_${mode}.zip`)
        document.body.appendChild(link); link.click(); link.remove()
        window.URL.revokeObjectURL(url)
        setTimeout(() => { setIsSuccess(true); setStatus('SECURE') }, 500)
      }
    } catch (e: any) {
      clearInterval(timer)
      setError(e?.response?.data?.error || e?.message || 'Batch operation aborted.')
      setStatus('READY')
    } finally { setIsProcessing(false) }
  }

  return (
    <div className={`h-full flex flex-col gap-2 max-w-7xl mx-auto overflow-hidden ${window.innerWidth > 768 ? 'cursor-override' : 'cursor-auto'}`}>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black italic tracking-tighter uppercase text-[var(--fg)] glow-text leading-none">Bulk Actions</h2>
          <p className="text-[var(--fg-dim)]/80 text-[9px] font-bold tracking-[0.3em] uppercase mt-1 italic">Work with many images at the same time</p>
        </div>
        <div className="flex bg-[var(--bg-sidebar)] p-1.5 rounded-2xl border border-[var(--border)] gap-1">
          {(['hide', 'extract', 'scan'] as const).map(m => (
            <button key={m} onClick={() => { setMode(m); setError(null); setIsSuccess(false); setBatchResults(null); setFiles([]); setSecret(null); setPassword(''); }}
              className={`px-5 py-3 rounded-xl text-[10px] font-black tracking-[0.3em] uppercase transition-all ${mode === m ? 'bg-primary text-[var(--btn-text)] shadow-[0_0_20px_var(--primary-glow)]' : 'text-[var(--fg-dim)]/30 hover:text-[var(--fg-dim)]/60'}`}
            >
              {m === 'hide' ? 'Hide' : m === 'extract' ? 'Find' : 'AI Scan'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-3 gap-3">
        {/* Dropzone Area */}
        <div className="xl:col-span-2 flex flex-col gap-3 min-h-0">
          <div {...getRootProps()} className={`relative h-28 border border-dashed rounded-3xl flex flex-col items-center justify-center transition-all ${isDragActive ? 'border-primary bg-primary/10' : 'border-[var(--border)] bg-[var(--bg-sidebar)] hover:border-primary/40 group'}`}>
            <input {...getInputProps()} />
            <Layers className={`h-8 w-8 mb-2 transition-all ${isDragActive ? 'text-primary scale-110' : 'text-[var(--fg-dim)]/20 group-hover:text-[var(--fg-dim)]/40'}`} />
            <p className="text-base font-bold italic tracking-tighter uppercase text-[var(--fg)] transition-colors">
              Add images to list
            </p>
            <p className="text-[9px] text-[var(--fg-dim)]/50 uppercase tracking-[0.4em] mt-2 font-bold italic">Capacity: 50 Units Concurrent</p>
          </div>

          <AnimatePresence>
            {files.length > 0 && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-[var(--bg-card)] border border-[var(--border)] rounded-3xl p-4 flex-1 min-h-0 flex flex-col gap-3">
                <div className="flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-2"><Zap className="h-4 w-4 text-primary" /><span className="text-[10px] font-black tracking-[0.4em] text-[var(--fg)] uppercase italic">Synchronization Locked ({files.length})</span></div>
                  <button onClick={() => { setFiles([]); setBatchResults(null); setIsSuccess(false); setStatus('READY'); setPassword(''); setSecret(null); }} className="text-[9px] text-red-500/40 hover:text-red-500 font-black uppercase tracking-widest transition-colors">Abort All</button>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 overflow-y-auto flex-1 pr-2">
                  {files.map((file, i) => (
                    <div key={i} className="flex items-center gap-3 bg-[var(--fg)]/[0.02] rounded-xl p-3 border border-[var(--border)] group">
                      <FileText className="h-4 w-4 text-[var(--fg-dim)]/20 shrink-0 group-hover:text-primary transition-colors" />
                      <span className="text-[10px] font-black italic text-[var(--fg-dim)]/50 truncate uppercase tracking-tighter">{file.name}</span>
                      <button onClick={() => setFiles(p => p.filter((_, j) => j !== i))} className="ml-auto text-[var(--fg-dim)]/20 hover:text-red-500 hover:bg-red-500/10 p-0.5 rounded-full transition-all">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Configuration */}
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-3xl p-4 flex flex-col gap-3 min-h-0">
          {mode === 'hide' && (
            <div className="space-y-4">
              <div className="space-y-2 px-2">
                <label className="text-[9px] font-bold tracking-[0.4em] text-[var(--fg-dim)]/40 uppercase italic">Scanner Accuracy</label>
                <div className="grid grid-cols-2 gap-2">
                  {(['lsb', 'adaptive'] as const).map(m => (
                    <button key={m} onClick={() => setMethod(m)}
                      className={`py-2.5 rounded-xl text-[9px] font-black tracking-widest uppercase transition-all border ${method === m ? 'bg-primary/20 border-primary/40 text-primary shadow-[0_0_15px_var(--primary-glow)]' : 'bg-[var(--bg-sidebar)] border-[var(--border)] text-[var(--fg-dim)] hover:text-[var(--fg)]'}`}
                    >
                      {m === 'lsb' ? 'Standard' : 'Secure'} Method
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-[9px] font-bold tracking-[0.4em] text-[var(--fg)] uppercase italic px-2">Secret File</label>
                <div {...getSecretProps()} className="relative h-24 border border-dashed rounded-2xl flex items-center justify-center border-[var(--border)] bg-[var(--bg-sidebar)] hover:border-accent/40 transition-all cursor-pointer">
                  <input {...getSecretInputProps()} />
                  {secret ? (
                    <div className="text-center group w-full h-full flex flex-col items-center justify-center relative">
                      <button 
                        onClick={(e) => { e.stopPropagation(); setSecret(null); }}
                        className="absolute top-2 right-2 p-1 rounded-full bg-red-500/20 border border-red-500/40 text-red-500 hover:text-white hover:bg-red-500 transition-all z-10"
                      >
                        <X className="h-3 w-3" />
                      </button>
                      <CheckCircle className="h-6 w-6 text-accent mx-auto mb-2" />
                      <p className="text-[10px] font-black text-[var(--fg)] italic truncate max-w-[150px] px-2 uppercase tracking-tighter">{secret.name}</p>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3 opacity-30 text-[var(--fg)]"><Upload className="h-5 w-5" /><p className="text-[10px] font-black uppercase tracking-widest italic">Stage Source</p></div>
                  )}
                </div>
              </div>
            </div>
          )}

          {mode !== 'scan' && (
            <div className="space-y-3">
                <label className="text-[9px] font-bold tracking-[0.4em] text-[var(--fg)] uppercase italic px-2">Security Settings</label>
                {mode === 'hide' ? (
                <div className="relative group">
                    <Key className="absolute left-5 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--fg-dim)]/30 group-focus-within:text-primary transition-colors" />
                    <input type={showPassword ? "text" : "password"} placeholder="GLOBAL_SESSION_KEY"
                    className="w-full bg-[var(--bg-sidebar)] border border-[var(--border)] rounded-2xl py-3 pl-14 pr-12 text-xs font-black tracking-[0.3em] focus:outline-none focus:border-primary/40 transition-all font-mono text-[var(--fg)] placeholder:text-[var(--fg-dim)]/20"
                    value={password} onChange={e => setPassword(e.target.value)}
                    />
                    <button 
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--fg-dim)]/40 hover:text-primary transition-colors"
                    >
                      {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                </div>
                ) : (
                <textarea placeholder={'S_KEY_01\nS_KEY_02\nS_KEY_03...'}
                    className="w-full bg-[var(--bg-sidebar)] border border-[var(--border)] rounded-2xl py-3 px-5 text-xs font-black focus:outline-none focus:border-primary/40 transition-all font-mono text-[var(--fg)] placeholder:text-[var(--fg-dim)]/20 resize-none h-20 tracking-widest"
                    value={password} onChange={e => setPassword(e.target.value)}
                />
                )}
            </div>
          )}

          <div className="flex-1 flex flex-col items-center justify-center py-4 text-center min-h-0">
            <AnimatePresence mode="wait">
                {isProcessing ? (
                    <div className="space-y-4">
                        <PowerBar progress={progress} active={true} />
                        <p className="text-[10px] font-black text-primary animate-pulse tracking-[0.2em] italic">PROCESSING CLUSTER...</p>
                    </div>
                 ) : batchResults ? (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="w-full h-full flex flex-col gap-3 min-h-0">
                        <div className="flex items-center justify-between px-2 shrink-0">
                            <span className="text-[10px] font-black uppercase text-primary/60 tracking-widest italic">Neural Scan Results</span>
                            <CheckCircle className="h-4 w-4 text-primary" />
                        </div>
                        <div className="flex-1 overflow-y-auto rounded-2xl bg-[var(--bg-sidebar)] border border-[var(--border)] p-2 space-y-1">
                            {batchResults.map((r, i) => (
                                <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-[var(--fg)]/[0.03] border border-[var(--border)] group hover:bg-[var(--fg)]/5 transition-colors">
                                    <div className="flex flex-col items-start truncate pr-4">
                                        <span className="text-[10px] font-black italic text-[var(--fg)] truncate w-full uppercase">{r.filename}</span>
                                        <span className="text-[8px] text-[var(--fg-dim)]/30 uppercase font-bold tracking-tighter">{r.heuristic}</span>
                                    </div>
                                    <div className={`px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-tighter ${r.verdict === 'CLEAN' ? 'text-green-500 bg-green-500/10 border border-green-500/20' : 'text-red-500 bg-red-500/10 border border-red-500/20 shadow-[0_0_10px_rgba(239,68,68,0.1)]'}`}>
                                        {r.verdict}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                 ) : isSuccess ? (
                    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex items-center gap-3 text-primary bg-primary/10 border border-primary/20 rounded-2xl p-5">
                        <CheckCircle className="h-6 w-6" />
                        <span className="text-[10px] font-black uppercase tracking-[0.3em]">Batch Package Exported</span>
                    </motion.div>
                 ) : error ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-3 text-red-500 bg-red-500/10 border border-red-500/20 rounded-2xl p-5 text-left">
                        <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                        <p className="text-[10px] font-black uppercase tracking-widest leading-relaxed">Cluster Error: <span className="normal-case">{error}</span></p>
                    </motion.div>
                 ) : (
                    <div className="opacity-10"><Layers className="h-10 w-10 mx-auto" /></div>
                 )}
            </AnimatePresence>
          </div>

          <button 
            disabled={files.length === 0 || (mode === 'hide' && !secret) || isProcessing} 
            onClick={handleBatch}
            style={{ color: '#ffffff' }}
            className="w-full bg-primary disabled:bg-primary/20 font-black tracking-[0.2em] text-[13px] uppercase rounded-2xl py-3 shadow-[0_0_30px_var(--primary-glow)] hover:opacity-90 transition-all active:scale-[0.98]"
          >
            {isProcessing ? 'Processing...' : 'Run Action'}
          </button>
        </div>
      </div>
    </div>
  )
}
