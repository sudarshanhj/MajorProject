import { useState, memo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Mail, User, MessageSquare, ShieldCheck, CheckCircle2 } from 'lucide-react'
import { stegoApi } from '@/services/api'

const TRANSITION = { duration: 0.6, ease: [0.22, 1, 0.36, 1] }

export const Support = memo(function Support() {
    const [formData, setFormData] = useState({ name: '', email: '', message: '' })
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [submitted, setSubmitted] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!formData.name || !formData.email || !formData.message) return
        
        setIsSubmitting(true)
        setError(null)
        
        try {
            await stegoApi.contact(formData)
            setSubmitted(true)
            setFormData({ name: '', email: '', message: '' })
            setTimeout(() => setSubmitted(false), 5000)
        } catch (err: any) {
            setError(err.response?.data?.error || 'Failed to transmit signal to HQ.')
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className="h-full flex flex-col gap-4 max-w-4xl mx-auto overflow-y-auto pb-4">
            <div className="space-y-2">
                <h2 className="text-xl font-bold tracking-tight text-[var(--fg)] leading-none">Support</h2>
                <p className="text-xs font-medium text-[var(--fg-dim)] mt-1">Send us a message and we'll get back to you within 24 hours</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Left Side: Info */}
                <div className="space-y-4">
                    <div className="bg-[var(--bg-card)] p-5 rounded-[2rem] border border-[var(--border)] space-y-4 shadow-xl">
                        <div className="p-4 bg-primary/10 rounded-2xl border border-primary/20 w-fit">
                            <ShieldCheck className="h-8 w-8 text-primary" />
                        </div>
                        <div className="space-y-2">
                            <h3 className="text-xl font-black italic tracking-tight text-[var(--fg)] uppercase tracking-wider">Direct Operator Link</h3>
                            <p className="text-[var(--fg-dim)]/40 text-[10px] font-bold tracking-widest leading-relaxed uppercase">
                                Your message will be routed through our secure proxy network. 
                                Standard encryption protocols are active for all outgoing signals.
                            </p>
                        </div>
                        
                        <div className="h-px bg-[var(--border)]" />
                        
                        <div className="space-y-4">
                            {[
                                { label: 'Response Time', val: '< 24H', icon: Send },
                                { label: 'Priority Level', val: 'ALPHA-9', icon: ShieldCheck },
                            ].map((item, i) => (
                                <div key={i} className="flex items-center gap-4">
                                    <div className="p-2 bg-[var(--bg)] rounded-lg border border-[var(--border)]">
                                        <item.icon className="h-4 w-4 text-[var(--fg-dim)]/40" />
                                    </div>
                                    <div>
                                        <p className="text-[8px] font-black text-[var(--fg-dim)]/20 uppercase tracking-widest leading-none mb-1">{item.label}</p>
                                        <p className="text-xs font-mono font-black text-[var(--fg)]/80 tracking-tighter">{item.val}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-[var(--bg-card)] p-4 rounded-3xl border border-[var(--border)] text-center shadow-lg">
                        <p className="text-[10px] text-[var(--fg-dim)]/20 font-bold italic uppercase tracking-widest">
                            Authorized personnel only. Logs are maintained for audit trails.
                        </p>
                    </div>
                </div>

                {/* Right Side: Form */}
                <div className="relative">
                    <AnimatePresence mode="wait">
                        {submitted ? (
                            <motion.div
                                key="success"
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                className="bg-[var(--bg-card)] h-full flex flex-col items-center justify-center p-8 rounded-[2rem] border border-primary/20 text-center space-y-4 shadow-2xl"
                            >
                                <div className="h-20 w-20 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center">
                                    <CheckCircle2 className="h-10 w-10 text-primary" />
                                </div>
                                <div className="space-y-2">
                                    <h3 className="text-2xl font-black italic text-primary uppercase tracking-tighter">Signal Received</h3>
                                    <p className="text-[var(--fg-dim)]/50 text-xs font-bold tracking-wide leading-relaxed">
                                        Transmission successful. Our operators will decode and review your query shortly.
                                    </p>
                                </div>
                                <button 
                                    onClick={() => setSubmitted(false)}
                                    className="px-8 py-3 rounded-xl border border-primary/20 bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest hover:bg-primary/20 transition-all"
                                >
                                    Send Another Signal
                                </button>
                            </motion.div>
                        ) : (
                            <motion.form
                                key="form"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                transition={TRANSITION}
                                onSubmit={handleSubmit}
                                className="bg-[var(--bg-card)] p-5 rounded-[2rem] border border-[var(--border)] space-y-4 shadow-2xl"
                            >
                                <div className="space-y-3">
                                    <div className="space-y-2">
                                        <label className="text-[9px] font-semibold text-primary uppercase tracking-wide ml-2">Name</label>
                                        <div className="relative group">
                                            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--fg-dim)]/30 group-focus-within:text-primary transition-colors">
                                                <User className="h-4 w-4" />
                                            </div>
                                            <input 
                                                required
                                                type="text" 
                                                placeholder="Your name"
                                                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl py-3 pl-12 pr-6 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all text-[var(--fg)] placeholder:text-[var(--fg-dim)]/50"
                                                value={formData.name}
                                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-[9px] font-semibold text-primary uppercase tracking-wide ml-2">Email</label>
                                        <div className="relative group">
                                            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--fg-dim)]/30 group-focus-within:text-primary transition-colors">
                                                <Mail className="h-4 w-4" />
                                            </div>
                                            <input 
                                                required
                                                type="email" 
                                                placeholder="Email address"
                                                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl py-3 pl-12 pr-6 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all text-[var(--fg)] placeholder:text-[var(--fg-dim)]/50"
                                                value={formData.email}
                                                onChange={e => setFormData({ ...formData, email: e.target.value })}
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-[9px] font-semibold text-primary uppercase tracking-wide ml-2">Message</label>
                                        <div className="relative group">
                                            <div className="absolute left-4 top-5 text-[var(--fg-dim)]/30 group-focus-within:text-primary transition-colors">
                                                <MessageSquare className="h-4 w-4" />
                                            </div>
                                            <textarea 
                                                required
                                                rows={4}
                                                placeholder="Describe your issue or question"
                                                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl py-3 pl-12 pr-6 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all text-[var(--fg)] placeholder:text-[var(--fg-dim)]/50 resize-none font-sans"
                                                value={formData.message}
                                                onChange={e => setFormData({ ...formData, message: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                </div>

                                {error && (
                                    <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-[10px] font-bold text-red-400 text-center uppercase tracking-widest italic">
                                        {error}
                                    </div>
                                )}

                                <button 
                                    disabled={isSubmitting}
                                    className="w-full bg-primary hover:opacity-90 disabled:bg-primary/50 text-black py-3 rounded-2xl font-black text-xs uppercase tracking-[0.3em] shadow-[0_0_30px_var(--primary-glow)] hover:shadow-[0_0_40px_var(--primary-glow)] transition-all active:scale-95 flex items-center justify-center gap-3"
                                >
                                    {isSubmitting ? (
                                        <>
                                            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }} className="h-4 w-4 border-2 border-black border-t-transparent rounded-full" />
                                            Sending...
                                        </>
                                    ) : (
                                        <>
                                            <Send className="h-4 w-4" />
                                            Send Message
                                        </>
                                    )}
                                </button>
                            </motion.form>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    )
})
