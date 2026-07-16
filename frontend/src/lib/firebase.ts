import { initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'

// Firebase Web config is NOT a secret -- it identifies the project, it
// doesn't authorize anything by itself (Firebase enforces access via
// Security Rules / backend ID-token verification, not by hiding this
// object). Still sourced from env vars rather than hardcoded so different
// environments (dev/staging/prod Firebase projects) can point at different
// projects without a code change. See frontend/.env.example.
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

export const firebaseApp = initializeApp(firebaseConfig)
export const firebaseAuth = getAuth(firebaseApp)
