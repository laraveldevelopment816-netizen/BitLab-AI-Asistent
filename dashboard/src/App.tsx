import { Navigate, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Overview }          from './pages/Overview'
import { Sessions }          from './pages/Sessions'
import { SessionDetailPage } from './pages/SessionDetail'
import { Live }              from './pages/Live'
import { History }           from './pages/History'
import { Compare }           from './pages/Compare'
import { Stats }             from './pages/Stats'
import { Settings }          from './pages/Settings'
import { RequestDetail }     from './pages/RequestDetail'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/"             element={<Navigate to="/overview" replace />} />
        <Route path="/overview"     element={<Overview />} />
        <Route path="/sessions"     element={<Sessions />} />
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
        <Route path="/live"         element={<Live />} />
        <Route path="/history"      element={<History />} />
        <Route path="/compare"      element={<Compare />} />
        <Route path="/stats"        element={<Stats />} />
        <Route path="/settings"     element={<Settings />} />
        <Route path="/requests/:id" element={<RequestDetail />} />
      </Routes>
    </Layout>
  )
}
