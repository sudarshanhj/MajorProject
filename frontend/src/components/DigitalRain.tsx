import { useEffect, useRef } from 'react'
import { useStore } from '@/store/useStore'

const HEX_CHARS = '0123456789ABCDEF01'
const FONT_SIZE = 13
const COLUMN_WIDTH = 18
const FPS = 30 // Cap at 30 FPS to save CPU/GPU

export function DigitalRain() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const theme = useStore(s => s.theme)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: false })! // Optimize for opaque background if possible

    let columns: { y: number; speed: number; chars: string[] }[] = []
    let animId: number
    let lastTime = 0

    const init = () => {
      const W = window.innerWidth
      const H = window.innerHeight
      canvas.width = W
      canvas.height = H

      const colCount = Math.floor(W / COLUMN_WIDTH)
      const prev = columns
      columns = Array.from({ length: colCount }, (_, i) => {
        if (prev[i]) return prev[i]
        return {
          y: Math.random() * -H,
          speed: 0.6 + Math.random() * 1.2,
          chars: Array.from({ length: 25 }, () => HEX_CHARS[Math.floor(Math.random() * HEX_CHARS.length)]), // Reduced length
        }
      })
    }

    const draw = (time: number) => {
      animId = requestAnimationFrame(draw)

      // Throttle to 30 FPS
      const delta = time - lastTime
      if (delta < 1000 / FPS) return
      lastTime = time

      const W = canvas.width
      const H = canvas.height

      // Use theme-aware background
      const isDark = document.documentElement.classList.contains('dark')
      
      // Clear with specified background color for better visibility in dark mode
      ctx.fillStyle = isDark ? '#0a0a0a' : '#ffffff'
      ctx.globalAlpha = 0.15
      ctx.fillRect(0, 0, W, H)
      ctx.globalAlpha = 1.0

      ctx.font = `${FONT_SIZE}px "JetBrains Mono", monospace`
      ctx.textAlign = 'center'

      for (let i = 0; i < columns.length; i++) {
        const col = columns[i]
        const x = i * COLUMN_WIDTH + COLUMN_WIDTH / 2

        for (let j = 0; j < col.chars.length; j++) {
          const charY = col.y - j * FONT_SIZE
          if (charY < -FONT_SIZE || charY > H + FONT_SIZE) continue

          const isHead = j === 0
          let alpha = isHead ? 0.7 : Math.max(0, 0.12 - j * 0.005)
          if (!isDark) alpha *= 0.5 
          if (alpha <= 0) continue

          ctx.fillStyle = isHead ? (isDark ? '#ffffff' : '#0f172a') : (isDark ? '#00f2ff' : '#0096a3')
          ctx.globalAlpha = alpha

          if (Math.random() > 0.99) {
            col.chars[j] = HEX_CHARS[Math.floor(Math.random() * HEX_CHARS.length)]
          }

          ctx.fillText(col.chars[j], x, charY)
        }

        col.y += col.speed * FONT_SIZE * 0.25
        if (col.y - col.chars.length * FONT_SIZE > H) {
          col.y = -20
          col.speed = 0.5 + Math.random() * 1.5
        }
      }
      ctx.globalAlpha = 1.0
    }

    init()
    animId = requestAnimationFrame(draw)

    const onResize = () => init()
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', onResize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-[1] will-change-transform"
      style={{ opacity: theme === 'light' ? 0.15 : 0.12 }} // Adjusted for theme differentiation
    />
  )
}
