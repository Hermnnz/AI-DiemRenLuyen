import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';

export const StudentAppeal: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Khiếu nại Điểm Đánh giá</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Chọn các tiêu chí cần xem xét lại và nhập lý do cụ thể
          </p>
        </div>
        <StatusBadge status="PUBLISHED" />
      </div>

      <div className="card">
        <p style={{ fontSize: '0.875rem', color: '#475569', marginBottom: '1.5rem' }}>
          Sinh viên chỉ được gửi khiếu nại một lần trong thời hạn cho phép. Sau khi gửi, Ban cán sự sẽ xem xét và phản hồi.
        </p>

        <div style={{ border: '1px solid #e2e8f0', borderRadius: '6px', padding: '1rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 600 }}>TC03: Ý thức tham gia hoạt động phong trào</span>
            <span>Tự chấm: 8.00 | Điểm dự kiến: 6.00</span>
          </div>
          <textarea
            placeholder="Nhập lý do khiếu nại chi tiết..."
            rows={3}
            style={{ width: '100%', padding: '0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px' }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
          <button className="btn btn-primary">Gửi khiếu nại</button>
        </div>
      </div>
    </div>
  );
};
