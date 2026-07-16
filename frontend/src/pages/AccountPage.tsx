import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { bootstrapFirstAdmin } from '../api/client'
import { hasRoleAtLeast } from '../types/user'

export default function AccountPage() {
  const { profile, logout, refreshProfile } = useAuth()
  const navigate = useNavigate()
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleBootstrap() {
    setBusy(true)
    setMessage(null)
    setError(null)
    try {
      await bootstrapFirstAdmin()
      await refreshProfile()
      setMessage('You are now an admin.')
    } catch {
      setError('An admin already exists — ask them to assign your role from Manage Users instead.')
    } finally {
      setBusy(false)
    }
  }

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="mx-auto max-w-lg px-6 py-10">
      <Link to="/" className="text-sm text-slate-body hover:underline">
        ← Back to documents
      </Link>
      <h1 className="mt-2 font-serif text-2xl font-medium text-ink">Account</h1>

      <div className="mt-6 rounded-md border border-ledger bg-white p-5">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">Signed in as</p>
        <p className="mt-1 text-sm text-ink">{profile?.email}</p>
        <p className="mt-3 font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">Role</p>
        <p className="mt-1 text-sm capitalize text-ink">{profile?.role}</p>
      </div>

      {!hasRoleAtLeast(profile?.role, 'admin') && (
        <div className="mt-4 rounded-md border border-ledger bg-ledger-soft/60 p-4">
          <p className="text-sm text-slate-body">
            No admin has claimed this instance yet? You can promote yourself — this only succeeds while zero admins
            exist system-wide.
          </p>
          <button
            onClick={handleBootstrap}
            disabled={busy}
            className="mt-3 rounded-sm border border-ink bg-ink px-3.5 py-1.5 text-sm font-semibold text-paper transition-colors hover:bg-ink-soft disabled:opacity-60"
          >
            Become the first admin
          </button>
        </div>
      )}

      {message && <p className="mt-3 text-sm text-seal-blue">{message}</p>}
      {error && <p className="mt-3 text-sm text-redline">{error}</p>}

      {hasRoleAtLeast(profile?.role, 'admin') && (
        <Link
          to="/admin/users"
          className="mt-4 inline-block rounded-sm border border-ledger px-3.5 py-1.5 text-sm text-ink hover:border-ink"
        >
          Manage Users →
        </Link>
      )}

      <button
        onClick={handleLogout}
        className="mt-6 block text-sm text-slate-body underline decoration-slate-body/40 underline-offset-2 hover:text-ink"
      >
        Sign out
      </button>
    </div>
  )
}
