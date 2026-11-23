import React, { useState } from 'react'
import { AlertTriangle, AlertCircle } from 'lucide-react'
import { detectAPI } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import ResultCard from '../components/ResultCard'
import toast from 'react-hot-toast'

const CATS = ['UPI/Payment Scam','Job Scam','Lottery/Prize Scam','Shopping Scam','Investment Scam','Impersonation Scam','Loan Scam']

const EXAMPLES = [
  { label: 'Lottery scam',    text: 'Congratulations! You have won Rs 10,00,000 in our lucky draw! Send Rs 500 processing fee via UPI to claim your prize. Contact on WhatsApp immediately!' },
  { label: 'Job scam',        text: 'Work from home job offer! Earn Rs 5000 daily guaranteed. No experience needed. Part time hiring. Apply now! Registration fee Rs 999 only.' },
  { label: 'UPI/KYC scam',   text: 'Your KYC is expiring today. Your account will be blocked. Verify your Aadhaar and OTP immediately on this link to avoid suspension.' },
]

export default function FraudPage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const analyse = async (e) => {
    e.preventDefault()
    if (!text.trim()) { toast.error('Paste a suspicious message'); return }
    setLoading(true); setResult(null)
    try {
      const r = await detectAPI.digitalFraud({ text })
      setResult(r.data.data)
    } catch (err) { toast.error(err.response?.data?.message || 'Analysis failed') }
    finally { setLoading(false) }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #ea580c, #ef4444)', boxShadow: '0 0 20px rgba(234,88,12,0.3)' }}>
          <AlertTriangle className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">Fraud Detection</h1>
          <p className="text-slate-500 text-xs mt-0.5">7-category scam pattern recognition + ML classification</p>
        </div>
      </div>

      {/* Category pills */}
      <div className="cx-card p-4">
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Detectable Categories</div>
        <div className="flex flex-wrap gap-2">
          {CATS.map(c => (
            <span key={c} className="text-[10px] font-semibold px-2.5 py-1 rounded-lg"
              style={{ background: 'rgba(249,115,22,0.1)', color: '#fb923c', border: '1px solid rgba(249,115,22,0.2)' }}>
              {c}
            </span>
          ))}
        </div>
      </div>

      <div className="cx-card-glow p-6 space-y-5">
        <form onSubmit={analyse} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Suspicious Message
            </label>
            <textarea className="cx-textarea min-h-[180px] text-sm"
              placeholder="Paste suspicious SMS, WhatsApp message, job offer, lottery notice, or any suspicious text here…"
              value={text} onChange={e => setText(e.target.value)} maxLength={5000} />
            <div className="text-[10px] text-slate-600 text-right mt-1 font-mono">{text.length}/5000</div>
          </div>

          {/* Quick examples */}
          <div className="space-y-1.5">
            <div className="text-[10px] text-slate-600 font-semibold uppercase tracking-wider">Quick Examples</div>
            {EXAMPLES.map(ex => (
              <button key={ex.label} type="button"
                onClick={() => { setText(ex.text); setResult(null) }}
                className="w-full text-left p-3 rounded-xl transition-all group"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(249,115,22,0.3)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'}>
                <div className="text-[10px] font-bold text-orange-500/80 mb-0.5">{ex.label}</div>
                <div className="text-xs text-slate-500 truncate">{ex.text.slice(0, 90)}…</div>
              </button>
            ))}
          </div>

          <button type="submit" className="cx-btn-primary w-full py-3" disabled={loading}>
            {loading ? 'Detecting…' : 'Detect Fraud Pattern'}
          </button>
        </form>
      </div>

      {loading && <LoadingSpinner message="Identifying fraud patterns…" sub="Running 7-category rule engine + ML classifier" />}
      {result && !loading && <ResultCard result={result} />}
    </div>
  )
}
