import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Role } from '../api/types';

interface AppLayoutProps {
  currentRole: Role;
  onRoleChange?: (role: Role) => void;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ currentRole, onRoleChange }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    navigate('/login');
  };

  const isBcs = currentRole === 'BCS';

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* 1. Mandatory Demo Notice Banner */}
      <div className="demo-banner">
        ⚠️ Dữ liệu minh họa — không dùng để ra quyết định thật | Chế độ kiểm tra thủ công (AI chưa kích hoạt)
      </div>

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

          {/* GVCN Header */}
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
                Bảng điểm chính thức
              </NavLink>
            </nav>
          )}

          {/* ADMIN Header */}
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
                Cấu hình đợt đánh giá
              </NavLink>
            </nav>
          )}
        </div>

        {/* Demo Switcher & Profile */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.825rem' }}>
            <span style={{ color: '#64748b' }}>Vai trò thử nghiệm:</span>
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
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                border: '1px solid #cbd5e1',
                fontSize: '0.825rem',
                fontWeight: 600,
              }}
            >
              <option value="STUDENT">STUDENT (Sinh viên)</option>
              <option value="BCS">BCS (Ban cán sự lớp)</option>
              <option value="GVCN">GVCN (Giáo viên chủ nhiệm)</option>
              <option value="ADMIN">ADMIN (Quản trị viên)</option>
            </select>
          </div>

          <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}>
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
