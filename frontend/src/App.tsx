import { Route, Routes } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import DocumentView from './pages/DocumentView'
import WorkspacePage from './pages/WorkspacePage'
import PlaybookPage from './pages/PlaybookPage'
import LoginPage from './pages/LoginPage'
import AccountPage from './pages/AccountPage'
import ManageUsersPage from './pages/ManageUsersPage'
import ProtectedRoute from './components/ProtectedRoute'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <UploadPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/document/:docId"
        element={
          <ProtectedRoute>
            <DocumentView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/workspace/:msaId/:sowId"
        element={
          <ProtectedRoute>
            <WorkspacePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/playbook"
        element={
          <ProtectedRoute>
            <PlaybookPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/account"
        element={
          <ProtectedRoute>
            <AccountPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute requireRole="admin">
            <ManageUsersPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
