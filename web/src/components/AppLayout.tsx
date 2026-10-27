import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Role } from '../api/types';

interface AppLayoutProps {
  currentRole?: Role;
  onRoleChange?: (role: Role) => void;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ currentRole: propRole, onRoleChange }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Ưu tiên vai trò thực từ phiên làm việc đã xác thực
  const currentRole = user?.role || propRole || 'STUDENT';
  const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true';

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const isBcs = currentRole === 'BCS';

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {isDemoMode && (
        <div className="demo-banner" role="status">
          Dữ liệu minh họa — không dùng để ra quyết định thật.
        </div>
      )}

      {/* 2. Top Navigation Bar */}
      <header
        style={{
          backgroundColor: '#ffffff',
          borderBottom: '1px solid #e2e8f0',
          padding: '0.75rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <h1 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#1e40af' }}>
            Hệ thống Đánh giá ĐRL
          </h1>

          {/* Student Header Navigation */}
          {currentRole === 'STUDENT' && (
            <nav style={{ display: 'flex', gap: '0.75rem' }}>
              <NavLink
                to="/student"
                end
                style={({ isActive }) => ({
                  padding: '0.4rem 0.75rem',
                  borderRadius: '6px',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  backgroundColor: isActive ? '#eff6ff' : 'transparent',
                  color: isActive ? '#1e40af' : '#475569',
                })}
              >
                Tổng quan
              </NavLink>
              <NavLink
                to="/student/submission"
                style={({ isActive }) => ({
                  padding: '0.4rem 0.75rem',
                  borderRadius: '6px',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  backgroundColor: isActive ? '#eff6ff' : 'transparent',
                  color: isActive ? '#1e40af' : '#475569',
                })}
              >
                Tự chấm & Nộp
              </NavLink>
              <NavLink
                to="/student/result"
                style={({ isActive }) => ({
                  padding: '0.4rem 0.75rem',
                  borderRadius: '6px',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  backgroundColor: isActive ? '#eff6ff' : 'transparent',
                  color: isActive ? '#1e40af' : '#475569',
                })}
              >
                Kết quả dự kiến
              </NavLink>
              <NavLink
                to="/student/appeal"
                style={({ isActive }) => ({
                  padding: '0.4rem 0.75rem',
                  borderRadius: '6px',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  backgroundColor: isActive ? '#eff6ff' : 'transparent',
                  color: isActive ? '#1e40af' : '#475569',
                })}
              >
                Khiếu nại
              </NavLink>
            </nav>
          )}

          {/* Admin Header Navigation */}
          {currentRole === 'ADMIN' && (
            <nav style={{ display: 'flex', gap: '0.75rem' }}>
              <NavLink
                to="/admin/campaigns"
                style={({ isActive }) => ({
                  padding: '0.4rem 0.75rem',
                  borderRadius: '6px',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  backgroundColor: isActive ? '#eff6ff' : 'transparent',
                  color: isActive ? '#1e40af' : '#475569',
                })}
              >
                ⚙️ Quản lý Đợt đánh giá
              </NavLink>
              <NavLink
                to="/admin/ai-evaluations"
                style={({ isActive }) => ({
                  padding: '0.4rem 0.75rem',
                  borderRadius: '6px',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  backgroundColor: isActive ? '#eff6ff' : 'transparent',
                  color: isActive ? '#1e40af' : '#475569',
                })}
              >
                🤖 Đánh giá chất lượng AI
              </NavLink>
            </nav>
          )}

          {/* GVCN Header Navigation */}
          {currentRole === 'GVCN' && (
            <nav style={{ display: 'flex', gap: '0.75rem' }}>
              <NavLink
                to="/gvcn/final-scores"
                style={({ isActive }) => ({
                  padding: '0.4rem 0.75rem',
                  borderRadius: '6px',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  backgroundColor: isActive ? '#eff6ff' : 'transparent',
                  color: isActive ? '#1e40af' : '#475569',
                })}
              >
                🎓 Bảng điểm chính thức lớp
              </NavLink>
            </nav>
          )}
        </div>

        {/* User Profile & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {/* Thông tin tài khoản đăng nhập */}
          {user && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600, color: '#1e293b' }}>{user.full_name || user.username}</span>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  padding: '0.15rem 0.45rem',
                  borderRadius: '4px',
                  backgroundColor: '#e2e8f0',
                  color: '#475569',
                }}
              >
                {user.role}
              </span>
            </div>
          )}

          {/* Demo Role Switcher - CHỈ hiển thị khi VITE_DEMO_MODE=true */}
          {isDemoMode && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.825rem', backgroundColor: '#fef3c7', padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid #fde68a' }}>
              <span style={{ color: '#b45309', fontWeight: 600 }}>DEMO MOCK:</span>
              <select
                value={currentRole}
                onChange={(e) => {
                  const nextRole = e.target.value as Role;
                  onRoleChange?.(nextRole);
                  if (nextRole === 'STUDENT') navigate('/student');
                  else if (nextRole === 'BCS') navigate('/bcs');
                  else if (nextRole === 'GVCN') navigate('/gvcn/final-scores');
                  else if (nextRole === 'ADMIN') navigate('/admin/campaigns');
                }}
                style={{
                  padding: '0.2rem 0.4rem',
                  borderRadius: '4px',
                  border: '1px solid #cbd5e1',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                }}
              >
                <option value="STUDENT">STUDENT (Sinh viên)</option>
                <option value="BCS">BCS (Ban cán sự lớp)</option>
                <option value="GVCN">GVCN (Giáo viên chủ nhiệm)</option>
                <option value="ADMIN">ADMIN (Quản trị viên)</option>
              </select>
            </div>
          )}

          <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: '0.35rem 0.8rem', fontSize: '0.85rem' }}>
            Đăng xuất
          </button>
        </div>
      </header>

      {/* 3. Main Container Area */}
      <div style={{ display: 'flex', flex: 1 }}>
        {/* BCS Left Sidebar (240px) */}
        {isBcs && (
          <aside
            style={{
              width: 'var(--sidebar-width)',
              backgroundColor: '#ffffff',
              borderRight: '1px solid #e2e8f0',
              padding: '1.25rem 0.75rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
            }}
          >
            <div style={{ padding: '0 0.5rem 0.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
              Ban Cán Sự Lớp
            </div>
            <NavLink
              to="/bcs"
              end
              style={({ isActive }) => ({
                display: 'block',
                padding: '0.5rem 0.75rem',
                borderRadius: '6px',
                fontWeight: 500,
                fontSize: '0.875rem',
                backgroundColor: isActive ? '#eff6ff' : 'transparent',
                color: isActive ? '#1e40af' : '#475569',
              })}
            >
              📊 Tổng quan đợt
            </NavLink>
            <NavLink
              to="/bcs/cases"
              style={({ isActive }) => ({
                display: 'block',
                padding: '0.5rem 0.75rem',
                borderRadius: '6px',
                fontWeight: 500,
                fontSize: '0.875rem',
                backgroundColor: isActive ? '#eff6ff' : 'transparent',
                color: isActive ? '#1e40af' : '#475569',
              })}
            >
              📁 Hàng chờ hồ sơ
            </NavLink>
            <NavLink
              to="/bcs/scores"
              style={({ isActive }) => ({
                display: 'block',
                padding: '0.5rem 0.75rem',
                borderRadius: '6px',
                fontWeight: 500,
                fontSize: '0.875rem',
                backgroundColor: isActive ? '#eff6ff' : 'transparent',
                color: isActive ? '#1e40af' : '#475569',
              })}
            >
              📋 Bảng điểm & Công bố
            </NavLink>
            <NavLink
              to="/bcs/appeals"
              style={({ isActive }) => ({
                display: 'block',
                padding: '0.5rem 0.75rem',
                borderRadius: '6px',
                fontWeight: 500,
                fontSize: '0.875rem',
                backgroundColor: isActive ? '#eff6ff' : 'transparent',
                color: isActive ? '#1e40af' : '#475569',
              })}
            >
              ⚖️ Xử lý khiếu nại
            </NavLink>
          </aside>
        )}

        {/* Content View */}
        <main style={{ flex: 1, padding: '1.5rem', backgroundColor: '#f8fafc' }}>
          <div className="container">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
