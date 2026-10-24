import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Role } from '../api/types';

interface LoginPageProps {
  onLoginSuccess: (role: Role) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('sv001');
  const [password, setPassword] = useState('Demo@123456');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Chuyển hướng theo tiền tố tài khoản cho phiên bản shell Giai đoạn 0
    const uname = username.toLowerCase().trim();
    let role: Role = 'STUDENT';
    let target = '/student';

    if (uname.startsWith('bcs')) {
      role = 'BCS';
      target = '/bcs';
    } else if (uname.startsWith('gvcn')) {
      role = 'GVCN';
      target = '/gvcn/final-scores';
    } else if (uname.startsWith('admin')) {
      role = 'ADMIN';
      target = '/admin/campaigns';
    }

    onLoginSuccess(role);
    navigate(target);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f1f5f9',
        padding: '1rem',
      }}
    >
      <div className="card" style={{ maxWidth: '420px', width: '100%', padding: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e40af' }}>Đăng Nhập</h2>
          <p style={{ fontSize: '0.875rem', color: '#64748b', marginTop: '0.25rem' }}>
            Hệ thống Chấm Điểm Rèn Luyện (Vỏ V1)
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: '0.75rem',
              borderRadius: '6px',
              backgroundColor: '#fee2e2',
              color: '#b91c1c',
              fontSize: '0.875rem',
              marginBottom: '1rem',
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>
              Tên đăng nhập
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="sv001, bcs001, gvcn001, admin001"
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '0.9rem',
              }}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>
              Mật khẩu
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '0.9rem',
              }}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" style={{ marginTop: '0.5rem', width: '100%' }}>
            Đăng nhập
          </button>
        </form>

        <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', color: '#64748b', borderTop: '1px solid #e2e8f0', paddingTop: '1rem' }}>
          <strong>Tài khoản demo:</strong>
          <ul style={{ paddingLeft: '1.25rem', marginTop: '0.25rem', lineHeight: 1.6 }}>
            <li>Sinh viên: <code>sv001</code> / <code>Demo@123456</code></li>
            <li>Ban cán sự: <code>bcs001</code> / <code>Demo@123456</code></li>
            <li>GVCN: <code>gvcn001</code> / <code>Demo@123456</code></li>
            <li>Quản trị: <code>admin001</code> / <code>Demo@123456</code></li>
          </ul>
        </div>
      </div>
    </div>
  );
};
