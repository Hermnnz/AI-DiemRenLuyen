import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { Deadline } from '../../components/Deadline';
import { api } from '../../api/client';
import { BcsCampaignOverview, BcsCaseListItem, Campaign } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import {
  fetchPriorityCase,
  formatPriorityTask,
  EMPTY_PRIORITY_MESSAGE,
  PARTIAL_ERROR_MESSAGE,
  PRIORITY_QUEUE_ROUTE,
} from './bcsDashboardLogic';
import { ClipboardList, AlertCircle, CheckCircle2, Clock, Scale, ChevronRight, RotateCcw } from 'lucide-react';

const isDemoMode = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';

export const BcsDashboard: React.FC = () => {
  const [overview, setOverview] = useState<BcsCampaignOverview | null>(isDemoMode ? staffStore.getOverview() : null);
  const [campaign, setCampaign] = useState<Campaign | null>(isDemoMode ? staffStore.getCampaign() : null);
  const [priorityCase, setPriorityCase] = useState<BcsCaseListItem | null>(
    isDemoMode ? staffStore.getCases('BCS_REVIEW', '', 1, 1).items[0] || null : null
  );
  const [priorityLoading, setPriorityLoading] = useState<boolean>(false);
  const [priorityError, setPriorityError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showOpenConfirm, setShowOpenConfirm] = useState(false);
  const [opening, setOpening] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    setPriorityError(null);
    try {
      if (isDemoMode) {
        const camp = staffStore.getCampaign();
        const ov = staffStore.getOverview();
        setCampaign(camp);
        setOverview(ov);
        const pRes = await fetchPriorityCase(camp.id, true);
        setPriorityCase(pRes.priorityCase);
        setPriorityError(pRes.error);
        setPriorityLoading(false);
        setLoading(false);
        return;
      }

      const camp = await api.get<Campaign>('/bcs/campaigns/active');
      const ov = await api.get<BcsCampaignOverview>(`/bcs/campaigns/${camp.id}/overview`);
      setCampaign(camp);
      setOverview(ov);
      setLoading(false);

      if (ov.bcs_review_count > 0) {
        setPriorityLoading(true);
        const pRes = await fetchPriorityCase(camp.id, false);
        setPriorityCase(pRes.priorityCase);
        setPriorityError(pRes.error);
        setPriorityLoading(false);
      } else {
        setPriorityCase(null);
        setPriorityError(null);
        setPriorityLoading(false);
      }
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string }; message?: string };
      const msg = errObj?.error?.message || errObj?.message || 'Không thể kết nối đến máy chủ.';
      setError(msg);
      setCampaign(null);
      setOverview(null);
      setPriorityCase(null);
      setPriorityLoading(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenCampaign = async () => {
    if (!campaign || opening) return;
    setOpening(true);
    setActionError(null);
    try {
      const result = isDemoMode
        ? staffStore.openCampaign()
        : await api.post<{ id: string; status: string }>(`/bcs/campaigns/${campaign.id}/open`);
      setShowOpenConfirm(false);
      await loadData();
      setActionMessage(result.status === 'SCHEDULED'
        ? 'Đã lên lịch mở đợt. Hệ thống sẽ mở khi tới thời gian đã đặt.'
        : 'Đã mở đợt. Sinh viên trong lớp có thể bắt đầu tự chấm.');
    } catch (err: unknown) {
      const errorObj = err as { error?: { message?: string }; message?: string };
      setActionError(errorObj?.error?.message || errorObj?.message || 'Không mở được đợt. Hãy tải lại và thử lại.');
      setShowOpenConfirm(false);
    } finally {
      setOpening(false);
    }
  };

  if (loading && !campaign && !overview) {
    return (
      <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
        <p style={{ color: '#64748b' }}>Đang tải dữ liệu đợt đánh giá...</p>
      </div>
    );
  }

  if (error || !campaign || !overview) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
        <AlertCircle size={40} color="#dc2626" style={{ margin: '0 auto 1rem' }} />
        <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#0f172a', marginBottom: '0.5rem' }}>
          Lỗi tải dữ liệu bảng điều khiển
        </h3>
        <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
          {error || 'Không tìm thấy thông tin đợt đánh giá cho lớp của bạn.'}
        </p>
        <button className="btn btn-primary" onClick={loadData} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
          <RotateCcw size={16} /> Thử lại
        </button>
      </div>
    );
  }

  const totalNeedsReview = overview.bcs_review_count ?? 0;
  const totalSupplement = (overview.needs_info_count ?? 0) + (overview.needs_proof_count ?? 0);
  const totalProposed = overview.proposed_count ?? 0;
  const totalAppeals = overview.open_appeals_count ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {actionError && <div role="alert" className="card" style={{ color: '#991b1b', borderColor: '#fecaca' }}>{actionError}</div>}
      {actionMessage && <div role="status" className="card" style={{ color: '#065f46', borderColor: '#a7f3d0' }}>{actionMessage}</div>}
      {/* 1. Header & Campaign Status */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
              Bảng Điều Khiển Ban Cán Sự Lớp
            </h2>
            <StatusBadge status={campaign.status} />
          </div>
          <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Đợt: <span style={{ fontWeight: 600, color: '#1e293b' }}>{campaign.title}</span> | Học kỳ: {campaign.term}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {(campaign.status === 'DRAFT' || (campaign.status === 'SCHEDULED' && new Date(campaign.open_at).getTime() <= Date.now())) && (
            <button type="button" className="btn btn-primary" disabled={opening} onClick={() => setShowOpenConfirm(true)}>
              {opening ? 'Đang mở đợt...' : campaign.status === 'DRAFT' ? 'Lên lịch / Mở đợt' : 'Mở đợt ngay'}
            </button>
          )}
          <div style={{ textAlign: 'right', fontSize: '0.85rem' }}>
            <div style={{ color: '#64748b' }}>Hạn sinh viên nộp:</div>
            <Deadline isoString={campaign.submission_deadline_at} label="Đóng nộp" />
          </div>
        </div>
      </div>

      <ConfirmDialog
        isOpen={showOpenConfirm}
        title="Xác nhận mở đợt đánh giá"
        message="BCS sẽ mở đợt cho lớp mình. Nếu thời gian mở chưa tới, đợt được lên lịch và hệ thống tự mở đúng hạn. Admin vẫn có thể cập nhật cấu hình sau đó."
        confirmLabel="Xác nhận mở đợt"
        isLoading={opening}
        onConfirm={handleOpenCampaign}
        onCancel={() => setShowOpenConfirm(false)}
      />

      {/* 2. Stat Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(220px, 100%), 1fr))',
          gap: '1rem',
        }}
      >
        {/* Card 1: Chờ kiểm tra */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.825rem', fontWeight: 600, color: '#64748b' }}>Hồ sơ chờ kiểm tra</span>
            <div style={{ padding: '0.35rem', backgroundColor: '#eff6ff', borderRadius: '6px' }}>
              <ClipboardList size={18} color="#1e40af" />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: '#1e40af', margin: '0.5rem 0' }}>
            {loading ? '...' : totalNeedsReview}
          </div>
          <Link
            to="/bcs/cases?status=BCS_REVIEW"
            style={{ fontSize: '0.825rem', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
          >
            Vào hàng chờ kiểm tra <ChevronRight size={14} />
          </Link>
        </div>

        {/* Card 2: Chờ sinh viên bổ sung */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.825rem', fontWeight: 600, color: '#64748b' }}>Chờ sinh viên bổ sung</span>
            <div style={{ padding: '0.35rem', backgroundColor: '#fffbeb', borderRadius: '6px' }}>
              <Clock size={18} color="#d97706" />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: '#d97706', margin: '0.5rem 0' }}>
            {loading ? '...' : totalSupplement}
          </div>
          <Link
            to="/bcs/cases?status=NEEDS_INFO"
            style={{ fontSize: '0.825rem', fontWeight: 500, color: '#b45309', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
          >
            Xem danh sách bổ sung <ChevronRight size={14} />
          </Link>
        </div>

        {/* Card 3: Đã duyệt điểm dự kiến */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.825rem', fontWeight: 600, color: '#64748b' }}>Đã có điểm dự kiến</span>
            <div style={{ padding: '0.35rem', backgroundColor: '#ecfdf5', borderRadius: '6px' }}>
              <CheckCircle2 size={18} color="#059669" />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: '#059669', margin: '0.5rem 0' }}>
            {loading ? '...' : totalProposed}
          </div>
          <Link
            to="/bcs/scores"
            style={{ fontSize: '0.825rem', fontWeight: 500, color: '#047857', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
          >
            Bảng điểm lớp & công bố <ChevronRight size={14} />
          </Link>
        </div>

        {/* Card 4: Khiếu nại cần xử lý */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.825rem', fontWeight: 600, color: '#64748b' }}>Khiếu nại cần xử lý</span>
            <div style={{ padding: '0.35rem', backgroundColor: '#fef2f2', borderRadius: '6px' }}>
              <Scale size={18} color="#dc2626" />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: totalAppeals > 0 ? '#dc2626' : '#64748b', margin: '0.5rem 0' }}>
            {loading ? '...' : totalAppeals}
          </div>
          <Link
            to="/bcs/appeals"
            style={{ fontSize: '0.825rem', fontWeight: 500, color: '#b91c1c', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
          >
            Xử lý khiếu nại & chốt <ChevronRight size={14} />
          </Link>
        </div>
      </div>

      {/* 3. Urgent Action Tasks / Danh sách việc cần làm ngay */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <AlertCircle size={20} color="#1e40af" />
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#0f172a' }}>
            Danh sách việc cần ưu tiên xử lý
          </h3>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {/* 1. Trạng thái tải hồ sơ ưu tiên */}
          {priorityLoading ? (
            <div
              data-testid="priority-loading"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.85rem 1rem',
                backgroundColor: '#f8fafc',
                borderRadius: '6px',
                borderLeft: '4px solid #94a3b8',
                color: '#64748b',
                fontSize: '0.9rem',
              }}
            >
              <RotateCcw size={16} className="animate-spin" />
              <span>Đang tải công việc ưu tiên…</span>
            </div>
          ) : priorityError ? (
            /* 2. Trạng thái lỗi một phần khi gọi API priority case */
            <div
              data-testid="priority-error"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.75rem',
                padding: '0.85rem 1rem',
                backgroundColor: '#fffbeb',
                borderRadius: '6px',
                borderLeft: '4px solid #f59e0b',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#92400e' }}>
                  {PARTIAL_ERROR_MESSAGE}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#b45309' }}>
                  Có {totalNeedsReview} hồ sơ chờ kiểm tra trên hệ thống.
                </div>
              </div>
              <Link
                to={PRIORITY_QUEUE_ROUTE}
                className="btn btn-secondary"
                style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', minHeight: '44px', display: 'inline-flex', alignItems: 'center' }}
              >
                Mở hàng chờ →
              </Link>
            </div>
          ) : priorityCase ? (
            /* 3. Trạng thái thành công: hiển thị đúng dữ liệu động */
            <div
              data-testid="priority-case-card"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.75rem',
                padding: '0.85rem 1rem',
                backgroundColor: '#f8fafc',
                borderRadius: '6px',
                borderLeft: '4px solid #1e40af',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                  {formatPriorityTask(priorityCase).title}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  {formatPriorityTask(priorityCase).subtitle}
                </div>
              </div>
              <Link
                to={formatPriorityTask(priorityCase).route}
                className="btn btn-primary"
                style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', minHeight: '44px', display: 'inline-flex', alignItems: 'center' }}
              >
                Kiểm tra ngay →
              </Link>
            </div>
          ) : totalNeedsReview === 0 ? (
            /* 4. Empty state rõ ràng khi không có hồ sơ cần kiểm tra ngay */
            <div
              data-testid="priority-empty"
              style={{
                padding: '0.75rem 1rem',
                backgroundColor: '#f8fafc',
                borderRadius: '6px',
                borderLeft: '4px solid #10b981',
                color: '#065f46',
                fontSize: '0.875rem',
              }}
            >
              {EMPTY_PRIORITY_MESSAGE}
            </div>
          ) : (
            /* 5. Fallback khi có hồ sơ nhưng priorityCase chưa nạp được */
            <div
              data-testid="priority-fallback-queue"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.75rem',
                padding: '0.85rem 1rem',
                backgroundColor: '#f8fafc',
                borderRadius: '6px',
                borderLeft: '4px solid #1e40af',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                  Có {totalNeedsReview} hồ sơ đang chờ Ban cán sự kiểm tra
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Vui lòng kiểm tra minh chứng và chấm duyệt điểm rèn luyện cho sinh viên
                </div>
              </div>
              <Link
                to={PRIORITY_QUEUE_ROUTE}
                className="btn btn-primary"
                style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', minHeight: '44px', display: 'inline-flex', alignItems: 'center' }}
              >
                Vào hàng chờ kiểm tra →
              </Link>
            </div>
          )}

          {/* Khiếu nại cần xử lý */}
          {totalAppeals > 0 && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.75rem 1rem',
                backgroundColor: '#fef2f2',
                borderRadius: '6px',
                borderLeft: '4px solid #dc2626',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#991b1b' }}>
                  Có {totalAppeals} khiếu nại điểm rèn luyện đang chờ giải quyết
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Sinh viên đã gửi đơn khiếu nại đối với kết quả dự kiến, Ban cán sự cần rà soát và phản hồi.
                </div>
              </div>
              <Link
                to="/bcs/appeals"
                className="btn btn-danger"
                style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
              >
                Giải quyết khiếu nại →
              </Link>
            </div>
          )}

          {totalNeedsReview === 0 && totalAppeals === 0 && (
            <div style={{ textAlign: 'center', padding: '1rem 0', color: '#64748b', fontSize: '0.875rem' }}>
              🎉 Bạn đã xử lý xong toàn bộ công việc khẩn cấp. Bạn có thể theo dõi bảng điểm lớp hoặc kiểm tra các hồ sơ khác.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
