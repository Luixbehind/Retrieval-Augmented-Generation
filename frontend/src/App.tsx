import { Route, Routes } from "react-router-dom"
import { AppLayout } from "@/components/layout/app-layout"
import { DashboardPage } from "@/pages/dashboard-page"
import { ClientsPage } from "@/pages/clients-page"
import { KnowledgeBasesPage } from "@/pages/knowledge-bases-page"
import { KnowledgeBaseDetailPage } from "@/pages/knowledge-base-detail-page"
import { SettingsPage } from "@/pages/settings-page"

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/clients" element={<ClientsPage />} />
        <Route path="/knowledge-bases" element={<KnowledgeBasesPage />} />
        <Route path="/knowledge-bases/:knowledgeBaseId" element={<KnowledgeBaseDetailPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}

export default App
