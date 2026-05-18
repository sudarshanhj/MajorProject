import React, { useEffect, useRef } from 'react'
import { Terminal as TerminalIcon, ChevronUp, ChevronDown } from 'lucide-react'
import { useStore } from '@/store/useStore'

export function TerminalLog() {
  const logs = useStore((s) => s.logs)
  const [isOpen, setIsOpen] = React.useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { 
    if (isOpen) endRef.current?.scrollIntoView({ behavior: 'smooth' }) 
  }, [logs, isOpen])

  return (
    <div className={`fixed bottom-0 left-0 w-full z-40 transition-all duration-500 ${isOpen ? 'h-64' : 'h-10'} border-t border-white/5 bg-black/80 backdrop-blur-2xl`}>
      {/* Console Toggle Header */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="flex justify-between items-center px-6 h-10 cursor-pointer hover:bg-white/5 transition-colors border-b border-white/5"
      >
        <div className="flex items-center gap-2 text-[10px] font-black tracking-[0.2em] text-primary/60">
          <TerminalIcon className="h-3 w-3" />
          SYSTEM KERNEL CONSOLE
        </div>
        <div className="flex items-center gap-4 text-[9px] text-white/20 font-mono">
           <span>NODE: 127.0.0.1</span>
           {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
        </div>
      </div>

      {/* Log Feed */}
      <div className="p-6 h-[calc(100%-40px)] overflow-y-auto font-mono text-[11px] text-primary/50 scrollbar-hide">
        {logs.map((log, i) => (
          <div key={i} className="mb-2 flex gap-4">
            <span className="text-white/10 shrink-0">[{new Date().toLocaleTimeString()}]</span>
            <span className="leading-relaxed break-all">{log}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
