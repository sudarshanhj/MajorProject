import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, File as FileIcon, Shield, Key, CheckCircle, Copy, AlertTriangle, Lock, X, Mail, Flame, Info, Eye, EyeOff } from 'lucide-react'
import HeatmapViewer from '@/components/HeatmapViewer'

import { stegoApi } from '@/services/api'
import { useStore } from '@/store/useStore'

// ───────────────────── Power Bar Component ─────────────────────
function PowerBar({ progress, active }: { progress: number; active: boolean }) {
  // Weighted easing: fast start, slows near 90%
  const displayPct = Math.round(progress)

  return (
    <div className="flex flex-col items-center gap-5">
      <div className="flex gap-2 h-20 items-end">
        {[...Array(14)].map((_, i) => {
          const threshold = (i / 13) * 100
          const isActive = active && progress >= threshold
          return (
            <motion.div
              key={i}
              className={`w-2 rounded-sm ${isActive ? 'bg-primary' : 'bg-[var(--border)]'}`}
              animate={{
                height: isActive ? '100%' : '15%',
                boxShadow: isActive ? '0 0 14px var(--primary-glow)' : 'none',
                opacity: isActive ? [0.75, 1, 0.85] : 0.2,
              }}
              transition={isActive ? { repeat: Infinity, duration: 0.35, ease: 'easeInOut' } : { duration: 0.3 }}
            />
          )
        })}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-3xl font-black text-primary tracking-tighter tabular-nums" style={{ textShadow: '0 0 16px var(--primary-glow)' }}>
          {active ? displayPct : '—'}
        </span>
        {active && <span className="font-mono text-sm font-bold text-primary/60">%</span>}
        <span className="font-mono text-[10px] font-black text-[var(--fg-dim)] tracking-widest ml-2">
          {active ? 'PROCESSING' : 'READY'}
        </span>
      </div>
    </div>
  )
}

export function Embed() {
  const [cover, setCover] = useState<File | null>(null)
  const [secrets, setSecrets] = useState<File[]>([])
  const [method, setMethod] = useState<'LSB' | 'Adaptive'>('LSB')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<{ image: string; token?: string; visualization?: any } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showSharePanel, setShowSharePanel] = useState(false)
  const [coverUrl, setCoverUrl] = useState<string | null>(null)
  const [capacity, setCapacity] = useState<{ text: string, bytes: number } | null>(null)

  const setStatus = useStore(s => s.setStatus)

  const onDropCover = useCallback((f: File[]) => { 
    if (isProcessing) return;
    if (f[0].size > 10 * 1024 * 1024) {
      setError("Cover image exceeds the 10MB upload limit.");
      setCover(null); setCapacity(null);
      return;
    }
    
    setCover(f[0]); setResult(null); setError(null); setCapacity(null);
    if (coverUrl) URL.revokeObjectURL(coverUrl);
    
    const url = URL.createObjectURL(f[0]);
    setCoverUrl(url);
  }, [coverUrl, isProcessing])

  // Cleanup object URLs to prevent memory leaks
  useEffect(() => {
    return () => {
      if (coverUrl) URL.revokeObjectURL(coverUrl)
    }
  }, [coverUrl])

  useEffect(() => {
    if (!cover) {
      setCapacity(null);
      return;
    }

    const fetchCapacity = async () => {
      try {
        const fd = new FormData();
        fd.append('cover', cover);
        fd.append('protocol', method);
        
        const res = await stegoApi.getCapacity(fd);
        if (res.data.success && res.data.data) {
          const { max_payload_bytes, max_payload_mb } = res.data.data;
          
          let displaySize = '';
          if (max_payload_mb >= 1) {
            displaySize = max_payload_mb.toFixed(2) + " MB";
          } else if (max_payload_bytes >= 1024) {
            displaySize = (max_payload_bytes / 1024).toFixed(1) + " KB";
          } else {
            displaySize = max_payload_bytes + " B";
          }
          
          setCapacity({ text: displaySize, bytes: max_payload_bytes });
        }
      } catch (err) {
        console.error("Failed to fetch capacity:", err);
        // Fallback or silent fail
      }
    };

    fetchCapacity();
  }, [cover, method])

  const onDropSecret = useCallback((f: File[]) => { 
    if (isProcessing) return;
    setSecrets(f); setResult(null); setError(null) 
  }, [isProcessing])

  const { getRootProps: getCoverProps, getInputProps: getCoverInputProps, isDragActive: isCoverActive } = useDropzone({ onDrop: onDropCover, accept: { 'image/*': [] }, multiple: false })
  const { getRootProps: getSecretProps, getInputProps: getSecretInputProps, isDragActive: isSecretActive } = useDropzone({ onDrop: onDropSecret, multiple: true })

  const handleEmbed = async () => {
    if (!cover || secrets.length === 0) return

    const totalSecretSize = secrets.reduce((acc, f) => acc + f.size, 0);
    if (capacity && totalSecretSize > capacity.bytes) {
       setError(`Payload too large! The secrets (${(totalSecretSize / 1024 / 1024).toFixed(2)} MB) exceed the max secure capacity for this cover (${capacity.text}).`);
       return;
    }

    if (!window.confirm('Embedding a payload costs 5 Neural Credits. Proceed?')) return

    setIsProcessing(true)
    setStatus('PROCESSING'); setError(null); setProgress(0)
    
    // Smooth progress: even distribution that doesn't "stick" at 93
    const timer = setInterval(() => {
      setProgress(p => {
        if (p < 40) return p + (Math.random() * 2 + 1)      // Initial fast start
        if (p < 75) return p + (Math.random() * 0.8 + 0.4)   // Steady middle
        if (p < 98) return p + (Math.random() * 0.2 + 0.05)  // Very slow crawl to keep it moving
        return p
      })
    }, 100)

    const fd = new FormData()
    fd.append('cover', cover); 
    secrets.forEach(s => fd.append('secret', s))
    fd.append('method', method); fd.append('password', password)

    try {
      const res = await stegoApi.embed(fd)
      clearInterval(timer); setProgress(100)
      
      const blob = res.data as Blob
      const imageUrl = URL.createObjectURL(blob)
      const token = res.headers['x-recovery-token']
      
      setTimeout(() => {
          setResult({
            image: imageUrl,
            token: token || undefined
          })
          setStatus('SECURE')
      }, 400)
    } catch (e: any) {
      clearInterval(timer)
      setError(e?.response?.data?.error || e?.message || 'Synthesis aborted.')
      setStatus('READY')
    } finally { setIsProcessing(false) }
  }

  const fetchDifferenceHeatmap = async () => {
    if (!cover || !result) throw new Error("Missing images");
    try {
      const fd = new FormData();
      fd.append('cover', cover);
      
      let blob: Blob;
      if (result.image.startsWith('blob:')) {
        const res = await fetch(result.image);
        blob = await res.blob();
      } else {
        // Fallback for legacy base64 if any remains
        const b64Data = result.image.split(',')[1];
        const byteCharacters = atob(b64Data);
        const byteArrays = [];
        for (let offset = 0; offset < byteCharacters.length; offset += 1024) {
          const slice = byteCharacters.slice(offset, offset + 1024);
          const byteNumbers = new Array(slice.length);
          for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
          }
          byteArrays.push(new Uint8Array(byteNumbers));
        }
        blob = new Blob(byteArrays, { type: 'image/png' });
      }
      
      fd.append('stego', new File([blob], 'stego.png', { type: 'image/png' }));
      
      const response = await stegoApi.getDifferenceHeatmap(fd);
      if (!response.data.success) throw new Error(response.data.error || "Synthesis failed");
      
      return "data:image/png;base64," + response.data.heatmap_b64;
    } catch (err: any) {
      console.error("Heatmap Error:", err);
      throw err;
    }
  };

  const handleGmailShare = () => {
    if (!result) return
    // Trigger file download first so the user can attach it
    const link = document.createElement('a')
    link.href = result.image
    link.download = 'deep_container.png'
    link.click()
    // Build the email body including the encryption key (if set)
    const keyLine = password
      ? `Encryption Key (AES-256 Key): ${password}`
      : 'Encryption Key (AES-256 Key): (No password was set for this container)'
    const subject = 'DeepStegAI — Stego Container'
    const body = `Hello,

I am sharing a steganography container generated using DeepStegAI.

⚠️ Important Notice:
This PNG file contains embedded hidden data. To preserve the hidden payload, please download and save the file exactly as received. Avoid sharing it in applications that may automatically recompress or modify the image.

Before sending this email, please attach the downloaded file (deep_container.png) to ensure the container is delivered correctly.

${keyLine}

Best regards,
DeepStegAI`
    
    // mailto: is MUCH more reliable for pre-filling multi-line bodies than the web-only Gmail cm URL
    window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  }

  return (
    <div className="h-full flex flex-col gap-2 max-w-6xl mx-auto overflow-y-auto custom-scrollbar pr-2">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 px-2 sm:px-0">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--fg)] leading-none">Hide Information</h2>
          <p className="text-xs font-medium mt-1 text-[var(--fg-dim)]">Hide a secret file inside an image</p>
        </div>
        <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-[var(--fg-dim)]">Clearance:</span>
            <span className="px-3 py-1 bg-primary/20 border border-primary/40 text-primary text-[9px] font-bold uppercase tracking-wide rounded-full shadow-[0_0_8px_var(--primary-glow)]">Level-04</span>
        </div>
      </div>

      <div className="shrink-0 grid grid-cols-1 lg:grid-cols-2 gap-4 pb-4">
        {/* Input Card */}
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-3xl p-4 flex flex-col gap-3 self-start">
          {/* Cover dropzone */}
          <div {...getCoverProps()} className={`relative h-24 sm:h-28 border border-dashed rounded-2xl flex items-center justify-center transition-all ${isCoverActive ? 'border-primary bg-primary/10' : 'border-[var(--border)] bg-[var(--bg-sidebar)] hover:border-primary/40'}`}>
            <input {...getCoverInputProps()} />
            {cover ? (
                <div className="text-center group w-full h-full flex flex-col items-center justify-center relative">
                    <button 
                      onClick={(e) => { e.stopPropagation(); setCover(null); setSecrets([]); setPassword(''); setResult(null); setError(null); setCapacity(null); if (coverUrl) { URL.revokeObjectURL(coverUrl); setCoverUrl(null); } }}
                      className="absolute top-3 right-3 p-1.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-500 hover:text-white hover:bg-red-500 transition-all shadow-[0_0_10px_rgba(239,68,68,0.2)] z-10"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                    <CheckCircle className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-primary mb-1.5" />
                    <p className="text-[9px] sm:text-[10px] font-black text-[var(--fg)] italic truncate max-w-[150px] sm:max-w-[200px] px-4 uppercase">{cover.name}</p>
                    
                    {capacity && (
                       <div className="mt-4 bg-[var(--bg)] px-5 py-2.5 rounded-full border-2 border-[var(--border)] shadow-lg backdrop-blur-sm transition-all group-hover:border-primary/50 group-hover:shadow-[0_0_20px_var(--primary-glow)]">
                          <p className="text-xs font-bold text-[var(--fg-dim)] tracking-wider uppercase">Max Secret Size: <span className="text-primary glow-text ml-1.5 font-black text-sm">{capacity.text}</span></p>
                       </div>
                    )}
                </div>
            ) : (
                <div className="text-center">
                    <Upload className="h-6 w-6 sm:h-8 sm:w-8 mx-auto mb-2 text-[var(--fg-dim)]" />
                    <p className="text-xs font-medium text-[var(--fg-dim)]">Drop cover image here</p>
                    <p className="text-[10px] text-[var(--fg-dim)]/50 mt-1">PNG, JPG, BMP supported</p>
                </div>
            )}
          </div>

          {/* Secret dropzone */}
          <div {...getSecretProps()} className={`relative h-12 border border-dashed rounded-xl flex items-center justify-center transition-all lg:cursor-none ${isSecretActive ? 'border-[var(--fg-dim)] bg-[var(--glass-bg)]' : 'border-[var(--border)] bg-[var(--bg-sidebar)] hover:border-[var(--fg-dim)]'}`}>
            <input {...getSecretInputProps()} />
            {secrets.length > 0 ? (
                <div className="flex items-center gap-3 px-6 w-full h-full relative">
                    <FileIcon className="h-4 w-4 sm:h-5 sm:w-5 text-primary shrink-0" />
                    <span className="text-[9px] sm:text-[10px] font-black text-[var(--fg)] truncate max-w-[150px] sm:max-w-[180px] uppercase italic">
                      {secrets.length === 1 ? secrets[0].name : `${secrets.length} Files Bundled`}
                    </span>
                    <CheckCircle className="h-3 w-3 sm:h-4 sm:w-4 text-primary shrink-0" />
                    <button 
                      onClick={(e) => { e.stopPropagation(); setSecrets([]); setPassword(''); setResult(null); setError(null); }}
                      className="ml-auto p-1 rounded-full text-red-500/60 hover:text-red-500 hover:bg-red-500/10 transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                </div>
            ) : (
                <div className="flex items-center gap-2 sm:gap-3"><Key className="h-4 w-4 text-[var(--fg-dim)]" /><p className="text-xs font-medium text-[var(--fg-dim)]">Drop secret file(s) here</p></div>
            )}
          </div>

          {/* Config */}
          <div className="grid grid-cols-2 gap-3">
            {(['LSB', 'Adaptive'] as const).map(m => (
              <button key={m} onClick={() => setMethod(m)}
                className={`py-2.5 rounded-xl text-[10px] font-black tracking-[0.3em] uppercase transition-all border ${method === m ? 'bg-primary/20 border-primary/50 text-primary glow-text' : 'bg-[var(--bg-sidebar)] border-[var(--border)] text-[var(--fg-dim)] hover:text-[var(--fg)]'}`}
              >
                {m === 'LSB' ? 'Standard' : 'Secure'} Method
              </button>
            ))}
          </div>

          <div className="relative group">
            <Lock className="absolute left-5 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--fg-dim)] group-focus-within:text-primary transition-colors" />
            <input type={showPassword ? "text" : "password"} placeholder={method === 'Adaptive' ? "Password (Required for Adaptive)" : "Password (Optional)"}
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

          <AnimatePresence>
            {error && (
              <motion.div layout initial={{ opacity: 0, height: 0, scale: 0.9 }} animate={{ opacity: 1, height: 'auto', scale: 1 }} exit={{ opacity: 0, height: 0, scale: 0.9 }} className="flex items-start gap-4 bg-red-500/10 border border-red-500/20 rounded-2xl p-4 overflow-hidden">
                <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-[10px] font-black text-red-400 tracking-widest leading-relaxed">{error}</p>
              </motion.div>
            )}
          </AnimatePresence>

          <motion.button layout disabled={!cover || secrets.length === 0 || isProcessing} onClick={handleEmbed}
            className="w-full bg-primary text-[var(--btn-text)] font-bold tracking-wide text-sm uppercase rounded-2xl py-3 shadow-[0_0_20px_var(--primary-glow)] hover:opacity-90 hover:shadow-[0_0_35px_var(--primary-glow)] transition-all active:scale-[0.98] disabled:opacity-30"
          >
            {isProcessing ? 'Processing...' : 'Start Hiding'}
          </motion.button>
          {/* trigger hmr */}
        </div>

        {/* Output Area */}
        <div className="flex flex-col h-full">
          <AnimatePresence mode="wait">
            {!result ? (
              <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full w-full glass-panel rounded-3xl flex flex-col items-center justify-center p-6 text-center border-dashed border-white/10 min-h-[400px]">
                <PowerBar progress={progress} active={isProcessing} />
                {!isProcessing && (
                    <div className="mt-10">
                        <Shield className="h-12 w-12 mx-auto text-[var(--fg-dim)]/20 mb-6" />
                        <h3 className="text-sm font-semibold text-[var(--fg-dim)]/30 mb-2">Ready</h3>
                        <p className="text-[10px] text-[var(--fg-dim)]/20 font-medium max-w-[200px] leading-loose">Drop images above to begin.</p>
                    </div>
                )}
              </motion.div>
            ) : (
              <motion.div key="result" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col gap-4 h-full">
                <div className="relative glass-panel rounded-3xl p-4 flex flex-col min-h-[300px] border-primary/20 bg-primary/[0.02]">
                    <div className="absolute top-4 right-4 z-10 px-4 py-1.5 bg-primary rounded-full text-[9px] font-bold uppercase text-black">Done!</div>
                    <div className="flex-1 flex items-center justify-center overflow-hidden rounded-2xl bg-[var(--bg-sidebar)] mt-10">
                        <img src={result.image} alt="Stego" className="max-w-full max-h-full object-contain" />
                    </div>
                </div>

                {result.token && (
                  <div className="glass-panel rounded-3xl p-5 border-primary/20 bg-primary/5">
                    <div className="flex items-center justify-between mb-3 text-[9px] font-black uppercase tracking-[0.4em] text-primary">
                      <span>Recovery Code</span>
                      <button onClick={() => navigator.clipboard.writeText(result.token!)} className="text-[var(--fg-dim)] hover:text-[var(--fg)] transition-colors">
                        <Copy className="h-4 w-4" />
                      </button>
                    </div>
                    <div className="bg-[var(--bg-sidebar)] rounded-xl p-3 font-mono text-[10px] break-all text-primary/80">{result.token}</div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex flex-col gap-3">
                  {/* Primary row: Download + Share toggle */}
                  <div className="grid grid-cols-2 gap-3">
                    <a
                      href={result.image}
                      download="deep_container.png"
                      className="bg-[var(--fg)] text-[var(--bg)] font-black tracking-[0.2em] text-[10px] uppercase rounded-2xl py-4 text-center transition-all hover:opacity-90 active:scale-[0.98] shadow-2xl glitch-hover"
                    >
                      Download
                    </a>

                    <button
                      onClick={() => setShowSharePanel(p => !p)}
                      className={`flex items-center justify-center gap-2 font-black tracking-[0.2em] text-[10px] uppercase rounded-2xl py-4 transition-all active:scale-[0.98] border ${
                        showSharePanel
                          ? 'bg-primary/30 border-primary/60 text-primary'
                          : 'bg-primary/20 border-primary/40 text-primary hover:bg-primary/30'
                      }`}
                    >
                      <Mail className="h-3.5 w-3.5" />
                      Share via Gmail
                    </button>
                  </div>

                  {/* Expandable share panel */}
                  <AnimatePresence>
                    {showSharePanel && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="flex flex-col gap-3 pt-1">
                          {/* Compression Warning — only visible when panel is open */}
                          <div className="flex items-start gap-3 bg-yellow-500/10 border border-yellow-500/20 rounded-2xl p-3">
                            <AlertTriangle className="h-3.5 w-3.5 text-yellow-400 shrink-0 mt-0.5" />
                            <p className="text-[9px] font-bold text-yellow-400/90 tracking-wider leading-relaxed">
                              <span className="font-black text-yellow-300">WhatsApp</span> compresses images and destroys hidden data.
                              Always share as a <span className="text-yellow-300 font-black">Document</span>, or use{' '}
                              <span className="text-yellow-300 font-black">Email</span> for full integrity.
                            </p>
                          </div>

                          {/* Gmail — only option */}
                          <button
                            onClick={handleGmailShare}
                            className="w-full flex items-center justify-center gap-2 font-black tracking-[0.15em] text-[10px] uppercase rounded-2xl py-3.5 transition-all active:scale-[0.98] border bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20 hover:border-red-500/50"
                          >
                            <Mail className="h-3.5 w-3.5" />
                            Open Gmail &amp; Download File
                          </button>

                          <p className="text-[8px] text-[var(--fg-dim)] font-bold uppercase tracking-widest text-center">
                            File auto-downloads — attach it in the Gmail compose window
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* 🔥 Heatmap Analysis Section */}
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
                  <div className="p-2.5 bg-orange-500/10 rounded-xl border border-orange-500/20 shadow-[0_0_15px_rgba(249,115,22,0.1)]">
                    <Flame className="w-6 h-6 text-orange-400 animate-pulse" />
                  </div>
                  <h2 className="text-3xl font-black italic tracking-tighter text-fg uppercase">Heatmap Analysis</h2>
                </div>
                <p className="text-sm text-fg-dim font-medium max-w-2xl leading-relaxed">
                  Generate a pixel-level <span className="text-orange-400 font-bold">Difference Map</span> to visualize exactly where data has been injected. 
                  This forensic tool isolates the steganographic modifications using the <span className="font-mono text-xs bg-white/5 px-2 py-0.5 rounded border border-white/10 uppercase tracking-widest">Hot Colormap</span>.
                </p>
              </div>

              <div className="flex items-center gap-4 bg-white/5 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Info className="w-4 h-4 text-blue-400" />
                </div>
                <p className="text-[10px] text-fg-dim/80 font-bold uppercase tracking-[0.1em] leading-tight max-w-[180px]">
                  Requires both original cover and generated stego container.
                </p>
              </div>
            </div>

            <div className="max-w-4xl mx-auto">
              <HeatmapViewer 
                baseImage={result.image} 
                fetchHeatmap={fetchDifferenceHeatmap} 
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
