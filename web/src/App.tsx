import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './components/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { StudentDashboard } from './pages/student/StudentDashboard';
import { StudentSubmission } from './pages/student/StudentSubmission';
import { StudentResult } from './pages/student/StudentResult';
import { StudentAppeal } from './pages/student/StudentAppeal';
import { BcsDashboard } from './pages/bcs/BcsDashboard';
import { BcsCases } from './pages/bcs/BcsCases';
import { BcsCaseDetail } from './pages/bcs/BcsCaseDetail';
import { BcsScores } from './pages/bcs/BcsScores';
import { BcsAppeals } from './pages/bcs/BcsAppeals';
import { AdminCampaigns } from './pages/admin/AdminCampaigns';
import { GvcnFinalScores } from './pages/gvcn/GvcnFinalScores';

const RoleRedirect: React.FC = () => {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === 'BCS') return <Navigate to="/bcs" replace />;
  if (user.role === 'GVCN') return <Navigate to="/gvcn/final-scores" replace />;
  if (user.role === 'ADMIN') return <Navigate to="/admin/campaigns" replace />;
  return <Navigate to="/student" replace />;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Login Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Authenticated Layout Routes */}
          <Route element={<AppLayout />}>
            <Route path="/" element={<RoleRedirect />} />

            {/* Student Routes */}
            <Route
              path="/student"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <StudentDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/student/submission"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <StudentSubmission />
                </ProtectedRoute>
              }
            />
            <Route
              path="/student/result"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <StudentResult />
                </ProtectedRoute>
              }
            />
            <Route
              path="/student/appeal"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <StudentAppeal />
                </ProtectedRoute>
              }
            />

            {/* BCS Routes */}
            <Route
              path="/bcs"
              element={
                <ProtectedRoute allowedRoles={['BCS']}>
                  <BcsDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/bcs/dashboard"
              element={
                <ProtectedRoute allowedRoles={['BCS']}>
                  <BcsDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/bcs/cases"
              element={
                <ProtectedRoute allowedRoles={['BCS']}>
                  <BcsCases />
                </ProtectedRoute>
              }
            />
            <Route
              path="/bcs/cases/:id"
              element={
                <ProtectedRoute allowedRoles={['BCS']}>
                  <BcsCaseDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/bcs/scores"
              element={
                <ProtectedRoute allowedRoles={['BCS']}>
                  <BcsScores />
                </ProtectedRoute>
              }
            />
            <Route
              path="/bcs/appeals"
              element={
                <ProtectedRoute allowedRoles={['BCS']}>
                  <BcsAppeals />
                </ProtectedRoute>
              }
            />

            {/* Admin Routes */}
            <Route
              path="/admin/campaigns"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <AdminCampaigns />
                </ProtectedRoute>
              }
            />

            {/* GVCN Routes */}
            <Route
              path="/gvcn/final-scores"
              element={
                <ProtectedRoute allowedRoles={['GVCN']}>
                  <GvcnFinalScores />
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Fallback route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
