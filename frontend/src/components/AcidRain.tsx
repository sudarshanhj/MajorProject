import { useEffect, useRef } from 'react'


const ACID_CHARS = '0123456789ABCDEF!@#$%^&*()_+'
const FONT_SIZE = 14
const COLUMN_WIDTH = 20
const FPS = 24 

export function AcidRain() {
  const canvasRef = useRef<HTMLCanvasElement>(null)


  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: false })!

    let columns: { y: number; speed: number; chars: string[]; melt: number }[] = []
    let animId: number
    let lastTime = 0

    const init = () => {
      const W = window.innerWidth
      const H = window.innerHeight
      canvas.width = W
      canvas.height = H

      const colCount = Math.floor(W / COLUMN_WIDTH)
      columns = Array.from({ length: colCount }, () => ({
        y: Math.random() * -H,
        speed: 0.5 + Math.random() * 1.5,
        chars: Array.from({ length: 20 + Math.floor(Math.random() * 15) }, () => ACID_CHARS[Math.floor(Math.random() * ACID_CHARS.length)]),
        melt: Math.random() * 0.1
      }))
    }

    const draw = (time: number) => {
      animId = requestAnimationFrame(draw)

      const delta = time - lastTime
      if (delta < 1000 / FPS) return
      lastTime = time

      const W = canvas.width
      const H = canvas.height
      const isDark = document.documentElement.classList.contains('dark')
      
      // Acidic smear effect
      ctx.fillStyle = isDark ? 'rgba(3, 7, 10, 0.1)' : 'rgba(255, 255, 255, 0.1)'
      ctx.fillRect(0, 0, W, H)

      ctx.font = `bold ${FONT_SIZE}px "JetBrains Mono", monospace`
      ctx.textAlign = 'center'

      for (let i = 0; i < columns.length; i++) {
        const col = columns[i]
        const x = i * COLUMN_WIDTH + COLUMN_WIDTH / 2

        for (let j = 0; j < col.chars.length; j++) {
          const charY = col.y - j * FONT_SIZE
          if (charY < -FONT_SIZE || charY > H + FONT_SIZE) continue

          const isHead = j === 0
          // "Acid" gradients: Cyan to Green/Dim
          if (isHead) {
            ctx.fillStyle = isDark ? '#00f2ff' : '#0096a3'
            ctx.globalAlpha = 0.8
          } else {
            // Toxic green/cyan mix for the tail
            ctx.fillStyle = isDark ? '#00ffaa' : '#00a36c'
            ctx.globalAlpha = Math.max(0, 0.3 - (j * 0.015))
          }

          if (Math.random() > 0.98) {
            col.chars[j] = ACID_CHARS[Math.floor(Math.random() * ACID_CHARS.length)]
          }

          ctx.fillText(col.chars[j], x, charY)
        }

        col.y += col.speed * FONT_SIZE * (0.2 + col.melt)
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
      className="pointer-events-none fixed inset-0 z-[0] will-change-transform opacity-20"
      style={{ filter: 'blur(0.5px) contrast(1.2)' }}
    />
  )
}
