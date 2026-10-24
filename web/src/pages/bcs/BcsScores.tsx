import React, { useState } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';

export const BcsScores: React.FC = () => {
  const [showPublishConfirm, setShowPublishConfirm] = useState(false);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Bảng điểm Dự kiến Cả lớp & Công bố</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Ghi nhận biên bản họp BCS/Lớp và công bố điểm rèn luyện</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowPublishConfirm(true)}>
          Công bố điểm dự kiến
        </button>
      </div>

      {/* Biên bản họp */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>Biên bản Họp Bình xét</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          <div style={{ border: '1px solid #e2e8f0', borderRadius: '6px', padding: '0.75rem' }}>
            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>✅ Cuộc họp 1: Họp Ban cán sự</div>
            <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem' }}>Thời gian: 27/10/2026 14:00</div>
            <div style={{ fontSize: '0.8rem', color: '#475569', marginTop: '0.25rem' }}>"Đã rà soát 100% hồ sơ trong lớp"</div>
          </div>
          <div style={{ border: '1px solid #e2e8f0', borderRadius: '6px', padding: '0.75rem' }}>
            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>✅ Cuộc họp 2: Họp toàn Thể Lớp</div>
            <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem' }}>Thời gian: 27/10/2026 16:00</div>
            <div style={{ fontSize: '0.8rem', color: '#475569', marginTop: '0.25rem' }}>"Lớp đã biểu quyết thông qua"</div>
          </div>
        </div>
      </div>

      {/* Bảng điểm */}
      <div className="card">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e2e8f0', textAlign: 'left', color: '#64748b' }}>
              <th style={{ padding: '0.75rem 0.5rem' }}>Mã SV</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Họ và tên</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Trạng thái</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Điểm tự khai</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Điểm dự kiến</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>SV001</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>Nguyễn Văn An</td>
              <td style={{ padding: '0.75rem 0.5rem' }}><StatusBadge status="PROPOSED" /></td>
              <td style={{ padding: '0.75rem 0.5rem' }}>26.00</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600, color: '#1e40af' }}>24.00</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>SV002</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>Trần Thị Bình</td>
              <td style={{ padding: '0.75rem 0.5rem' }}><StatusBadge status="PROPOSED" /></td>
              <td style={{ padding: '0.75rem 0.5rem' }}>28.00</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600, color: '#1e40af' }}>28.00</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>SV003</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>Lê Văn Cường</td>
              <td style={{ padding: '0.75rem 0.5rem' }}><StatusBadge status="PROPOSED" /></td>
              <td style={{ padding: '0.75rem 0.5rem' }}>22.00</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600, color: '#1e40af' }}>20.00</td>
            </tr>
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        isOpen={showPublishConfirm}
        title="Xác nhận công bố điểm dự kiến"
        message="Điểm rèn luyện dự kiến sẽ được công bố công khai đến toàn bộ sinh viên trong lớp. Sinh viên sẽ có 72 giờ để xác nhận hoặc khiếu nại."
        confirmLabel="Công bố ngay"
        onConfirm={() => setShowPublishConfirm(false)}
        onCancel={() => setShowPublishConfirm(false)}
      />
    </div>
  );
};
