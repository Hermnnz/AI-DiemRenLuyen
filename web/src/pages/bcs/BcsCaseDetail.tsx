import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';

export const BcsCaseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [showCompleteConfirm, setShowCompleteConfirm] = useState(false);

  return (
    <div>
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Link to="/bcs/cases" style={{ fontSize: '0.85rem' }}>← Quay lại hàng chờ</Link>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Hồ sơ SV001 · Nguyễn Văn An</h2>
            <StatusBadge status="BCS_REVIEW" />
          </div>
          <p style={{ color: '#64748b', fontSize: '0.8rem', marginTop: '0.25rem' }}>
            Phiên bản: 4 | Lượt bổ sung: INFO: 1/2, PROOF: 0/2 | Chế độ: <span style={{ fontWeight: 600 }}>Kiểm tra thủ công — AI chưa kích hoạt</span>
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary">Yêu cầu bổ sung</button>
          <button className="btn btn-primary" onClick={() => setShowCompleteConfirm(true)}>
            Hoàn tất kiểm tra
          </button>
        </div>
      </div>

      {/* 3-ZONE LAYOUT */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        {/* VÙNG 1: MINH CHỨNG GỐC */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem', marginBottom: '0.75rem', color: '#1e40af' }}>
            1. Minh chứng gốc
          </h3>
          <div style={{ flex: 1, backgroundColor: '#f1f5f9', borderRadius: '6px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ border: '1px solid #cbd5e1', borderRadius: '4px', padding: '0.75rem', backgroundColor: '#ffffff' }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>📄 bang-diem.pdf</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Kích thước: 1.0 MB | Tải lên: 25/10/2026 11:00</div>
              <button className="btn btn-secondary" style={{ marginTop: '0.5rem', padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                Xem trước an toàn
              </button>
            </div>
            <div style={{ border: '1px solid #cbd5e1', borderRadius: '4px', padding: '0.75rem', backgroundColor: '#ffffff' }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>🖼️ chung-nhan-tinh-nguyen.jpg</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Kích thước: 512 KB | Tải lên: 24/10/2026 09:45</div>
              <button className="btn btn-secondary" style={{ marginTop: '0.5rem', padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                Xem trước an toàn
              </button>
            </div>
          </div>
        </div>

        {/* VÙNG 2: TỰ KHAI & QUY ĐỊNH */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem', marginBottom: '0.75rem', color: '#1e40af' }}>
            2. Tự khai & Quy định
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.875rem' }}>
            <div style={{ borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem' }}>
              <div style={{ fontWeight: 600 }}>TC01: Ý thức tham gia học tập</div>
              <div style={{ color: '#64748b', fontSize: '0.8rem' }}>Tối đa: 10.00 điểm | Tự khai: <span style={{ fontWeight: 600, color: '#0f172a' }}>8.00</span></div>
              <div style={{ marginTop: '0.25rem', fontStyle: 'italic', color: '#475569' }}>"GPA 3.4/4.0"</div>
            </div>
            <div style={{ borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem' }}>
              <div style={{ fontWeight: 600 }}>TC02: Ý thức chấp hành nội quy, quy chế</div>
              <div style={{ color: '#64748b', fontSize: '0.8rem' }}>Tối đa: 10.00 điểm | Tự khai: <span style={{ fontWeight: 600, color: '#0f172a' }}>10.00</span></div>
              <div style={{ marginTop: '0.25rem', fontStyle: 'italic', color: '#475569' }}>"Không vi phạm nội quy"</div>
            </div>
            <div>
              <div style={{ fontWeight: 600 }}>TC03: Ý thức tham gia phong trào</div>
              <div style={{ color: '#64748b', fontSize: '0.8rem' }}>Tối đa: 10.00 điểm | Tự khai: <span style={{ fontWeight: 600, color: '#0f172a' }}>8.00</span></div>
              <div style={{ marginTop: '0.25rem', fontStyle: 'italic', color: '#475569' }}>"Tham gia tiếp sức mùa thi"</div>
            </div>
          </div>
        </div>

        {/* VÙNG 3: QUYẾT ĐỊNH CỦA BCS */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem', marginBottom: '0.75rem', color: '#1e40af' }}>
            3. Quyết định của BCS
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Điểm duyệt TC01:</span>
                <input type="text" defaultValue="8.00" style={{ width: '80px', padding: '0.25rem 0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px' }} />
              </div>
              <input type="text" placeholder="Lý do duyệt..." defaultValue="Minh chứng hợp lệ" style={{ width: '100%', padding: '0.25rem 0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px', fontSize: '0.8rem' }} />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Điểm duyệt TC02:</span>
                <input type="text" defaultValue="10.00" style={{ width: '80px', padding: '0.25rem 0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px' }} />
              </div>
              <input type="text" placeholder="Lý do (bắt buộc nếu khác tự khai)..." style={{ width: '100%', padding: '0.25rem 0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px', fontSize: '0.8rem' }} />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Điểm duyệt TC03:</span>
                <input type="text" defaultValue="6.00" style={{ width: '80px', padding: '0.25rem 0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px' }} />
              </div>
              <input type="text" placeholder="Lý do (bắt buộc vì khác tự chấm)..." defaultValue="Hoạt động cấp khoa chỉ tính 6.00 điểm" style={{ width: '100%', padding: '0.25rem 0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px', fontSize: '0.8rem' }} />
            </div>
          </div>
        </div>
      </div>

      <ConfirmDialog
        isOpen={showCompleteConfirm}
        title="Xác nhận hoàn tất kiểm tra hồ sơ"
        message="Hồ sơ sẽ được chuyển sang trạng thái ĐÃ DUYỆT ĐIỂM DỰ KIẾN (PROPOSED) với tổng điểm 24.00. Bạn có chắc chắn muốn hoàn tất?"
        confirmLabel="Hoàn tất"
        onConfirm={() => setShowCompleteConfirm(false)}
        onCancel={() => setShowCompleteConfirm(false)}
      />
    </div>
  );
};
