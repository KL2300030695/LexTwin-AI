import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { login, signup } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/'

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await signup(email, password)
      }
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4">
      <div className="w-full max-w-sm rounded-md border border-ledger bg-white p-8">
        <h1 className="font-serif text-xl font-medium text-ink">⚖️ LexTwin AI</h1>
        <p className="mt-1 text-sm text-slate-body">{mode === 'login' ? 'Sign in to continue.' : 'Create an account.'}</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-3.5">
          <div>
            <label className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-sm border border-ledger px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue"
            />
          </div>
          <div>
            <label className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">Password</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-sm border border-ledger px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue"
            />
          </div>

          {error && <p className="text-sm text-redline">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-sm border border-ink bg-ink px-4 py-2 text-sm font-semibold text-paper transition-colors hover:bg-ink-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <button
          onClick={() => {
            setMode(mode === 'login' ? 'signup' : 'login')
            setError(null)
          }}
          className="mt-4 w-full text-center text-sm text-slate-body underline decoration-slate-body/40 underline-offset-2 hover:text-ink"
        >
          {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
        </button>

        {mode === 'signup' && (
          <p className="mt-4 rounded-sm border border-ledger bg-ledger-soft/60 p-2.5 text-xs text-slate-body">
            New accounts default to the "reviewer" role. The very first account created can promote itself to admin
            from the Manage Users page.
          </p>
        )}
      </div>
    </div>
  )
}
