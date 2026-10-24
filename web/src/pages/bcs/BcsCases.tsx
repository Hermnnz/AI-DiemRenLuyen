import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { StatusBadge } from '../../components/StatusBadge';
import { api } from '../../api/client';
import { BcsCaseListItem } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import { Search, Filter, RotateCcw } from 'lucide-react';

export const BcsCases: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStatus = searchParams.get('status') || 'ALL';
  const initialQ = searchParams.get('q') || '';
  const initialPage = parseInt(searchParams.get('page') || '1', 10);

  const [statusFilter, setStatusFilter] = useState<string>(initialStatus);
  const [searchQuery, setSearchQuery] = useState<string>(initialQ);
  const [page, setPage] = useState<number>(initialPage);
  const [pageSize] = useState<number>(10);

  const [cases, setCases] = useState<BcsCaseListItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    const loadCases = async () => {
      setLoading(true);
      try {
        const campaign = staffStore.getCampaign();
        const queryParams = new URLSearchParams();
        if (statusFilter && statusFilter !== 'ALL') queryParams.set('status', statusFilter);
        if (searchQuery.trim()) queryParams.set('q', searchQuery.trim());
        queryParams.set('page', page.toString());
        queryParams.set('page_size', pageSize.toString());

        const res = await api.get<{ total: number; page: number; page_size: number; items: BcsCaseListItem[] }>(
          `/bcs/campaigns/${campaign.id}/cases?${queryParams.toString()}`
        );
        if (mounted && res && res.items) {
          setCases(res.items);
          setTotal(res.total);
        }
      } catch {
        // Fallback to staffStore mock
        if (mounted) {
          const res = staffStore.getCases(statusFilter, searchQuery, page, pageSize);
          setCases(res.items);
          setTotal(res.total);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadCases();
    return () => {
      mounted = false;
    };
  }, [statusFilter, searchQuery, page, pageSize]);

  const handleStatusChange = (newStatus: string) => {
    setStatusFilter(newStatus);
    setPage(1);
    setSearchParams({ status: newStatus, q: searchQuery, page: '1' });
  };

  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    setPage(1);
    setSearchParams({ status: statusFilter, q: val, page: '1' });
  };

  const handleReset = () => {
    setStatusFilter('ALL');
    setSearchQuery('');
    setPage(1);
    setSearchParams({ status: 'ALL', q: '', page: '1' });
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
            Hàng chờ Hồ sơ Rèn luyện Lớp
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Kiểm tra minh chứng, chấm duyệt điểm và yêu cầu bổ sung theo từng sinh viên
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card" style={{ padding: '0.85rem 1.25rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Search box */}
          <div style={{ position: 'relative', minWidth: '260px', flex: 1 }}>
            <Search size={16} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Tìm theo Mã SV hoặc Họ tên..."
              style={{
                width: '100%',
                padding: '0.45rem 0.75rem 0.45rem 2rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '0.85rem',
              }}
            />
          </div>

          {/* Status selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={16} color="#64748b" />
            <select
              value={statusFilter}
              onChange={(e) => handleStatusChange(e.target.value)}
              style={{
                padding: '0.45rem 0.75rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '0.85rem',
                fontWeight: 500,
                backgroundColor: '#ffffff',
              }}
            >
              <option value="ALL">Tất cả trạng thái</option>
              <option value="BCS_REVIEW">Chờ BCS kiểm tra (BCS_REVIEW)</option>
              <option value="NEEDS_INFO">Chờ bổ sung thông tin (NEEDS_INFO)</option>
              <option value="NEEDS_PROOF">Chờ bổ sung minh chứng (NEEDS_PROOF)</option>
              <option value="PROPOSED">Đã duyệt dự kiến (PROPOSED)</option>
              <option value="PUBLISHED">Đã công bố (PUBLISHED)</option>
              <option value="APPEALED">Đang khiếu nại (APPEALED)</option>
              <option value="FINALIZED">Đã chốt chính thức (FINALIZED)</option>
            </select>

            {(statusFilter !== 'ALL' || searchQuery.trim() !== '') && (
              <button
                onClick={handleReset}
                className="btn btn-secondary"
                title="Đặt lại bộ lọc"
                style={{ padding: '0.45rem 0.65rem' }}
              >
                <RotateCcw size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Cases Table Card */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left', color: '#475569' }}>
                <th style={{ padding: '0.75rem 1rem' }}>Mã SV</th>
                <th style={{ padding: '0.75rem 1rem' }}>Họ và tên</th>
                <th style={{ padding: '0.75rem 1rem' }}>Trạng thái</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Điểm tự khai</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Điểm duyệt BCS</th>
                <th style={{ padding: '0.75rem 1rem' }}>Lượt bổ sung</th>
                <th style={{ padding: '0.75rem 1rem' }}>Cập nhật</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                    Đang tải danh sách hồ sơ...
                  </td>
                </tr>
              ) : cases.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: '2.5rem', textAlign: 'center', color: '#64748b' }}>
                    <div>Không tìm thấy hồ sơ nào phù hợp với điều kiện tìm kiếm.</div>
                    <button onClick={handleReset} className="btn btn-secondary" style={{ marginTop: '0.75rem', fontSize: '0.8rem' }}>
                      Xóa bộ lọc
                    </button>
                  </td>
                </tr>
              ) : (
                cases.map((c) => {
                  const isPendingReview = c.status === 'BCS_REVIEW';
                  return (
                    <tr
                      key={c.id}
                      style={{
                        borderBottom: '1px solid #f1f5f9',
                        backgroundColor: isPendingReview ? '#f0fdf4' : 'transparent',
                        transition: 'background-color 0.15s',
                      }}
                    >
                      <td style={{ padding: '0.75rem 1rem', fontWeight: 600, color: '#0f172a' }}>
                        {c.student_code}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', fontWeight: 500 }}>
                        {c.student_name}
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <StatusBadge status={c.status} />
                      </td>
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 500 }}>
                        {c.claimed_total || '—'}
                      </td>
                      <td
                        style={{
                          padding: '0.75rem 1rem',
                          textAlign: 'right',
                          fontWeight: 700,
                          color: c.proposed_total ? '#1e40af' : '#94a3b8',
                        }}
                      >
                        {c.proposed_total || '—'}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', fontSize: '0.8rem', color: '#475569' }}>
                        INFO: {c.info_round}/2 · PROOF: {c.proof_round}/2
                      </td>
                      <td style={{ padding: '0.75rem 1rem', fontSize: '0.8rem', color: '#64748b' }}>
                        {new Date(c.updated_at).toLocaleDateString('vi-VN')}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                        <Link
                          to={`/bcs/cases/${c.id}`}
                          className={isPendingReview ? 'btn btn-primary' : 'btn btn-secondary'}
                          style={{ padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
                        >
                          {isPendingReview ? 'Kiểm tra →' : 'Xem chi tiết'}
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {total > 0 && (
          <div
            style={{
              padding: '0.75rem 1.25rem',
              borderTop: '1px solid #e2e8f0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: '#f8fafc',
              fontSize: '0.825rem',
              color: '#64748b',
            }}
          >
            <div>
              Hiển thị {cases.length} trên tổng số {total} hồ sơ
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="btn btn-secondary"
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
              >
                Trước
              </button>
              <span>
                Trang {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="btn btn-secondary"
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
              >
                Sau
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
