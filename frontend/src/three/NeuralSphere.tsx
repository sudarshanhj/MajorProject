import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useStore } from '@/store/useStore'

export function NeuralSphere() {
  const theme = useStore(s => s.theme)
  const isLight = theme === 'light'
  
  const pointsRef = useRef<THREE.Points>(null!)
  const ring1Ref = useRef<THREE.Mesh>(null!)
  const ring2Ref = useRef<THREE.Mesh>(null!)
  const wireframeRef = useRef<THREE.Mesh>(null!)
  const groupRef = useRef<THREE.Group>(null!)
  
  // Track continuous global mouse coordinates
  const mouse = useRef(new THREE.Vector2(0, 0))
  // Velocity vector for stretch
  const velocity = useRef(new THREE.Vector2(0, 0))
  const targetVelocity = useRef(new THREE.Vector2(0, 0))

  // Track scroll position to disable interaction when scrolling away from the top hero section
  const scrollY = useRef(0)
  
  useEffect(() => {
    const handleMouse = (e: MouseEvent) => {
      // Get real-time offset from CSS variable
      const sidebarW = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--sidebar-offset')) || 0
      const contentW = window.innerWidth - sidebarW
      const centerX = sidebarW + (contentW / 2)
      
      mouse.current.x = (e.clientX - centerX) / (contentW / 2)
      mouse.current.y = -(e.clientY / window.innerHeight) * 2 + 1
      
      targetVelocity.current.x = e.movementX * 0.05
      targetVelocity.current.y = -e.movementY * 0.05
    }
    
    const handleScroll = () => {
        scrollY.current = window.scrollY
    }

    // Capture global interactions
    window.addEventListener('mousemove', handleMouse, { passive: true })
    window.addEventListener('scroll', handleScroll, { passive: true })
    window.addEventListener('resize', () => {
        // Trigger a re-render or internal check if needed, 
        // though useFrame handles most cases, an explicit resize listener 
        // helps ensure viewport measurements are fresh.
    }, { passive: true })
    
    return () => {
        window.removeEventListener('mousemove', handleMouse)
        window.removeEventListener('scroll', handleScroll)
        window.removeEventListener('resize', () => {})
    }
  }, [])

  const count = 4000
  
  const [positions, colors] = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const color = new THREE.Color(isLight ? '#0096a3' : '#00f2ff')
    
    for (let i = 0; i < count; i++) {
        const theta = 2 * Math.PI * Math.random()
        const phi = Math.acos(2 * Math.random() - 1)
        const layer = Math.random() > 0.5 ? 4 : 4.5
        const r = layer + (Math.random() - 0.5) * 0.2
        
        pos[i * 3] = r * Math.sin(phi) * Math.cos(theta)
        pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
        pos[i * 3 + 2] = r * Math.cos(phi)
        
        col[i * 3] = color.r
        col[i * 3 + 1] = color.g
        col[i * 3 + 2] = color.b
    }
    return [pos, col]
  }, [isLight])

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    
    // Smooth down native movement speed
    targetVelocity.current.lerp(new THREE.Vector2(0, 0), 0.1)

    const sidebarStr = getComputedStyle(document.documentElement).getPropertyValue('--sidebar-offset') || '0'
    const sidebarPx = parseFloat(sidebarStr) || 0
    
    // The content area's center relative to window center is (sidebarPx / 2).
    // In Three.js world units, this shift is:
    const targetBaseX = (sidebarPx / (window.innerWidth || 1)) * (state.viewport.width / 2)

    // Bounds checking
    const distFromCenter = Math.sqrt(mouse.current.x ** 2 + mouse.current.y ** 2)
    const isHovered = distFromCenter < 0.65 && scrollY.current < 150
    
    if (isHovered) {
        velocity.current.x = THREE.MathUtils.lerp(velocity.current.x, targetVelocity.current.x, 0.08)
        velocity.current.y = THREE.MathUtils.lerp(velocity.current.y, targetVelocity.current.y, 0.08)
    } else {
        velocity.current.x = THREE.MathUtils.lerp(velocity.current.x, 0, 0.05)
        velocity.current.y = THREE.MathUtils.lerp(velocity.current.y, 0, 0.05)
    }

    if (groupRef.current) {
        const stretchX = 1 + Math.min(Math.abs(velocity.current.x) * 0.2, 0.3)
        const stretchY = 1 + Math.min(Math.abs(velocity.current.y) * 0.2, 0.3)
        const targetScaleX = stretchX * (1 - Math.min(Math.abs(velocity.current.y) * 0.1, 0.15))
        const targetScaleY = stretchY * (1 - Math.min(Math.abs(velocity.current.x) * 0.1, 0.15))

        groupRef.current.scale.x = THREE.MathUtils.lerp(groupRef.current.scale.x, targetScaleX, 0.08)
        groupRef.current.scale.y = THREE.MathUtils.lerp(groupRef.current.scale.y, targetScaleY, 0.08)

        // Combine base centering offset with interaction velocity
        const interactionPosX = velocity.current.x * 0.5
        const targetPosX = targetBaseX + interactionPosX
        const targetPosY = velocity.current.y * 0.5

        groupRef.current.position.x = THREE.MathUtils.lerp(groupRef.current.position.x, targetPosX, 0.1)
        groupRef.current.position.y = THREE.MathUtils.lerp(groupRef.current.position.y, targetPosY, 0.1)
        
        const targetRotZ = -velocity.current.x * 0.15
        groupRef.current.rotation.z = THREE.MathUtils.lerp(groupRef.current.rotation.z, targetRotZ, 0.08)
    }

    // Standard autonomous rotations
    if (pointsRef.current) {
      pointsRef.current.rotation.y = t * 0.08
      pointsRef.current.rotation.x = t * 0.04
    }

    if (ring1Ref.current) {
        ring1Ref.current.rotation.z = t * 0.2
        ring1Ref.current.rotation.x = t * 0.1
    }
    if (ring2Ref.current) {
        ring2Ref.current.rotation.z = -t * 0.15
        ring2Ref.current.rotation.y = t * 0.25
    }
    if (wireframeRef.current) {
        wireframeRef.current.rotation.x = -t * 0.1
        wireframeRef.current.rotation.y = -t * 0.2
    }
  })

  // Colors and Opacities tuned strictly for distinct visibility in both themes
  const baseColor = isLight ? "#0096a3" : "#00f2ff"
  
  return (
    <group ref={groupRef}>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
          <bufferAttribute attach="attributes-color" count={count} array={colors} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial 
          size={isLight ? 0.04 : 0.035} 
          color={isLight ? "#0096a3" : "#ffffff"} 
          vertexColors={!isLight} 
          transparent 
          opacity={isLight ? 1.0 : 0.85} 
          blending={isLight ? THREE.NormalBlending : THREE.AdditiveBlending} 
          depthWrite={false} 
          sizeAttenuation={true} 
        />
      </points>
      
      <mesh ref={ring1Ref}>
        <torusGeometry args={[5.2, 0.010, 6, 80]} />
        <meshBasicMaterial color={baseColor} transparent opacity={isLight ? 0.6 : 0.4} />
      </mesh>
      
      <mesh ref={ring2Ref} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[5.5, 0.007, 6, 80]} />
        <meshBasicMaterial color={baseColor} transparent opacity={isLight ? 0.5 : 0.3} />
      </mesh>
      
      <mesh ref={wireframeRef} rotation={[0, Math.PI / 4, 0]}>
        <sphereGeometry args={[4.8, 12, 12]} />
        <meshBasicMaterial color={baseColor} wireframe transparent opacity={isLight ? 0.35 : 0.15} />
      </mesh>
      
      <mesh>
        <sphereGeometry args={[3.2, 32, 32]} />
        <meshBasicMaterial color={baseColor} transparent opacity={isLight ? 0.12 : 0.02} />
      </mesh>
    </group>
  )
}
