import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { hasRoleAtLeast } from '../types/user'
import type { Role } from '../types/user'

export default function ProtectedRoute({
  children,
  requireRole,
}: {
  children: ReactNode
  /** If set, requires at least this role in addition to being logged in --
   * e.g. the Manage Users page requires 'admin'. Unauthenticated users
   * still get redirected to /login rather than seeing a 403 page. */
  requireRole?: Role
}) {
  const { user, profile, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-slate-body">Loading…</div>
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (requireRole && !hasRoleAtLeast(profile?.role, requireRole)) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 text-center">
        <p className="text-sm text-slate-body">
          This page requires the "{requireRole}" role. You're signed in as "{profile?.role ?? 'reviewer'}".
        </p>
      </div>
    )
  }

  return <>{children}</>
}
