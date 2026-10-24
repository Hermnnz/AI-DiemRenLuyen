import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { api } from '../../api/client';
import { BcsCampaignOverview, Campaign } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import { ClipboardList, AlertCircle, CheckCircle2, Clock, Scale, ChevronRight } from 'lucide-react';

export const BcsDashboard: React.FC = () => {
  const [overview, setOverview] = useState<BcsCampaignOverview>(staffStore.getOverview());
  const [campaign, setCampaign] = useState<Campaign>(staffStore.getCampaign());
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      setLoading(true);
      try {
        const campaignData = await api.get<Campaign>(`/admin/campaigns/${campaign.id}`);
        if (mounted && campaignData) setCampaign(campaignData);
      } catch {
        // Fallback to mock store
        if (mounted) setCampaign(staffStore.getCampaign());
      }

      try {
        const overviewData = await api.get<BcsCampaignOverview>(`/bcs/campaigns/${campaign.id}/overview`);
        if (mounted && overviewData) setOverview(overviewData);
      } catch {
        // Fallback to mock store
        if (mounted) setOverview(staffStore.getOverview());
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadData();
    return () => {
      mounted = false;
    };
  }, [campaign.id]);

  const totalNeedsReview = overview.bcs_review_count;
  const totalSupplement = overview.needs_info_count + overview.needs_proof_count;
  const totalProposed = overview.proposed_count;
  const totalAppeals = overview.open_appeals_count;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
              Bảng Điều Khiển Ban Cán Sự Lớp
            </h2>
            <StatusBadge status={campaign.status} />
          </div>
          <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Đợt: <span style={{ fontWeight: 600, color: '#1e293b' }}>{campaign.title}</span> | Học kỳ: {campaign.term} | Lớp: LOP-DEMO
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ textAlign: 'right', fontSize: '0.85rem' }}>
            <div style={{ color: '#64748b' }}>Hạn sinh viên nộp:</div>
            <Deadline isoString={campaign.submission_deadline_at} label="Đóng nộp" />
          </div>
        </div>
      </div>

      {/* 2. Stat Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
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
          {totalNeedsReview > 0 && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.75rem 1rem',
                backgroundColor: '#f8fafc',
                borderRadius: '6px',
                borderLeft: '4px solid #1e40af',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                  Kiểm tra minh chứng hồ sơ SV001 · Nguyễn Văn An
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Hồ sơ đang ở trạng thái BCS_REVIEW, sinh viên đã hoàn thành bổ sung thông tin
                </div>
              </div>
              <Link
                to="/bcs/cases/55555555-5555-5555-5555-555555555001"
                className="btn btn-primary"
                style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
              >
                Kiểm tra ngay →
              </Link>
            </div>
          )}

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
                  Xử lý khiếu nại tiêu chí TC03 từ sinh viên SV001
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Sinh viên đề nghị xem xét lại minh chứng tình nguyện để nâng từ 6.00 lên 8.00 điểm
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
            <div style={{ textAlign: 'center', padding: '1.5rem 0', color: '#64748b', fontSize: '0.875rem' }}>
              🎉 Hiện tại không có hồ sơ khẩn cấp cần xử lý. Bạn có thể theo dõi bảng điểm lớp hoặc kiểm tra các hồ sơ khác.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
