import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { Link } from 'react-router-dom';

export const StudentDashboard: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Bảng tin Sinh viên</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Theo dõi tiến độ nộp và đánh giá rèn luyện cá nhân</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#1e40af' }}>
              Đợt đánh giá ĐRL Học kỳ 1 2026-2027 (Minh họa)
            </h3>
            <p style={{ fontSize: '0.875rem', color: '#64748b', marginTop: '0.25rem' }}>
              Học kỳ: HK1-2026-2027 | Lớp: LOP-DEMO
            </p>
          </div>
          <StatusBadge status="OPEN" />
        </div>

        <div style={{ marginTop: '1.25rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', borderTop: '1px solid #f1f5f9', paddingTop: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Trạng thái hồ sơ</div>
            <div style={{ marginTop: '0.25rem' }}>
              <StatusBadge status="DRAFT" />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Hạn chót nộp hồ sơ</div>
            <div style={{ marginTop: '0.25rem' }}>
              <Deadline isoString="2026-10-30T17:00:00Z" />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Tổng điểm tự khai</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#1e40af', marginTop: '0.1rem' }}>
              0.00 / 30.00
            </div>
          </div>
        </div>

        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
          <Link to="/student/submission" className="btn btn-primary">
            Điền tự chấm & Tải minh chứng
          </Link>
          <Link to="/student/result" className="btn btn-secondary">
            Xem kết quả dự kiến
          </Link>
        </div>
      </div>
    </div>
  );
};
