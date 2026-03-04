import { Routes, Route } from "react-router-dom"
import Layout from "@/components/Layout"
import Dashboard from "@/pages/Dashboard"
import ReportDetail from "@/pages/ReportDetail"
import PipelineMonitor from "@/pages/PipelineMonitor"
import FailedRequests from "@/pages/FailedRequests"

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/reports/:id" element={<ReportDetail />} />
        <Route path="/pipeline" element={<PipelineMonitor />} />
        <Route path="/failed" element={<FailedRequests />} />
      </Routes>
    </Layout>
  )
}
