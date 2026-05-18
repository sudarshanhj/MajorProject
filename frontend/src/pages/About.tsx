import React, { useState } from 'react'
import { motion, useMotionValue, useSpring, useTransform, AnimatePresence } from 'framer-motion'
import { Shield, Globe, Zap, Target, CheckCircle2, FileText, Fingerprint, Network, ShieldCheck, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { AcidRain } from '@/components/AcidRain'
import { DecryptTitle } from '@/components/effects/DecryptTitle'
import { useStore } from '@/store/useStore'

// Team Image Imports
import varshaImg from '@/assets/team/varsha.jpeg'
import rajImg from '@/assets/team/raj.jpg'
import sudarshanImg from '@/assets/team/sudarshan.png'
import aryanImg from '@/assets/team/aryan.jpeg'
import srujanImg from '@/assets/team/srujan.jpeg'
import dhruvImg from '@/assets/team/dhruv.jpeg'

// ─── DATA ───
const TEAM = {
  leadership: [
    {
      name: 'Dr. Varsha Jadhav',
      role: 'Project Coordinator',
      image: varshaImg,
      details: {
        title: "Assistant Professor, Dept. of Information Science & Engineering",
        expertise: ["Medical Image Analysis", "Deep Learning (CNNs)", "Cybersecurity Systems", "Machine Learning"],
        bio: "Specialist in the intersection of AI and Medical Imaging. Expertise in VGG-16/EfficientNet deployment and practical, high-accuracy AI modeling. Her background in Cybersecurity and Linux systems ensures a robust architecture for our platform."
      }
    },
    {
      name: 'Dr. Rajashekarappa',
      role: 'Project Guide',
      image: rajImg,
      details: {
        title: "Professor, Dept. of Information Science & Engineering",
        expertise: ["Cryptanalysis & Security", "Image Encryption", "Network Security", "IoT Automation"],
        bio: "Core strength in Cryptography and encryption algorithm security (DES, TEA). His research in Partial Image Encryption via pixel manipulation is pivotal to our Steganalysis resistance and recovery features."
      }
    }
  ],
  engineering: [
    { name: 'Sudarshan H J', role: 'Lead Architect', image: sudarshanImg, position: 'object-top' },
    { name: 'Aryan Giri', role: 'Design Support', image: aryanImg },
    { name: 'Srujan Aravalli', role: 'Frontend Engineer', image: srujanImg },
    { name: 'Dhruvaraj R', role: 'Operations Coordinator', image: dhruvImg, position: 'object-top' }
  ]
}

const DOMAINS = [
  {
    title: "Military & Defense",
    desc: "Critical for secure field ops and sending mission-critical data through high-risk zones.",
    icon: ShieldCheck
  },
  {
    title: "Legal & Journalism",
    desc: "Protecting whistleblowers and journalists who need to share truth without being caught.",
    icon: FileText
  },
  {
    title: "Corporate Protection",
    desc: "Guarding company trade secrets and private data from industrial spies.",
    icon: Fingerprint
  },
  {
    title: "Digital Forensics",
    desc: "Finding hidden threats in digital files to catch malicious actors.",
    icon: Network
  }
]

// ─── COMPONENTS ───

function AntigravityCard({ children, isLarge = false }: { children: React.ReactNode, isLarge?: boolean }) {
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const springX = useSpring(x, { stiffness: 150, damping: 20 })
  const springY = useSpring(y, { stiffness: 150, damping: 20 })
  const rotateX = useTransform(springY, [-0.5, 0.5], [10, -10])
  const rotateY = useTransform(springX, [-0.5, 0.5], [-10, 10])
  const driftY = useTransform(springY, [-0.5, 0.5], [-15, 15])

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect()
    x.set((e.clientX - rect.left) / rect.width - 0.5)
    y.set((e.clientY - rect.top) / rect.height - 0.5)
  }

  return (
    <motion.div
      onMouseMove={handleMouseMove}
      onMouseLeave={() => { x.set(0); y.set(0) }}
      style={{ rotateX, rotateY, y: driftY, transformStyle: "preserve-3d" }}
      className={`relative group ${isLarge ? 'w-full max-w-sm' : 'w-full'}`}
    >
      <motion.div
        style={{
          background: `radial-gradient(circle at var(--x) var(--y), rgba(0,242,255,0.15) 0%, transparent 80%)`,
          // @ts-ignore
          '--x': useTransform(springX, [-0.5, 0.5], ["0%", "100%"]),
          '--y': useTransform(springY, [-0.5, 0.5], ["0%", "100%"]),
        }}
        className="absolute inset-0 z-10 pointer-events-none rounded-2xl"
      />
      {children}
    </motion.div>
  )
}

function ProfileCard({
  member,
  variant = 'dev',
  isLight = false,
  side = 'right',
  isVanish = false,
  isShifted = false,
  onHoverChange
}: {
  member: any,
  variant?: 'lead' | 'dev',
  isLight?: boolean,
  side?: 'left' | 'right',
  isVanish?: boolean,
  isShifted?: boolean,
  onHoverChange?: (hovered: boolean) => void
}) {
  // Click-based toggle is now handled directly by onHoverChange (renamed to onClick logically)

  return (
    <motion.div
      animate={{
        opacity: isVanish ? 0.1 : 1,
        scale: isVanish ? 0.95 : 1,
        x: isShifted ? (side === 'left' ? 160 : -160) : 0
      }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
      className={`relative flex items-center group cursor-pointer ${variant === 'lead' ? 'w-full max-w-sm' : 'w-full min-w-[300px]'} ${isVanish ? 'pointer-events-none opacity-10' : ''}`}
      onClick={(e) => {
        e.stopPropagation();
        onHoverChange?.(!isShifted);
      }}
    >
      <AntigravityCard isLarge={variant === 'lead'}>
        <div className={`
          relative overflow-hidden backdrop-blur-md border transition-all duration-500
          ${variant === 'lead'
            ? `aspect-[3/4] rounded-3xl border-white/10 ${isLight ? 'bg-white/70' : 'bg-black/60'}`
            : `aspect-square rounded-2xl ${isLight ? 'border-primary/10 bg-white/70 shadow-md' : 'border-white/10 bg-black/60'}`}
        `}>
          <img
            src={member.image}
            className={`absolute inset-0 w-full h-full object-cover ${member.position || 'object-top'} scale-90 grayscale opacity-40 group-hover:opacity-100 group-hover:grayscale-0 group-hover:scale-100 transition-all duration-700`}
          />
          <div className={`absolute inset-0 ${isLight ? 'bg-gradient-to-t from-white/80 via-transparent' : 'bg-gradient-to-t from-black via-black/20 to-transparent'}`} />
          <div className="absolute bottom-0 left-0 right-0 p-6 space-y-1" style={{ transform: "translateZ(40px)" }}>
            <p className="text-[10px] font-mono tracking-[0.3em] text-primary uppercase">{member.role}</p>
            <h3 className={`text-xl font-bold tracking-tight ${isLight ? 'text-slate-900' : 'text-white'}`}>{member.name}</h3>
          </div>
        </div>
      </AntigravityCard>

      {/* Side Detail Card for Leadership */}
      {variant === 'lead' && member.details && (
        <AnimatePresence mode="wait">
          {isShifted && (
            <motion.div
              initial={{ opacity: 0, x: side === 'right' ? 30 : -30, scale: 0.95 }}
              animate={{ opacity: 1, x: side === 'right' ? 20 : -20, scale: 1 }}
              transition={{ duration: 0.8, ease: "circOut" }}
              exit={{ opacity: 0, x: side === 'right' ? 15 : -15, scale: 0.95 }}
              className={`
                 absolute ${side === 'right' ? 'left-full ml-12' : 'right-full mr-12'} w-[360px] p-8 rounded-3xl border backdrop-blur-3xl z-[50] shadow-2xl
                 ${isLight ? 'bg-white/95 border-slate-200' : 'bg-[#0a0f14]/95 border-white/10'}
               `}
              style={{ transformStyle: 'preserve-3d' }}
            >
              <div className="space-y-6">
                <div className="pb-4 border-b border-white/5">
                  <h4 className={`text-[11px] font-mono uppercase tracking-[0.2em] mb-2 ${isLight ? 'text-slate-500' : 'text-white/40'}`}>{member.details.title}</h4>
                  <div className="flex flex-wrap gap-2.5 mt-3">
                    {member.details.expertise.map((exp: string, i: number) => (
                      <span key={i} className={`px-3 py-1.5 rounded-xl border text-[10px] font-bold uppercase tracking-wider ${isLight ? 'bg-slate-100 border-slate-200 text-slate-600' : 'bg-white/5 border-white/10 text-white/70'}`}>
                        {exp}
                      </span>
                    ))}
                  </div>
                </div>
                <p className={`text-sm leading-relaxed font-medium ${isLight ? 'text-slate-600' : 'text-white/70'}`}>
                  {member.details.bio}
                </p>
                <div className={`pt-2 flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.2em] ${isLight ? 'text-slate-300' : 'text-white/20'}`}>
                  <div className={`w-2 h-2 rounded-full ${isLight ? 'bg-slate-200' : 'bg-white/10'} animate-pulse`} />
                  Tactical Advisor Core _ Encrypted
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      )}
    </motion.div>
  )
}

export function About() {
  const theme = useStore(s => s.theme)
  const isLight = theme === 'light'
  const [selectedLeader, setSelectedLeader] = useState<number | null>(null)

  const handleLeaderClick = (index: number | null) => {
    setSelectedLeader(prev => prev === index ? null : index)
  }

  return (
    <div className={`min-h-screen bg-transparent ${isLight ? 'text-slate-900' : 'text-white'} selection:bg-primary/30 transition-colors duration-500`}>
      {/* Background Effects */}
      {!isLight && <AcidRain />}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className={`absolute top-0 right-0 w-[500px] h-[500px] ${isLight ? 'hidden' : 'bg-primary/10'} blur-[150px] rounded-full`} />
        <div className={`absolute bottom-0 left-0 w-[400px] h-[400px] ${isLight ? 'hidden' : 'bg-blue-500/5'} blur-[120px] rounded-full`} />
      </div>

      {/* Navigation Portal */}
      <nav className="fixed top-8 left-8 z-[100]">
        {/* Removed Terminal_Return as per user request */}
      </nav>

      <main className={`max-w-7xl mx-auto px-6 ${useStore.getState().isAuthenticated ? 'pt-24' : 'pt-40'} pb-32 relative z-10`}>

        {/* Hero: Floating Titles with STEG highlight */}
        <section className="text-center space-y-6 mb-40">
          <DecryptTitle
            text="DEEPSTEGAI"
            highlightStart={4}
            highlightEnd={8}
            className={`text-6xl md:text-8xl font-black italic ${isLight ? 'text-slate-900' : 'text-white'}`}
          />
          <p className="text-primary/60 font-mono tracking-[0.5em] uppercase text-sm">Aero-Tactical Intelligence Platform</p>
        </section>

        {/* Section: Project Manifest (Implementation & Use Cases) */}
        <section className="mb-40 space-y-24">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <h2 className="text-4xl font-black tracking-tight uppercase">Our <span className="text-primary">Mission</span></h2>
                <p className={`text-lg leading-relaxed italic ${isLight ? 'text-slate-600' : 'text-white/70'}`}>
                  DeepStegAI builds tools for secure and private information sharing.
                  We help people hide data inside images so it can be moved safely across any network, while our AI tools help find hidden threats before they cause harm.
                </p>
              </div>

              <div className="space-y-6">
                <div className="flex gap-6 items-start">
                  <div className="mt-1 w-12 h-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h4 className="text-lg font-bold uppercase tracking-tight mb-1">Stealth Data Hiding</h4>
                    <p className={`text-sm leading-relaxed ${isLight ? 'text-slate-500' : 'text-white/50'}`}>Hide secret messages inside any image. Our tool cleans up digital signatures so scanners can't find them.</p>
                  </div>
                </div>
                <div className="flex gap-6 items-start">
                  <div className="mt-1 w-12 h-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h4 className="text-lg font-bold uppercase tracking-tight mb-1">AI Truth Scanner</h4>
                    <p className={`text-sm leading-relaxed ${isLight ? 'text-slate-500' : 'text-white/50'}`}>Use smart AI to find microscopic changes in files that show someone is hiding data.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {DOMAINS.map((domain, i) => (
                <motion.div
                  key={i}
                  whileHover={{ scale: 1.02, y: -5 }}
                  className={`p-8 rounded-[2rem] border transition-all group backdrop-blur-xl ${isLight ? 'bg-white/70 border-primary/10 hover:border-primary/40 shadow-sm' : 'bg-black/60 border-white/10 hover:border-white/20'}`}
                >
                  <domain.icon className="w-8 h-8 text-primary mb-6 group-hover:scale-110 transition-transform" />
                  <h4 className={`text-sm font-black uppercase tracking-widest mb-3 ${isLight ? 'text-slate-800' : 'text-white'}`}>{domain.title}</h4>
                  <p className={`text-[11px] leading-relaxed font-semibold uppercase tracking-wider ${isLight ? 'text-slate-400' : 'text-white/40'}`}>{domain.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Section: Leadership (The "Command Deck") */}
        <section className="space-y-12 mb-40">
          <div className="flex items-center gap-4">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-primary/20" />
            <h2 className={`text-2xl font-bold tracking-widest uppercase flex items-center gap-3 ${isLight ? 'text-slate-800' : 'text-white'}`}>
              <Shield className="text-primary w-6 h-6" /> Project Leadership
            </h2>
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-primary/20" />
          </div>

          <div className="flex justify-center items-center h-[500px] gap-8" onMouseLeave={() => setSelectedLeader(null)}>
            {TEAM.leadership.map((lead, i) => (
              <ProfileCard
                key={i}
                member={lead}
                variant="lead"
                isLight={isLight}
                side={i === 0 ? 'right' : 'left'} // Make them open towards center
                isVanish={selectedLeader !== null && selectedLeader !== i}
                isShifted={selectedLeader === i}
                onHoverChange={() => handleLeaderClick(i)}
              />
            ))}
          </div>
        </section>

        {/* Section: Core Engineers */}
        <section className="space-y-12 mb-20">
          <div className="text-center">
            <h2 className={`text-3xl font-black tracking-tighter uppercase mb-2 ${isLight ? 'text-slate-900' : 'text-white'}`}>The Core Team</h2>
            <div className="w-24 h-1 bg-primary mx-auto rounded-full" />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 px-4">
            {TEAM.engineering.map((dev, i) => (
              <ProfileCard key={i} member={dev} isLight={isLight} />
            ))}
          </div>
        </section>

        {/* Section: Applications (Tactical Marquee) */}
        <section className="space-y-12 pb-10 overflow-hidden">
          <div className="flex flex-col items-center gap-4">
            <h3 className={`text-sm font-black uppercase tracking-[0.4em] ${isLight ? 'text-slate-800' : 'text-white/60'}`}>Mission Parameters</h3>
            <div className="h-px w-24 bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
          </div>

          <style>{`
              @keyframes about-marquee {
                0% { transform: translateX(0); }
                100% { transform: translateX(-50%); }
              }
              .animate-about-marquee {
                animation: about-marquee 40s linear infinite;
              }
              .about-marquee-mask {
                mask-image: linear-gradient(to right, transparent, black 15%, black 85%, transparent);
                -webkit-mask-image: linear-gradient(to right, transparent, black 15%, black 85%, transparent);
              }
           `}</style>

          <div className="relative about-marquee-mask">
            <div className="flex gap-8 w-max animate-about-marquee py-4">
              {[...Array(3)].map((_, groupIdx) => (
                <React.Fragment key={groupIdx}>
                  {[
                    { title: "Zero-Trace Hiding", desc: "Hide info inside photos without leaving any digital tracks.", icon: Zap },
                    { title: "Smart AI Scanner", desc: "Scan files with deep learning to find hidden messages instantly.", icon: Target },
                    { title: "Field Operations", desc: "Secure ways to send info from high-risk or monitored locations.", icon: Globe }
                  ].map((app, i) => (
                    <div
                      key={`${groupIdx}-${i}`}
                      className={`w-[350px] p-8 rounded-[2rem] border transition-all duration-500 backdrop-blur-xl ${isLight ? 'bg-white/70 border-primary/10 shadow-sm' : 'bg-black/60 border-white/10'}`}
                    >
                      <app.icon className="w-10 h-10 text-primary mb-6" />
                      <h4 className={`text-lg font-bold mb-3 uppercase tracking-tight ${isLight ? 'text-slate-800' : 'text-white'}`}>{app.title}</h4>
                      <p className={`text-sm leading-relaxed font-medium ${isLight ? 'text-slate-500' : 'text-white/50'}`}>{app.desc}</p>
                    </div>
                  ))}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Core Navigation Bridge (Integrated) */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            className="text-center pt-10"
          >
            <Link
              to="/"
              className={`
                  inline-flex items-center gap-4 px-12 py-5 rounded-2xl border font-black uppercase tracking-[0.3em] text-sm
                  transition-all duration-300 transform hover:scale-105 active:scale-95
                  ${isLight ? 'bg-white border-slate-200 text-slate-900 shadow-xl shadow-black/5 hover:bg-slate-50' : 'bg-primary/10 border-primary/30 text-primary hover:bg-primary/20'}
                `}
            >
              <ArrowRight className="w-5 h-5 rotate-180" />
              Return to Core
            </Link>
          </motion.div>
        </section>

      </main>

    </div>
  )
}
