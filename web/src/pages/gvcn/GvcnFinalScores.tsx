import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';

export const GvcnFinalScores: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Bảng điểm Rèn luyện Chính thức (GVCN)</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Chỉ đọc bảng điểm sau khi Ban cán sự đã chốt điểm toàn bộ lớp
          </p>
        </div>
        <button className="btn btn-primary">
          📥 Xuất bảng điểm CSV
        </button>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <strong>Lớp:</strong> LOP-DEMO | <strong>Học kỳ:</strong> HK1-2026-2027
          </div>
          <StatusBadge status="FINALIZED" />
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e2e8f0', textAlign: 'left', color: '#64748b' }}>
              <th style={{ padding: '0.75rem 0.5rem' }}>STT</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Mã SV</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Họ và tên</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Điểm tự khai</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Điểm dự kiến</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Điểm chính thức</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Tình trạng</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '0.75rem 0.5rem' }}>1</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>SV001</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>Nguyễn Văn An</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>26.00</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>24.00</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 700, color: '#1e40af' }}>24.00</td>
              <td style={{ padding: '0.75rem 0.5rem' }}><StatusBadge status="FINALIZED" /></td>
            </tr>
            <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '0.75rem 0.5rem' }}>2</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>SV002</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>Trần Thị Bình</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>28.00</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>28.00</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 700, color: '#1e40af' }}>28.00</td>
              <td style={{ padding: '0.75rem 0.5rem' }}><StatusBadge status="FINALIZED" /></td>
            </tr>
            <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '0.75rem 0.5rem' }}>3</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>SV003</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>Lê Văn Cường</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>22.00</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>20.00</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 700, color: '#1e40af' }}>20.00</td>
              <td style={{ padding: '0.75rem 0.5rem' }}><StatusBadge status="FINALIZED" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
