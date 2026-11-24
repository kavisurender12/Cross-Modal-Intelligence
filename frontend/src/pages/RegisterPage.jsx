import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Zap, Mail, Lock, User, Eye, EyeOff, ArrowRight, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name || !form.email || !form.password) { toast.error('All fields required'); return }
    if (form.password !== form.confirm) { toast.error('Passwords do not match'); return }
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    if (!/[A-Za-z]/.test(form.password)) { toast.error('Password must contain a letter'); return }
    if (!/\d/.test(form.password)) { toast.error('Password must contain a number'); return }
    setLoading(true)
    try {
      await register(form.name, form.email, form.password)
      toast.success('Account created!')
      navigate('/dashboard')
    } catch (err) {
      const serverMsg = err.response?.data?.message || err.response?.data?.error
      const networkMsg = err.code === 'ERR_NETWORK' ? 'Network error: Cannot connect to Render backend' : null
      toast.error(serverMsg || networkMsg || err.message || 'Registration failed')
    } finally { setLoading(false) }
  }

  const F = (key) => ({ value: form[key], onChange: e => setForm(p => ({ ...p, [key]: e.target.value })) })

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ background: '#02040f' }}>
      <div className="fixed top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full blur-3xl pointer-events-none opacity-10"
        style={{ background: 'radial-gradient(circle, #8b5cf6, transparent)' }} />

      <div className="w-full max-w-md relative animate-slide-up">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-violet-700 flex items-center justify-center shadow-lg">
              <Zap className="w-6 h-6 text-white" />
            </div>
          </Link>
          <h1 className="text-3xl font-black text-white">Create Account</h1>
          <p className="text-slate-500 mt-2 text-sm">Join CYBERNEX AI — free forever</p>
        </div>

        <div className="cx-card-glow p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {[
              { key: 'name',    label: 'Full Name',       type: 'text',     Icon: User,  ph: 'Your name',    ac: 'name' },
              { key: 'email',   label: 'Email Address',   type: 'email',    Icon: Mail,  ph: 'you@example.com', ac: 'email' },
            ].map(({ key, label, type, Icon, ph, ac }) => (
              <div key={key}>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">{label}</label>
                <div className="relative">
                  <Icon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input type={type} className="cx-input pl-10" placeholder={ph} autoComplete={ac} {...F(key)} />
                </div>
              </div>
            ))}
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type={show ? 'text' : 'password'} className="cx-input pl-10 pr-10"
                  placeholder="Min 8 chars, one letter, one number" {...F('password')} />
                <button type="button" onClick={() => setShow(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                  {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="password" className="cx-input pl-10" placeholder="Repeat password" {...F('confirm')} />
              </div>
            </div>
            <button type="submit" className="cx-btn-primary w-full py-3" disabled={loading}>
              {loading
                ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Creating…</>
                : <>Create Account <ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>
          <p className="text-center text-slate-500 text-sm mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-400 hover:text-blue-300 font-semibold">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
