import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Role, ErrorResponse } from '../api/types';

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const user = await login(username.trim(), password);

      // Điều hướng theo vai trò thực tế trả về từ backend
      const roleHomeMap: Record<Role, string> = {
        STUDENT: '/student',
        BCS: '/bcs',
        GVCN: '/gvcn/final-scores',
        ADMIN: '/admin/campaigns',
      };

      const from = (location.state as any)?.from?.pathname;
      const target = from || roleHomeMap[user.role] || '/student';
      navigate(target, { replace: true });
    } catch (err: any) {
      const errResp = err as ErrorResponse;
      const msg = errResp?.error?.message || 'Tên đăng nhập hoặc mật khẩu không chính xác. Vui lòng kiểm tra lại.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
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
            Hệ thống Đánh giá Điểm Rèn Luyện (V1)
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: '0.75rem 1rem',
              borderRadius: '6px',
              backgroundColor: '#fee2e2',
              border: '1px solid #fecaca',
              color: '#b91c1c',
              fontSize: '0.875rem',
              marginBottom: '1rem',
              lineHeight: 1.5,
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
              placeholder="Nhập tên đăng nhập (ví dụ: sv001, bcs001...)"
              autoComplete="username"
              style={{
                width: '100%',
                padding: '0.55rem 0.75rem',
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
              placeholder="Nhập mật khẩu"
              autoComplete="current-password"
              style={{
                width: '100%',
                padding: '0.55rem 0.75rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '0.9rem',
              }}
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="btn btn-primary"
            style={{ marginTop: '0.5rem', width: '100%', padding: '0.65rem' }}
          >
            {submitting ? 'Đang xác thực...' : 'Đăng nhập'}
          </button>
        </form>

        <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', color: '#64748b', borderTop: '1px solid #e2e8f0', paddingTop: '1rem', lineHeight: 1.6 }}>
          <strong>Tài khoản seed mẫu theo vai trò:</strong>
          <ul style={{ paddingLeft: '1.25rem', marginTop: '0.25rem' }}>
            <li>Sinh viên: <code>sv001</code>, <code>sv002</code>, <code>sv003</code></li>
            <li>Ban cán sự lớp: <code>bcs001</code></li>
            <li>Giáo viên chủ nhiệm: <code>gvcn001</code></li>
            <li>Quản trị viên: <code>admin001</code></li>
          </ul>
          <p style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#94a3b8' }}>
            * Mật khẩu được thiết lập qua biến môi trường DEMO_PASSWORD khi seed database.
          </p>
        </div>
      </div>
    </div>
  );
};
