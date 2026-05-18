import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Points, PointMaterial, Float } from '@react-three/drei'
import * as THREE from 'three'
import { NeuralSphere } from './NeuralSphere'
import { useLocation } from 'react-router-dom'

function DataPackets({ count = 100 }) {
  const points = useMemo(() => {
    const p = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
        p[i * 3] = (Math.random() - 0.5) * 50
        p[i * 3 + 1] = (Math.random() - 0.5) * 50
        p[i * 3 + 2] = (Math.random() - 0.5) * 50
    }
    return p
  }, [count])

  const ref = useRef<THREE.Points>(null!)

  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.x += 0.0005
      ref.current.rotation.y += 0.0003
    }
  })

  return (
    <Points ref={ref} positions={points} stride={3} frustumCulled={false}>
      <PointMaterial
        transparent
        color="#00ffff"
        size={0.05}
        sizeAttenuation={true}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </Points>
  )
}

function Grid() {
    return (
        <gridHelper 
            args={[100, 50, "#111111", "#111111"]} 
            position={[0, -10, 0]} 
            rotation={[0, 0, 0]}
        />
    )
}

export function Scene() {
  const location = useLocation()
  const isHome = location.pathname === '/'

  return (
    <div className="fixed inset-0 z-[-1] pointer-events-none bg-[#020202]">
      <Canvas camera={{ position: [0, 0, 20], fov: 60 }}>
        <color attach="background" args={['#020202']} />
        <fog attach="fog" args={['#020202', 10, 50]} />
        <ambientLight intensity={0.5} />
        
        <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
            <DataPackets count={300} />
        </Float>

        {isHome && (
            <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.5}>
                <group position={[0, 2, 0]}>
                    <NeuralSphere />
                </group>
            </Float>
        )}

        <Grid />
      </Canvas>
    </div>
  )
}
