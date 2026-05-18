import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

interface DecryptTitleProps {
  text: string
  highlightStart?: number
  highlightEnd?: number
  className?: string
  speed?: number
}

export function DecryptTitle({ 
  text, 
  highlightStart = 4, 
  highlightEnd = 8, 
  className = '',
  speed = 60 // ms per frame (slower)
}: DecryptTitleProps) {
  // Use a global window variable instead of sessionStorage.
  // This ensures it survives React Router navigation but RESETS when you hit Refresh (F5).
  const hasSeen = (window as any).__hasSeenDeepStegTitle === true
  const [displayText, setDisplayText] = useState(hasSeen ? text : '')
  const [isResolved, setIsResolved] = useState(hasSeen)

  useEffect(() => {
    if (hasSeen) return

    let iteration = 0
    const totalIterations = Math.floor(800 / speed) // Runs for exactly 800ms
    
    const interval = setInterval(() => {
      iteration += 1
      
      if (iteration >= totalIterations) {
        clearInterval(interval)
        setDisplayText(text)
        setIsResolved(true)
        ;(window as any).__hasSeenDeepStegTitle = true
      } else {
        setDisplayText(text.split('').map(() => CHARS[Math.floor(Math.random() * CHARS.length)]).join(''))
      }
    }, speed)

    return () => clearInterval(interval)
  }, [text, speed, hasSeen])

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, z: -20 }}
      animate={{ opacity: 1, scale: 1, z: 0 }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className={`relative inline-block overflow-hidden rounded-lg px-4 ${className}`}
      style={{ perspective: '800px', transformStyle: 'preserve-3d' }}
    >
      {/* Invisible lock layer: physically enforces the exact final dimensions */}
      <div className="relative flex justify-center gap-1.5 px-8 font-black tracking-tighter uppercase opacity-0 pointer-events-none select-none" aria-hidden="true">
        {text.split('').map((char, i) => (
          <span key={i} className={i >= highlightStart && i < highlightEnd ? 'italic' : ''}>
            {char}
          </span>
        ))}
      </div>

      {/* Absolute Scramble Layer: Bounded perfectly inside the locked size */}
      <div className={`absolute inset-y-0 left-8 right-8 flex justify-center gap-1.5 font-black tracking-tighter uppercase select-none ${isResolved ? 'resolved-title' : ''}`}>
        {displayText.split('').map((char, i) => {
          const isHighlight = i >= highlightStart && i < highlightEnd
          return (
            <span
              key={i}
              className={`transition-colors duration-300 ${isResolved ? (isHighlight ? 'text-[var(--primary)] italic glow-text' : 'text-[var(--fg)]') : 'text-[var(--primary)]/50'}`}
              style={{
                textShadow: isResolved && isHighlight ? '0 0 20px var(--primary-glow)' : 'none',
              }}
            >
              {char}
            </span>
          )
        })}
      </div>

      {/* Light Sweep Effect (Luxe Shimmer) - Strictly Bounded */}
      <motion.div
        animate={{ 
          left: ['-50%', '150%'],
          opacity: [0, 0.9, 0]
        }}
        transition={{ 
          duration: 3.5, 
          ease: "easeInOut", 
          repeat: Infinity,
          repeatDelay: 6.0
        }}
        className="absolute top-0 bottom-0 w-24 -skew-x-20 pointer-events-none"
        style={{
          background: 'linear-gradient(90deg, transparent, rgba(0, 242, 255, 0.4), rgba(255,255,255,0.9), rgba(0, 242, 255, 0.4), transparent)',
          mixBlendMode: 'screen',
          filter: 'blur(4px)'
        }}
      />

      {/* Hover Pulse Glow */}
      <motion.div
        className="absolute inset-0 rounded-lg pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-700"
        style={{
          boxShadow: '0 0 50px var(--primary-glow)',
          background: 'radial-gradient(circle, var(--primary-glow) 0%, transparent 70%)',
          zIndex: -1
        }}
      />
    </motion.div>
  )
}
