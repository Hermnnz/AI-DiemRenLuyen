import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Link } from 'react-router-dom';

export const BcsDashboard: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Tổng quan Ban Cán Sự Lớp</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Lớp: LOP-DEMO | Học kỳ: HK1-2026-2027</p>
        </div>
        <StatusBadge status="REVIEW" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div className="card">
          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Hồ sơ chờ kiểm tra</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#1e40af', marginTop: '0.25rem' }}>1</div>
          <Link to="/bcs/cases" style={{ fontSize: '0.8rem', marginTop: '0.5rem', display: 'inline-block' }}>Xem hàng chờ →</Link>
        </div>
        <div className="card">
          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Chờ sinh viên bổ sung</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#d97706', marginTop: '0.25rem' }}>1</div>
          <Link to="/bcs/cases" style={{ fontSize: '0.8rem', marginTop: '0.5rem', display: 'inline-block' }}>Xem danh sách →</Link>
        </div>
        <div className="card">
          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Đã duyệt điểm dự kiến</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#059669', marginTop: '0.25rem' }}>1</div>
          <Link to="/bcs/scores" style={{ fontSize: '0.8rem', marginTop: '0.5rem', display: 'inline-block' }}>Bảng điểm lớp →</Link>
        </div>
        <div className="card">
          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Khiếu nại cần xử lý</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#dc2626', marginTop: '0.25rem' }}>0</div>
          <Link to="/bcs/appeals" style={{ fontSize: '0.8rem', marginTop: '0.5rem', display: 'inline-block' }}>Xem khiếu nại →</Link>
        </div>
      </div>
    </div>
  );
};
