import { useState } from 'react'
import { motion } from 'framer-motion'
import { Zap, ArrowRight, CreditCard, ShieldCheck } from 'lucide-react'
import { stegoApi } from '@/services/api'
import { useStore } from '@/store/useStore'

const TIERS = [
  { id: 99, tokens: 50, price: '₹99', name: 'OPERATOR', desc: 'Basic access for standard forensic scans.' },
  { id: 199, tokens: 120, price: '₹199', name: 'ANALYST', desc: 'Extended bandwidth for neural processing.', popular: true },
  { id: 499, tokens: 350, price: '₹499', name: 'COMMANDER', desc: 'Maximum throughput and payload embedding.' },
]

function loadScript(src: string) {
  return new Promise((resolve) => {
    const script = document.createElement('script')
    script.src = src
    script.onload = () => resolve(true)
    script.onerror = () => resolve(false)
    document.body.appendChild(script)
  })
}

export function Pricing() {
  const [loadingTier, setLoadingTier] = useState<number | null>(null)
  const addLog = useStore(s => s.addLog)
  const fetchUser = useStore(s => s.fetchUser)
  const user = useStore(s => s.user)

  const handlePayment = async (amount: number) => {
    setLoadingTier(amount)
    try {
      const resLoad = await loadScript('https://checkout.razorpay.com/v1/checkout.js')
      if (!resLoad) {
        addLog('Failed to load payment gateway.')
        return
      }

      const res = await stegoApi.createRazorpayOrder(amount)
      if (!res.data.success) throw new Error('Order creation failed')

      const order = res.data.data
      const options = {
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: 'DeepStegAI',
        description: 'Neural Credits Top-up',
        order_id: order.order_id,
        handler: async function (response: any) {
             addLog('Payment authorized. Synchronizing with neural network...')
             try {
                 const verifyRes = await stegoApi.verifyPayment({
                     razorpay_order_id: response.razorpay_order_id,
                     razorpay_payment_id: response.razorpay_payment_id,
                     razorpay_signature: response.razorpay_signature,
                     credits: TIERS.find(t => t.id === amount)?.tokens || 0
                 });
                 
                 if (verifyRes.data.success) {
                     addLog(`Successfully recharged credits balance!`)
                     fetchUser()
                 } else {
                     addLog('Payment verification failed on server.')
                 }
             } catch (err: any) {
                 addLog(`Verification error: ${err.message}`)
             }
        },
        prefill: {
          email: user?.email || '',
        },
        theme: {
          color: '#00f2ff'
        }
      }

      const paymentObject = new (window as any).Razorpay(options)
      paymentObject.open()

    } catch (err: any) {
      addLog(`Payment initialization failed: ${err.message}`)
    } finally {
      setLoadingTier(null)
    }
  }

  return (
    <div className="h-full flex flex-col items-center justify-center p-4">
      <div className="text-center mb-10 w-full max-w-4xl">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 border border-primary/20 mb-6 shadow-[0_0_30px_var(--primary-glow)]">
          <CreditCard className="h-8 w-8 text-primary" />
        </div>
        <h2 className="text-3xl sm:text-4xl font-black italic tracking-tighter uppercase text-[var(--fg)] glow-text mb-4">Network Top-Up</h2>
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-[var(--fg-dim)]/60">Acquire additional Neural Credits to bypass firewall limits.</p>
      </div>

      {((import.meta as any).env.VITE_ADMIN_EMAILS || 'aravalli813@gmail.com,hjsudarshan18@gmail.com').split(',').includes(user?.email || '') ? (
        <div className="w-full max-w-2xl bg-[var(--bg-card)] border border-primary/30 rounded-3xl p-10 text-center shadow-[0_0_40px_var(--primary-glow)]">
          <div className="mx-auto w-16 h-16 bg-primary/10 border border-primary/20 rounded-full flex items-center justify-center mb-6">
            <ShieldCheck className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-2xl font-black italic tracking-widest uppercase text-primary mb-2">Developer Clearance</h3>
          <p className="text-sm font-bold tracking-[0.2em] text-[var(--fg-dim)] uppercase leading-relaxed mb-6">
            Global network restrictions lifted. Access granted with infinite cryptographic resources.
          </p>
          <div className="inline-block px-6 py-3 bg-[var(--bg-sidebar)] border border-primary/20 rounded-xl text-primary font-mono text-xs font-black tracking-widest">
            CREDITS: ∞
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl">
        {TIERS.map(tier => (
          <motion.div
            key={tier.id}
            whileHover={{ y: -10 }}
            className={`relative rounded-3xl border p-8 backdrop-blur-sm flex flex-col transition-all duration-300 ${tier.popular ? 'bg-primary/5 border-primary shadow-[0_0_30px_var(--primary-glow)]' : 'bg-[var(--bg-card)] border-[var(--border)] shadow-xl'}`}
          >
            {tier.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-[var(--btn-text)] text-[9px] font-black uppercase tracking-widest px-4 py-1 rounded-full shadow-[0_0_15px_var(--primary-glow)]">
                Most Popular
              </div>
            )}
            <div className="flex items-center gap-3 mb-6">
              <Zap className={`h-5 w-5 ${tier.popular ? 'text-primary' : 'text-[var(--fg-dim)]'}`} />
              <h3 className="text-lg font-black italic tracking-widest uppercase text-[var(--fg)]">{tier.name}</h3>
            </div>
            
            <div className="mb-2">
              <span className="text-4xl font-black glow-text">{tier.price}</span>
            </div>
            <p className="text-xs font-bold tracking-widest uppercase text-primary mb-6"><span className="text-2xl">{tier.tokens}</span> CREDITS</p>
            
            <p className="text-[10px] font-bold tracking-[0.2em] leading-relaxed text-[var(--fg-dim)]/60 mb-8 flex-1">
              {tier.desc}
            </p>

            <button
              onClick={() => handlePayment(tier.id)}
              disabled={loadingTier === tier.id}
              className={`w-full py-4 rounded-xl flex items-center justify-center gap-2 text-sm font-bold tracking-wide transition-all group ${tier.popular ? 'bg-primary text-[var(--btn-text)] hover:shadow-[0_0_20px_var(--primary-glow)] hover:opacity-90' : 'bg-[var(--bg-sidebar)] border border-[var(--border)] text-[var(--fg)] hover:border-primary/50'}`}
            >
              {loadingTier === tier.id ? 'Processing...' : 'Buy'}
              {loadingTier !== tier.id && <ArrowRight className="h-3 w-3 group-hover:translate-x-1 transition-transform" />}
            </button>
          </motion.div>
        ))}
      </div>
      )}
    </div>
  )
}
