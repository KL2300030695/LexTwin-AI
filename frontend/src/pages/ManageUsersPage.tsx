import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listUsers, setUserRole } from '../api/client'
import type { Role, UserProfile } from '../types/user'

const ROLES: Role[] = ['reviewer', 'approver', 'admin']

export default function ManageUsersPage() {
  const [users, setUsers] = useState<UserProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [updatingUid, setUpdatingUid] = useState<string | null>(null)

  useEffect(() => {
    refresh()
  }, [])

  function refresh() {
    setLoading(true)
    listUsers()
      .then(setUsers)
      .finally(() => setLoading(false))
  }

  async function handleRoleChange(uid: string, role: Role) {
    setUpdatingUid(uid)
    try {
      const updated = await setUserRole(uid, role)
      setUsers((prev) => prev.map((u) => (u.uid === uid ? updated : u)))
    } finally {
      setUpdatingUid(null)
    }
  }

  if (loading) return <p className="p-8 text-slate-body">Loading users…</p>

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <Link to="/account" className="text-sm text-slate-body hover:underline">
        ← Back to account
      </Link>
      <h1 className="mt-2 font-serif text-2xl font-medium text-ink">Manage Users</h1>
      <p className="mt-1 text-sm text-slate-body">
        A role change takes effect the next time that user's browser refreshes their session token — usually within
        an hour, or immediately if they sign out and back in.
      </p>

      <ul className="mt-6 space-y-2">
        {users.map((u) => (
          <li
            key={u.uid}
            className="flex items-center justify-between gap-3 rounded-md border border-ledger bg-white p-3.5"
          >
            <div>
              <p className="text-sm text-ink">{u.email ?? u.uid}</p>
              <p className="font-mono text-[11px] text-slate-body/70">{u.uid}</p>
            </div>
            <select
              value={u.role}
              disabled={updatingUid === u.uid}
              onChange={(e) => handleRoleChange(u.uid, e.target.value as Role)}
              className="rounded-sm border border-ledger px-2 py-1 text-sm capitalize text-ink disabled:opacity-50"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
    </div>
  )
}
