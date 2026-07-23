import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/lib/auth-context'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AppLayout } from '@/components/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { AcceptInvitePage } from '@/pages/AcceptInvitePage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/pages/ResetPasswordPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { CyclesPage } from '@/pages/CyclesPage'
import { NewCyclePage } from '@/pages/NewCyclePage'
import { CycleDetailPage } from '@/pages/CycleDetailPage'
import { TeamPage } from '@/pages/TeamPage'
import { MyEvaluationsPage } from '@/pages/MyEvaluationsPage'
import { EvaluationDetailPage } from '@/pages/EvaluationDetailPage'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/accept-invite/:token" element={<AcceptInvitePage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/evaluations" element={<MyEvaluationsPage />} />
              <Route path="/evaluations/:id" element={<EvaluationDetailPage />} />
              <Route path="/cycles" element={<CyclesPage />} />
              <Route path="/cycles/new" element={<NewCyclePage />} />
              <Route path="/cycles/:id" element={<CycleDetailPage />} />
              <Route path="/team" element={<TeamPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
