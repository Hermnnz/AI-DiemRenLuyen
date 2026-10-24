import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';

export const AdminCampaigns: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Quản trị Cấu hình Đợt Đánh giá</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Khởi tạo đợt, thiết lập thời hạn, trần số lượt bổ sung và bộ tiêu chí</p>
        </div>
        <button className="btn btn-primary">+ Tạo đợt đánh giá mới</button>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#1e40af' }}>
              Đợt đánh giá ĐRL Học kỳ 1 2026-2027 (Minh họa)
            </h3>
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.25rem' }}>
              Mã học kỳ: HK1-2026-2027 | Lớp: LOP-DEMO
            </p>
          </div>
          <StatusBadge status="DRAFT" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', borderTop: '1px solid #f1f5f9', paddingTop: '1rem', marginBottom: '1.25rem' }}>
          <div>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Thời gian mở nộp</div>
            <Deadline isoString="2026-10-25T01:00:00Z" label="Mở" />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Hạn nộp hồ sơ</div>
            <Deadline isoString="2026-10-30T17:00:00Z" label="Đóng" />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Giới hạn lượt bổ sung</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, marginTop: '0.25rem' }}>INFO: 2 lượt | PROOF: 2 lượt</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', borderTop: '1px solid #f1f5f9', paddingTop: '1rem' }}>
          <button className="btn btn-secondary">Chỉnh sửa tiêu chí</button>
          <button className="btn btn-primary">Lên lịch / Mở đợt</button>
        </div>
      </div>
    </div>
  );
};
