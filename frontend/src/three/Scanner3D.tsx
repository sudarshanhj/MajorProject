import { useRef, Suspense, memo } from 'react'
import { useFrame, useLoader } from '@react-three/fiber'
import { Plane } from '@react-three/drei'
import * as THREE from 'three'
import { useStore } from '@/store/useStore'

interface Scanner3DProps {
  image?: string
  scanning: boolean
}

function ImagePlane({ url }: { url: string }) {
  const texture = useLoader(THREE.TextureLoader, url)
  return (
    <Plane args={[10, 10]} position={[0, 0, 0]}>
        <meshBasicMaterial map={texture} transparent opacity={0.9} />
    </Plane>
  )
}

export const Scanner3D = memo(function Scanner3D({ image, scanning }: Scanner3DProps) {
  const theme = useStore(s => s.theme)
  const isLight = theme === 'light'
  
  const scanLineRef  = useRef<THREE.Mesh>(null!)
  const glowLineRef  = useRef<THREE.Mesh>(null!)
  const cornerTLRef  = useRef<THREE.Mesh>(null!)
  const cornerBRRef  = useRef<THREE.Mesh>(null!)

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (scanning) {
      // Sweeping scan line
      if (scanLineRef.current)  scanLineRef.current.position.y  = Math.sin(t * 2.5) * 5.2
      if (glowLineRef.current)  glowLineRef.current.position.y  = Math.sin(t * 2.5) * 5.2
      // Pulsing corners
      if (cornerTLRef.current)  (cornerTLRef.current.material as THREE.MeshBasicMaterial).opacity = 0.4 + Math.sin(t * 6) * 0.3
      if (cornerBRRef.current)  (cornerBRRef.current.material as THREE.MeshBasicMaterial).opacity = 0.4 + Math.sin(t * 6 + Math.PI) * 0.3
    }
  })

  return (
    <group>
      {/* Image Plane */}
      <Suspense fallback={
        <Plane args={[10, 10]}>
          <meshBasicMaterial color="#050505" transparent opacity={0.8} />
        </Plane>
      }>
        {image ? (
          <ImagePlane url={image} />
        ) : (
          <Plane args={[10, 10]} position={[0, 0, 0]}>
            <meshBasicMaterial color="#050505" transparent opacity={0.6} />
          </Plane>
        )}
      </Suspense>

      {/* Cyber grid overlay — always visible */}
      <Plane args={[11, 11]} position={[0, 0, 0.02]}>
        <meshBasicMaterial color={isLight ? "#0096a3" : "#00f2ff"} wireframe transparent opacity={scanning ? (isLight ? 0.25 : 0.12) : (isLight ? 0.1 : 0.04)} />
      </Plane>

      {/* Corner bracket TL */}
      <mesh ref={cornerTLRef} position={[-4.8, 4.8, 0.1]}>
        <planeGeometry args={[1, 0.05]} />
        <meshBasicMaterial color={isLight ? "#0096a3" : "#00f2ff"} transparent opacity={isLight ? 0.9 : 0.6} />
      </mesh>
      <mesh position={[-4.8, 4.8, 0.1]} rotation={[0, 0, Math.PI / 2]}>
        <planeGeometry args={[1, 0.05]} />
        <meshBasicMaterial color={isLight ? "#0096a3" : "#00f2ff"} transparent opacity={isLight ? 0.9 : 0.6} />
      </mesh>

      {/* Corner bracket BR */}
      <mesh ref={cornerBRRef} position={[4.8, -4.8, 0.1]}>
        <planeGeometry args={[1, 0.05]} />
        <meshBasicMaterial color={isLight ? "#0096a3" : "#00f2ff"} transparent opacity={isLight ? 0.9 : 0.6} />
      </mesh>
      <mesh position={[4.8, -4.8, 0.1]} rotation={[0, 0, Math.PI / 2]}>
        <planeGeometry args={[1, 0.05]} />
        <meshBasicMaterial color={isLight ? "#0096a3" : "#00f2ff"} transparent opacity={isLight ? 0.9 : 0.6} />
      </mesh>

      {/* Scan sweeper — only while scanning */}
      {scanning && (
        <>
          {/* Main line */}
          <mesh ref={scanLineRef} position={[0, 0, 0.15]}>
            <planeGeometry args={[10.5, 0.04]} />
            <meshBasicMaterial color={isLight ? "#0096a3" : "#00f2ff"} transparent opacity={isLight ? 1 : 0.9} blending={isLight ? THREE.NormalBlending : THREE.AdditiveBlending} />
          </mesh>
          {/* Diffuse glow below line */}
          <mesh ref={glowLineRef} position={[0, -0.3, 0.12]}>
            <planeGeometry args={[10.5, 0.6]} />
            <meshBasicMaterial color={isLight ? "#0096a3" : "#00f2ff"} transparent opacity={isLight ? 0.2 : 0.08} blending={isLight ? THREE.NormalBlending : THREE.AdditiveBlending} />
          </mesh>
          {/* Wireframe bounding box */}
          <mesh position={[0, 0, 0.5]}>
            <boxGeometry args={[10.5, 10.5, 1]} />
            <meshBasicMaterial color={isLight ? "#0096a3" : "#00f2ff"} wireframe transparent opacity={isLight ? 0.3 : 0.15} />
          </mesh>
        </>
      )}
    </group>
  )
})
