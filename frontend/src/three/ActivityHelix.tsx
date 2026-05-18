/**
 * ActivityHelix.tsx — Premium Activity Feed
 *
 * Architecture:
 *  - Background: minimal Three.js canvas for the subtle cyan particle field
 *  - Foreground: DOM card list (full text clarity) with Framer Motion
 *  - Subtle CSS 3D perspective on the container (not extreme)
 *  - Scroll-driven very slight tilt (purely aesthetic, non-distracting)
 */

import { useRef, useEffect, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { motion } from 'framer-motion'
import * as THREE from 'three'
import { Activity, Shield, Upload, Download, Layers, Search } from 'lucide-react'

// ─── Types ──────────────────────────────────────────────────────
interface ActivityRecord {
  id: string
  action: string
  details: string
  created_at: string
}

// ─── Per-Action Config ───────────────────────────────────────────
const getActionCfg = (action = '', details = '') => {
  const a = action.toLowerCase()
  const d = details.toLowerCase()
  const detected = a.includes('scan') && d.includes('detected')

  if (detected)              return { color: '#f87171', bg: 'rgba(239,68,68,0.10)', border: 'rgba(239,68,68,0.28)', icon: Shield,   tag: 'THREAT DETECTED', pulse: true  }
  if (a.includes('scan'))    return { color: '#22d3ee', bg: 'rgba(34,211,238,0.08)', border: 'rgba(34,211,238,0.22)', icon: Search,   tag: 'SCAN',            pulse: false }
  if (a.includes('embed'))   return { color: '#a78bfa', bg: 'rgba(167,139,250,0.08)', border: 'rgba(167,139,250,0.22)', icon: Upload,   tag: 'EMBED',           pulse: false }
  if (a.includes('extract')) return { color: '#fb923c', bg: 'rgba(251,146,60,0.08)', border: 'rgba(251,146,60,0.22)', icon: Download, tag: 'EXTRACT',         pulse: false }
  if (a.includes('batch'))   return { color: '#34d399', bg: 'rgba(52,211,153,0.08)', border: 'rgba(52,211,153,0.22)', icon: Layers,   tag: 'BATCH',           pulse: false }
  return                            { color: '#22d3ee', bg: 'rgba(34,211,238,0.06)', border: 'rgba(34,211,238,0.16)', icon: Activity, tag: action.toUpperCase() || 'EVENT', pulse: false }
}

// ─── Minimal Particle Background ────────────────────────────────
const Particles = () => {
  const ref = useRef<THREE.Points>(null!)
  const count = 500

  const positions = useMemo(() => {
    const p = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      p[i * 3]     = (Math.random() - 0.5) * 28
      p[i * 3 + 1] = (Math.random() - 0.5) * 18
      p[i * 3 + 2] = (Math.random() - 0.5) * 10
    }
    return p
  }, [])

  useFrame((_, dt) => {
    if (!ref.current) return
    const p = ref.current.geometry.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      p[i * 3 + 1] -= dt * (0.25 + (i % 6) * 0.04)
      if (p[i * 3 + 1] < -9) p[i * 3 + 1] = 9
    }
    ref.current.geometry.attributes.position.needsUpdate = true
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.045} color="#00d4e8" transparent opacity={0.35} sizeAttenuation depthWrite={false} />
    </points>
  )
}

// ─── Single Activity Card ────────────────────────────────────────
const ActivityCard = ({
  record, index, isLight
}: { record: ActivityRecord, index: number, isLight: boolean }) => {
  const cfg = getActionCfg(record.action, record.details)
  const Icon = cfg.icon
  // Newer items (lower index) are more prominent
  const opacity = Math.max(0.55, 1 - index * 0.08)
  const scale   = Math.max(0.96, 1 - index * 0.008)

  const timestamp = record.created_at
    ? new Date(record.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '—'
  const uuid = record.id?.substring(0, 8) ?? '--------'

  return (
    <motion.div
      initial={{ opacity: 0, y: 18, rotateX: -8 }}
      whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
      viewport={{ once: false, amount: 0.35 }}
      transition={{ duration: 0.5, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
      style={{ opacity, scale, transformOrigin: 'top center' }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          padding: '16px 20px',
          borderRadius: '18px',
          background: isLight
            ? `linear-gradient(135deg, #f0f7ff, #e8f4fc)`
            : `var(--bg-card)`,
          border: `1px solid ${isLight ? 'rgba(0,150,190,0.18)' : cfg.border}`,
          boxShadow: isLight
            ? '0 2px 12px rgba(0,100,160,0.08), 0 1px 3px rgba(0,0,0,0.05)'
            : `0 4px 24px rgba(0,0,0,0.3), 0 0 0 0.5px rgba(255,255,255,0.04)`,
          backdropFilter: 'blur(12px)',
          position: 'relative',
          overflow: 'hidden',
          cursor: 'default',
        }}
      >
        {/* Left edge accent line */}
        <div style={{
          position: 'absolute', left: 0, top: '16%', bottom: '16%', width: '3px',
          borderRadius: '2px',
          background: cfg.color,
          opacity: isLight ? 0.55 : 0.65,
          boxShadow: `0 0 8px ${cfg.color}60`,
        }} />

        {/* Icon */}
        <div style={{
          width: '42px', height: '42px', borderRadius: '13px', flexShrink: 0, marginLeft: '4px',
          background: isLight
            ? `rgba(0,130,180,0.08)`
            : cfg.bg,
          border: `1px solid ${isLight ? 'rgba(0,150,200,0.2)' : cfg.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={18} color={cfg.color} strokeWidth={2.2} style={{ opacity: isLight ? 0.8 : 1 }} />
        </div>

        {/* Text */}
        <div style={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{
              fontSize: '12px', fontWeight: 800, fontStyle: 'italic', letterSpacing: '0.08em',
              textTransform: 'uppercase', fontFamily: 'monospace',
              color: isLight ? (cfg.color === '#f87171' ? '#dc2626' : '#0e7490') : cfg.color,
              flexShrink: 0,
            }}>
              {cfg.tag}
            </span>
            {index === 0 && (
              <span style={{
                fontSize: '8px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase',
                padding: '2px 7px', borderRadius: '10px',
                background: isLight ? 'rgba(0,150,190,0.12)' : 'rgba(0,212,232,0.12)',
                color: isLight ? '#0891b2' : '#22d3ee',
                border: `1px solid ${isLight ? 'rgba(0,150,190,0.25)' : 'rgba(0,212,232,0.2)'}`,
                flexShrink: 0,
              }}>
                LATEST
              </span>
            )}
          </div>
          <p style={{
            margin: 0, fontSize: '11px', fontWeight: 500,
            color: isLight ? '#334155' : 'rgba(200,230,255,0.75)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {record.details || '—'}
          </p>
          <p style={{
            margin: '5px 0 0', fontSize: '9px', fontWeight: 600,
            fontFamily: 'monospace', letterSpacing: '0.08em', textTransform: 'uppercase',
            color: isLight ? 'rgba(30,60,100,0.38)' : 'rgba(0,212,232,0.28)',
          }}>
            {uuid}  ·  {timestamp}
          </p>
        </div>

        {/* Pulse dot for threats */}
        {cfg.pulse && (
          <div style={{ flexShrink: 0, position: 'relative', width: '10px', height: '10px' }}>
            <span style={{
              display: 'block', width: '10px', height: '10px', borderRadius: '50%',
              background: '#f87171',
              boxShadow: '0 0 8px rgba(248,113,113,0.8)',
              animation: 'pulse-dot 1.8s ease-in-out infinite',
            }} />
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ─── Public Component ────────────────────────────────────────────
export const ActivityHelix = ({
  activities,
  isLight,
}: {
  activities: ActivityRecord[]
  isLight: boolean
}) => {


  // Add pulse keyframe once
  useEffect(() => {
    const id = 'activity-helix-pulse-style'
    if (!document.getElementById(id)) {
      const s = document.createElement('style')
      s.id = id
      s.textContent = `@keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.7)} }`
      document.head.appendChild(s)
    }
  }, [])

  if (!activities || activities.length === 0) return null

  return (
    <div
      style={{
        width: '100%',
        borderRadius: '24px',
        overflow: 'hidden',
        position: 'relative',
        background: isLight
          ? 'linear-gradient(170deg, #eaf6fd 0%, #ddf0fa 100%)'
          : 'linear-gradient(170deg, #0a0a0c 0%, #111114 60%, #08080a 100%)',
        border: isLight ? '1px solid rgba(0,160,200,0.18)' : '1px solid rgba(0,212,232,0.15)',
        boxShadow: isLight
          ? '0 8px 32px rgba(0,120,180,0.10)'
          : '0 8px 40px rgba(0,0,0,0.6)',
      }}
    >
      {/* Particle field background (purely decorative, 180px tall strip) */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0,
        opacity: isLight ? 0.25 : 0.6,
      }}>
        <Canvas
          camera={{ position: [0, 0, 8], fov: 55 }}
          style={{ width: '100%', height: '100%' }}
          gl={{ antialias: false, alpha: true }}
        >
          <ambientLight intensity={0.2} />
          <Particles />
        </Canvas>
      </div>

      {/* Card list — DOM rendered, full sharpness */}
      <div style={{
        position: 'relative', zIndex: 1,
        display: 'flex', flexDirection: 'column', gap: '10px',
        padding: '20px',
      }}>
        {activities.map((r, i) => (
          <ActivityCard key={r.id} record={r} index={i} isLight={isLight} />
        ))}
      </div>
    </div>
  )
}
