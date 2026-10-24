import React, { useState } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { ConfirmDialog } from '../../components/ConfirmDialog';

export const StudentSubmission: React.FC = () => {
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Biểu mẫu Tự đánh giá & Nộp minh chứng</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Hồ sơ phiên bản 1 — Chế độ điền nháp và nộp minh chứng
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <StatusBadge status="DRAFT" />
          <Deadline isoString="2026-10-30T17:00:00Z" />
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
          Danh sách tiêu chí đánh giá
        </h3>

        {/* Tiêu chí 1 */}
        <div style={{ border: '1px solid #e2e8f0', borderRadius: '6px', padding: '1rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <div>
              <span style={{ fontWeight: 600, color: '#1e40af' }}>TC01: Ý thức tham gia học tập</span>
              <span style={{ fontSize: '0.8rem', color: '#dc2626', marginLeft: '0.5rem' }}>(Bắt buộc minh chứng)</span>
            </div>
            <span style={{ fontWeight: 600 }}>Tối đa: 10.00 điểm</span>
          </div>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '0.75rem' }}>
            Dữ liệu minh họa — Điểm trung bình học kỳ, chứng chỉ chuyên cần, nghiên cứu khoa học.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: '1rem', alignItems: 'center' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '0.25rem' }}>Điểm tự chấm</label>
              <input type="text" defaultValue="8.00" style={{ width: '100%', padding: '0.4rem', border: '1px solid #cbd5e1', borderRadius: '4px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '0.25rem' }}>Ghi chú giải trình</label>
              <input type="text" placeholder="Ghi chú minh chứng đính kèm" style={{ width: '100%', padding: '0.4rem', border: '1px solid #cbd5e1', borderRadius: '4px' }} />
            </div>
          </div>
        </div>

        {/* Action bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.5rem', borderTop: '1px solid #e2e8f0', paddingTop: '1rem' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#1e40af' }}>
            Tổng điểm tự khai: 8.00 / 30.00
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button className="btn btn-secondary">Lưu nháp</button>
            <button className="btn btn-primary" onClick={() => setShowConfirm(true)}>Nộp hồ sơ</button>
          </div>
        </div>
      </div>

      <ConfirmDialog
        isOpen={showConfirm}
        title="Xác nhận nộp hồ sơ đánh giá"
        message="Sau khi nộp, hồ sơ sẽ được chuyển đến Ban cán sự lớp kiểm tra. Bạn chỉ có thể sửa đổi nếu nhận được yêu cầu bổ sung."
        confirmLabel="Đồng ý nộp"
        onConfirm={() => setShowConfirm(false)}
        onCancel={() => setShowConfirm(false)}
      />
    </div>
  );
};
