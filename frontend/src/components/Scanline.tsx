

export function Scanline() {
  return (
    <div className="pointer-events-none fixed inset-0 z-50 opacity-[0.03]">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,118,0.06))] bg-[length:100%_4px,3px_100%]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle,rgba(0,255,255,0.05)_1px,transparent_1px)] bg-[length:40px_40px]" />
    </div>
  )
}
