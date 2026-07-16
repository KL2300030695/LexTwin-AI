import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User as FirebaseUser,
} from 'firebase/auth'
import { firebaseAuth } from '../lib/firebase'
import type { Role, UserProfile } from '../types/user'

interface AuthContextValue {
  user: FirebaseUser | null
  profile: UserProfile | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  /** Re-reads the ID token's custom claims -- call this after an admin
   * changes your role, since an already-issued token keeps its old claims
   * until force-refreshed (Firebase doesn't push claim changes live). */
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function buildProfile(user: FirebaseUser, forceRefresh: boolean): Promise<UserProfile> {
  const tokenResult = await user.getIdTokenResult(forceRefresh)
  const role = (tokenResult.claims.role as Role | undefined) ?? 'reviewer'
  return { uid: user.uid, email: user.email, role }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<FirebaseUser | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(firebaseAuth, async (nextUser) => {
      setUser(nextUser)
      if (nextUser) {
        setProfile(await buildProfile(nextUser, false))
      } else {
        setProfile(null)
      }
      setLoading(false)
    })
    return unsubscribe
  }, [])

  async function login(email: string, password: string) {
    await signInWithEmailAndPassword(firebaseAuth, email, password)
  }

  async function signup(email: string, password: string) {
    await createUserWithEmailAndPassword(firebaseAuth, email, password)
  }

  async function logout() {
    await signOut(firebaseAuth)
  }

  async function refreshProfile() {
    if (!firebaseAuth.currentUser) return
    setProfile(await buildProfile(firebaseAuth.currentUser, true))
  }

  return (
    <AuthContext.Provider value={{ user, profile, loading, login, signup, logout, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth() must be used within an AuthProvider')
  return ctx
}
