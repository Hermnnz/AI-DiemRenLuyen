import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { Link } from 'react-router-dom';

export const StudentResult: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Kết quả Đánh giá Dự kiến</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Kết quả được công bố sau khi BCS và lớp hoàn tất quy trình họp bình xét
          </p>
        </div>
        <StatusBadge status="PUBLISHED" />
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem', marginBottom: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Hạn chót gửi khiếu nại hoặc đồng ý:</div>
            <Deadline isoString="2026-10-31T09:00:00Z" />
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Tổng điểm dự kiến:</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e40af' }}>24.00 / 30.00</div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
          <Link to="/student/appeal" className="btn btn-secondary">
            Khiếu nại điểm
          </Link>
          <button className="btn btn-primary">
            Đồng ý với điểm dự kiến
          </button>
        </div>
      </div>
    </div>
  );
};
