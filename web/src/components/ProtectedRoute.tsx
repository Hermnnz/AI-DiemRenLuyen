import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Role } from '../api/types';

interface ProtectedRouteProps {
  children: React.ReactElement;
  allowedRoles: Role[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div
        style={{
          minHeight: '60vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '1rem',
          color: '#64748b',
        }}
      >
        <div
          style={{
            width: '36px',
            height: '36px',
            border: '3px solid #cbd5e1',
            borderTopColor: '#2563eb',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }}
        />
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        <p style={{ fontSize: '0.9rem' }}>Đang xác thực phiên làm việc...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!allowedRoles.includes(user.role)) {
    const roleHomeMap: Record<Role, string> = {
      STUDENT: '/student',
      BCS: '/bcs',
      GVCN: '/gvcn/final-scores',
      ADMIN: '/admin/campaigns',
    };
    const homeUrl = roleHomeMap[user.role] || '/login';

    return (
      <div style={{ maxWidth: '540px', margin: '4rem auto', padding: '2rem', textAlign: 'center' }}>
        <div className="card" style={{ padding: '2.5rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🚫</div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#b91c1c', marginBottom: '0.5rem' }}>
            403 — Không có quyền truy cập
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: 1.6 }}>
            Tài khoản của bạn có vai trò <strong>{user.role}</strong> ({user.full_name}). Trang này yêu cầu vai trò:{' '}
            <strong>{allowedRoles.join(', ')}</strong>.
          </p>
          <Link to={homeUrl} className="btn btn-primary" style={{ display: 'inline-block' }}>
            Về trang làm việc của bạn
          </Link>
        </div>
      </div>
    );
  }

  return children;
};
