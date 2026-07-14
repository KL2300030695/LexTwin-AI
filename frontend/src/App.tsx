import { Route, Routes } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import DocumentView from './pages/DocumentView'
import WorkspacePage from './pages/WorkspacePage'
import PlaybookPage from './pages/PlaybookPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<UploadPage />} />
      <Route path="/document/:docId" element={<DocumentView />} />
      <Route path="/workspace/:msaId/:sowId" element={<WorkspacePage />} />
      <Route path="/playbook" element={<PlaybookPage />} />
    </Routes>
  )
}
