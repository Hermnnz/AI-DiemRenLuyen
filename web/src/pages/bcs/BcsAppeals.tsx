import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';

export const BcsAppeals: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Danh sách Khiếu nại từ Sinh viên</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Xem xét minh chứng bổ sung, quyết định Giữ nguyên hoặc Điều chỉnh điểm</p>
        </div>
        <button className="btn btn-primary">Chốt điểm cả lớp</button>
      </div>

      <div className="card">
        <p style={{ color: '#64748b', fontSize: '0.875rem', textAlign: 'center', padding: '2rem 0' }}>
          Hiện chưa có khiếu nại nào cần xử lý.
        </p>
      </div>
    </div>
  );
};
