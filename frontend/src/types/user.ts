export type Role = 'reviewer' | 'approver' | 'admin'

export interface UserProfile {
  uid: string
  email: string | null
  role: Role
}

const ROLE_RANK: Record<Role, number> = { reviewer: 0, approver: 1, admin: 2 }

/** True if `role` is at least `minimum` -- mirrors the backend's
 * require_role() cumulative-rank logic (app/auth/__init__.py) so the UI
 * hides/disables actions consistently with what the API would actually
 * reject, instead of showing a button that always 403s. */
export function hasRoleAtLeast(role: Role | undefined, minimum: Role): boolean {
  if (!role) return false
  return ROLE_RANK[role] >= ROLE_RANK[minimum]
}
