import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Link } from 'react-router-dom';

export const BcsCases: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Hàng chờ Hồ sơ Rèn luyện</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Danh sách sinh viên trong lớp cần BCS kiểm tra minh chứng và duyệt điểm</p>
        </div>
      </div>

      <div className="card">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e2e8f0', textAlign: 'left', color: '#64748b' }}>
              <th style={{ padding: '0.75rem 0.5rem' }}>Mã SV</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Họ và tên</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Trạng thái</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Điểm tự khai</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Điểm duyệt</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Lượt bổ sung</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>SV001</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>Nguyễn Văn An</td>
              <td style={{ padding: '0.75rem 0.5rem' }}><StatusBadge status="BCS_REVIEW" /></td>
              <td style={{ padding: '0.75rem 0.5rem' }}>26.00</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>—</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>INFO: 1/2 | PROOF: 0/2</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>
                <Link to="/bcs/cases/55555555-5555-5555-5555-555555555001" className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>
                  Kiểm tra →
                </Link>
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>SV002</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>Trần Thị Bình</td>
              <td style={{ padding: '0.75rem 0.5rem' }}><StatusBadge status="PROPOSED" /></td>
              <td style={{ padding: '0.75rem 0.5rem' }}>28.00</td>
              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600, color: '#1e40af' }}>28.00</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>INFO: 0/2 | PROOF: 0/2</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>
                <Link to="/bcs/cases/55555555-5555-5555-5555-555555555002" className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>
                  Xem lại
                </Link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
