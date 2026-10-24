import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Role } from './api/types';
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

export const App: React.FC = () => {
  const [currentRole, setCurrentRole] = useState<Role>('STUDENT');

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Login Route */}
        <Route path="/login" element={<LoginPage onLoginSuccess={(role) => setCurrentRole(role)} />} />

        {/* Authenticated Layout Routes */}
        <Route element={<AppLayout currentRole={currentRole} onRoleChange={(role) => setCurrentRole(role)} />}>
          <Route path="/" element={<Navigate to="/student" replace />} />

          {/* Student Routes */}
          <Route path="/student" element={<StudentDashboard />} />
          <Route path="/student/submission" element={<StudentSubmission />} />
          <Route path="/student/result" element={<StudentResult />} />
          <Route path="/student/appeal" element={<StudentAppeal />} />

          {/* BCS Routes */}
          <Route path="/bcs" element={<BcsDashboard />} />
          <Route path="/bcs/cases" element={<BcsCases />} />
          <Route path="/bcs/cases/:id" element={<BcsCaseDetail />} />
          <Route path="/bcs/scores" element={<BcsScores />} />
          <Route path="/bcs/appeals" element={<BcsAppeals />} />

          {/* Admin Routes */}
          <Route path="/admin/campaigns" element={<AdminCampaigns />} />

          {/* GVCN Routes */}
          <Route path="/gvcn/final-scores" element={<GvcnFinalScores />} />
        </Route>

        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
