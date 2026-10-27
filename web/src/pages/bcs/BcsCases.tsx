import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { StatusBadge } from '../../components/StatusBadge';
import { api } from '../../api/client';
import { BcsCaseListItem, Campaign } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import { Search, Filter, RotateCcw, AlertCircle } from 'lucide-react';

const isDemoMode = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';

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
  const [error, setError] = useState<string | null>(null);

  const loadCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const campaign = await api.get<Campaign>('/bcs/campaigns/active');
      const queryParams = new URLSearchParams();
      if (statusFilter && statusFilter !== 'ALL') queryParams.set('status', statusFilter);
      if (searchQuery.trim()) queryParams.set('q', searchQuery.trim());
      queryParams.set('page', page.toString());
      queryParams.set('page_size', pageSize.toString());

      const res = await api.get<{ total: number; page: number; page_size: number; items: BcsCaseListItem[] }>(
        `/bcs/campaigns/${campaign.id}/cases?${queryParams.toString()}`
      );
      if (res && res.items) {
        setCases(res.items);
        setTotal(res.total);
      }
    } catch (err: unknown) {
      if (isDemoMode) {
        const res = staffStore.getCases(statusFilter, searchQuery, page, pageSize);
        setCases(res.items);
        setTotal(res.total);
      } else {
        const errObj = err as { error?: { message?: string }; message?: string };
        const msg = errObj?.error?.message || errObj?.message || 'Không thể tải danh sách hồ sơ từ máy chủ.';
        setError(msg);
        setCases([]);
        setTotal(0);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
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
          <div style={{ position: 'relative', minWidth: 'min(260px, 100%)', flex: 1 }}>
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
                minHeight: '44px',
              }}
            />
          </div>

          {/* Status selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
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
                minHeight: '44px',
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
                style={{ padding: '0.45rem 0.65rem', minHeight: '44px' }}
              >
                <RotateCcw size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Cases Table & Mobile Cards Card */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {/* Desktop Table View */}
        <div className="bcs-cases-table-desktop">
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
              ) : error ? (
                <tr>
                  <td colSpan={8} style={{ padding: '2.5rem', textAlign: 'center', color: '#dc2626' }}>
                    <AlertCircle size={32} style={{ margin: '0 auto 0.5rem' }} />
                    <div style={{ fontWeight: 600 }}>{error}</div>
                    <button onClick={loadCases} className="btn btn-primary" style={{ marginTop: '0.75rem', fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem', minHeight: '44px' }}>
                      <RotateCcw size={14} /> Thử lại
                    </button>
                  </td>
                </tr>
              ) : cases.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: '2.5rem', textAlign: 'center', color: '#64748b' }}>
                    <div>Không tìm thấy hồ sơ nào phù hợp với điều kiện tìm kiếm.</div>
                    <button onClick={handleReset} className="btn btn-secondary" style={{ marginTop: '0.75rem', fontSize: '0.8rem', minHeight: '44px' }}>
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
                          style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', minHeight: '38px', display: 'inline-flex', alignItems: 'center' }}
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

        {/* Mobile Cards View (<= 768px) */}
        <div className="bcs-cases-cards-mobile">
          {loading ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
              Đang tải danh sách hồ sơ...
            </div>
          ) : error ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#dc2626' }}>
              <AlertCircle size={28} style={{ margin: '0 auto 0.5rem' }} />
              <div style={{ fontWeight: 600 }}>{error}</div>
              <button onClick={loadCases} className="btn btn-primary" style={{ marginTop: '0.75rem', fontSize: '0.85rem', minHeight: '44px' }}>
                <RotateCcw size={14} /> Thử lại
              </button>
            </div>
          ) : cases.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
              <div>Không tìm thấy hồ sơ nào phù hợp.</div>
              <button onClick={handleReset} className="btn btn-secondary" style={{ marginTop: '0.75rem', fontSize: '0.85rem', minHeight: '44px' }}>
                Xóa bộ lọc
              </button>
            </div>
          ) : (
            cases.map((c) => {
              const isPendingReview = c.status === 'BCS_REVIEW';
              return (
                <div
                  key={c.id}
                  className={`bcs-case-mobile-card ${isPendingReview ? 'pending-review' : ''}`}
                >
                  <div className="bcs-case-mobile-header">
                    <div>
                      <div className="bcs-case-mobile-student">{c.student_name}</div>
                      <div style={{ fontSize: '0.8rem', color: '#64748b' }}>MSSV: {c.student_code}</div>
                    </div>
                    <StatusBadge status={c.status} />
                  </div>
                  <div className="bcs-case-mobile-scores">
                    <div>
                      <span style={{ color: '#64748b' }}>Tự khai: </span>
                      <strong>{c.claimed_total || '—'}</strong>
                    </div>
                    <div>
                      <span style={{ color: '#64748b' }}>BCS duyệt: </span>
                      <strong style={{ color: c.proposed_total ? '#1e40af' : '#94a3b8' }}>
                        {c.proposed_total || '—'}
                      </strong>
                    </div>
                  </div>
                  <div className="bcs-case-mobile-meta">
                    <span>INFO: {c.info_round}/2 · PROOF: {c.proof_round}/2</span>
                    <span>{new Date(c.updated_at).toLocaleDateString('vi-VN')}</span>
                  </div>
                  <div className="bcs-case-mobile-action">
                    <Link
                      to={`/bcs/cases/${c.id}`}
                      className={isPendingReview ? 'btn btn-primary' : 'btn btn-secondary'}
                    >
                      {isPendingReview ? 'Kiểm tra ngay →' : 'Xem chi tiết'}
                    </Link>
                  </div>
                </div>
              );
            })
          )}
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
