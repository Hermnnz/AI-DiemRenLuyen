import React, { useState, useEffect } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { MeetingRecordModal } from '../../components/staff/MeetingRecordModal';
import { api } from '../../api/client';
import { ScoreboardResponse, ScoreboardItem, Meeting, MeetingKind, Campaign } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import { Calendar, CheckCircle2, AlertCircle, AlertTriangle, Search, Send, RotateCcw } from 'lucide-react';

const isDemoMode = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';

const emptyScoreboard: ScoreboardResponse = {
  campaign_id: '',
  can_publish: false,
  meetings: [],
  items: [],
};

export const BcsScores: React.FC = () => {
  const [scoreboard, setScoreboard] = useState<ScoreboardResponse>(
    isDemoMode ? staffStore.getScoreboard() : emptyScoreboard
  );
  const [campaign, setCampaign] = useState<Campaign | null>(
    isDemoMode ? staffStore.getCampaign() : null
  );
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Search filter
  const [searchQuery, setSearchQuery] = useState('');

  // Meeting modal state
  const [selectedMeetingKind, setSelectedMeetingKind] = useState<MeetingKind>('BCS');
  const [showMeetingModal, setShowMeetingModal] = useState(false);

  // Publish confirm modal state
  const [showPublishConfirm, setShowPublishConfirm] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const loadScoreboard = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const camp = await api.get<Campaign>('/bcs/campaigns/active');
      setCampaign(camp);
      const data = await api.get<ScoreboardResponse>(`/bcs/campaigns/${camp.id}/scoreboard`);
      if (data) setScoreboard(data);
    } catch (err: unknown) {
      if (isDemoMode) {
        setScoreboard(staffStore.getScoreboard());
        setCampaign(staffStore.getCampaign());
      } else {
        const errObj = err as { error?: { message?: string }; message?: string };
        const msg = errObj?.error?.message || errObj?.message || 'Không thể tải bảng điểm từ máy chủ.';
        setErrorMsg(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScoreboard();
  }, []);

  const bcsMeeting = scoreboard.meetings.find((m) => m.kind === 'BCS');
  const classMeeting = scoreboard.meetings.find((m) => m.kind === 'CLASS');

  const hasBcsMeeting = !!bcsMeeting;
  const hasClassMeeting = !!classMeeting;

  const totalCases = scoreboard.items.length;
  const unproposedCases = scoreboard.items.filter(
    (item) => !['PROPOSED', 'PUBLISHED', 'ACCEPTED', 'ACCEPTED_AUTO', 'APPEALED', 'RESOLVED', 'FINALIZED', 'CLOSED_INCOMPLETE', 'CLOSED_NO_SUBMIT'].includes(item.status)
  ).length;

  const isAllCasesReady = unproposedCases === 0;
  const isAlreadyPublishedOrFinalized = campaign ? ['PUBLISHED', 'FINALIZED'].includes(campaign.status) : false;
  const canPublish = scoreboard.can_publish && !isAlreadyPublishedOrFinalized;

  const handleOpenMeetingModal = (kind: MeetingKind) => {
    setSelectedMeetingKind(kind);
    setShowMeetingModal(true);
  };

  const handleRecordMeeting = async (kind: MeetingKind, heldAt: string, note: string | null) => {
    if (!campaign) return;
    try {
      if (isDemoMode) {
        staffStore.recordMeeting(kind, heldAt, note);
      } else {
        await api.post(`/bcs/campaigns/${campaign.id}/meetings`, {
          kind,
          held_at: heldAt,
          note,
        });
      }
      setSuccessMsg(`Đã ghi nhận biên bản cuộc họp: ${kind === 'BCS' ? 'Họp Ban cán sự' : 'Họp toàn thể Lớp'}.`);
      await loadScoreboard();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message || (err as { message?: string })?.message || 'Lỗi khi ghi biên bản họp.';
      setErrorMsg(msg);
      throw err;
    }
  };

  const handlePublish = async () => {
    if (!campaign) return;
    try {
      setPublishing(true);
      setErrorMsg(null);
      if (isDemoMode) {
        staffStore.publishScores();
      } else {
        await api.post(`/bcs/campaigns/${campaign.id}/publish`, {
          expected_campaign_status: campaign.status,
        });
      }
      setShowPublishConfirm(false);
      setSuccessMsg('Đã công bố điểm rèn luyện dự kiến đến toàn bộ sinh viên trong lớp thành công!');
      await loadScoreboard();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message || (err as { message?: string })?.message || 'Lỗi khi công bố điểm rèn luyện.';
      setErrorMsg(msg);
    } finally {
      setPublishing(false);
    }
  };

  // Filtered scoreboard items
  const filteredItems = scoreboard.items.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return item.student_code.toLowerCase().includes(q) || item.student_name.toLowerCase().includes(q);
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* 1. Header & Actions */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
              Bảng điểm Dự kiến Cả lớp & Công bố
            </h2>
            <StatusBadge status={campaign ? campaign.status : 'DRAFT'} />
          </div>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Đợt: {campaign ? campaign.title : '—'} | Lớp: LOP-DEMO | Học kỳ: {campaign ? campaign.term : '—'}
          </p>
        </div>

        <div>
          {isAlreadyPublishedOrFinalized ? (
            <div className="badge badge-success" style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}>
              <CheckCircle2 size={16} /> Đã công bố điểm dự kiến
            </div>
          ) : (
            <button
              type="button"
              data-testid="publish-scores-btn"
              disabled={!canPublish || publishing}
              onClick={() => setShowPublishConfirm(true)}
              className="btn btn-primary"
              style={{ fontSize: '0.875rem' }}
            >
              <Send size={16} /> {publishing ? 'Đang công bố...' : 'Công bố điểm dự kiến'}
            </button>
          )}
        </div>
      </div>

      {/* Alerts */}
      {errorMsg && (
        <div
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            color: '#991b1b',
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div
          style={{
            backgroundColor: '#ecfdf5',
            border: '1px solid #a7f3d0',
            color: '#065f46',
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <CheckCircle2 size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Readiness Check Banner (Gate Check) */}
      {!isAlreadyPublishedOrFinalized && (
        <div
          className="card"
          style={{
            backgroundColor: canPublish ? '#eff6ff' : '#fffbeb',
            border: canPublish ? '1px solid #bfdbfe' : '1px solid #fde68a',
            padding: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            {canPublish ? (
              <CheckCircle2 size={20} color="#1e40af" />
            ) : (
              <AlertCircle size={20} color="#d97706" />
            )}
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: canPublish ? '#1e40af' : '#92400e' }}>
              {canPublish
                ? 'Đủ điều kiện công bố: Tất cả hồ sơ đã hoàn tất kiểm tra và đã ghi nhận đủ 2 cuộc họp.'
                : 'Chưa đủ điều kiện công bố điểm dự kiến:'}
            </h3>
          </div>

          {!canPublish && (
            <ul style={{ fontSize: '0.825rem', color: '#78350f', paddingLeft: '1.5rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {!isAllCasesReady && (
                <li>Còn <strong>{unproposedCases}</strong> hồ sơ chưa hoàn tất kiểm tra sang trạng thái PROPOSED.</li>
              )}
              {!hasBcsMeeting && <li>Chưa ghi nhận biên bản <strong>Họp Ban cán sự</strong>.</li>}
              {!hasClassMeeting && <li>Chưa ghi nhận biên bản <strong>Họp toàn thể Lớp</strong>.</li>}
            </ul>
          )}
        </div>
      )}

      {/* 2. Biên bản Họp Bình xét */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
            Biên bản Họp Bình xét Điểm Rèn luyện (Bắt buộc 2 cuộc họp)
          </h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {/* Cuộc họp 1: Họp BCS */}
          <div
            style={{
              border: hasBcsMeeting ? '1px solid #a7f3d0' : '1px dashed #cbd5e1',
              borderRadius: '6px',
              padding: '1rem',
              backgroundColor: hasBcsMeeting ? '#f0fdf4' : '#f8fafc',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '0.5rem',
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a' }}>
                  1. Họp Ban cán sự lớp
                </span>
                {hasBcsMeeting ? (
                  <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                    ✓ Đã ghi nhận
                  </span>
                ) : (
                  <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                    Chưa ghi nhận
                  </span>
                )}
              </div>

              {hasBcsMeeting ? (
                <div style={{ marginTop: '0.5rem', fontSize: '0.825rem', color: '#334155' }}>
                  <div>
                    <strong>Thời gian:</strong> {new Date(bcsMeeting.held_at).toLocaleString('vi-VN')}
                  </div>
                  {bcsMeeting.note && (
                    <div style={{ marginTop: '0.25rem', fontStyle: 'italic', color: '#475569' }}>
                      "{bcsMeeting.note}"
                    </div>
                  )}
                </div>
              ) : (
                <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.4rem' }}>
                  Ban cán sự họp kiểm tra rà soát 100% minh chứng và hồ sơ của lớp trước khi đưa ra sinh hoạt lớp.
                </p>
              )}
            </div>

            <button
              type="button"
              data-testid="record-bcs-meeting"
              onClick={() => handleOpenMeetingModal('BCS')}
              className="btn btn-secondary"
              style={{ padding: '0.3rem 0.6rem', fontSize: '0.775rem', alignSelf: 'flex-start', marginTop: '0.5rem' }}
            >
              <Calendar size={13} /> {hasBcsMeeting ? 'Chỉnh sửa biên bản' : 'Ghi nhận cuộc họp'}
            </button>
          </div>

          {/* Cuộc họp 2: Họp Lớp */}
          <div
            style={{
              border: hasClassMeeting ? '1px solid #a7f3d0' : '1px dashed #cbd5e1',
              borderRadius: '6px',
              padding: '1rem',
              backgroundColor: hasClassMeeting ? '#f0fdf4' : '#f8fafc',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '0.5rem',
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a' }}>
                  2. Họp toàn thể Lớp
                </span>
                {hasClassMeeting ? (
                  <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                    ✓ Đã ghi nhận
                  </span>
                ) : (
                  <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                    Chưa ghi nhận
                  </span>
                )}
              </div>

              {hasClassMeeting ? (
                <div style={{ marginTop: '0.5rem', fontSize: '0.825rem', color: '#334155' }}>
                  <div>
                    <strong>Thời gian:</strong> {new Date(classMeeting.held_at).toLocaleString('vi-VN')}
                  </div>
                  {classMeeting.note && (
                    <div style={{ marginTop: '0.25rem', fontStyle: 'italic', color: '#475569' }}>
                      "{classMeeting.note}"
                    </div>
                  )}
                </div>
              ) : (
                <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.4rem' }}>
                  Sinh hoạt lớp bình xét biểu quyết thông qua danh sách điểm rèn luyện dự kiến với sự tham gia của các thành viên.
                </p>
              )}
            </div>

            <button
              type="button"
              data-testid="record-class-meeting"
              onClick={() => handleOpenMeetingModal('CLASS')}
              className="btn btn-secondary"
              style={{ padding: '0.3rem 0.6rem', fontSize: '0.775rem', alignSelf: 'flex-start', marginTop: '0.5rem' }}
            >
              <Calendar size={13} /> {hasClassMeeting ? 'Chỉnh sửa biên bản' : 'Ghi nhận cuộc họp'}
            </button>
          </div>
        </div>
      </div>

      {/* 3. Bảng điểm dự kiến toàn lớp */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
              Danh sách Điểm Rèn luyện ({totalCases} sinh viên)
            </h3>
          </div>

          <div style={{ position: 'relative', minWidth: '240px' }}>
            <Search size={14} color="#94a3b8" style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm theo Mã SV hoặc Họ tên..."
              style={{
                width: '100%',
                padding: '0.35rem 0.6rem 0.35rem 1.8rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '0.8rem',
              }}
            />
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left', color: '#475569' }}>
                <th style={{ padding: '0.75rem 1rem' }}>Mã SV</th>
                <th style={{ padding: '0.75rem 1rem' }}>Họ và tên</th>
                <th style={{ padding: '0.75rem 1rem' }}>Trạng thái</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Điểm tự khai</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Điểm dự kiến BCS</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Điểm chính thức</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                    Đang tải dữ liệu bảng điểm...
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                    Không có sinh viên nào phù hợp với tìm kiếm.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => (
                  <tr key={item.case_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>{item.student_code}</td>
                    <td style={{ padding: '0.75rem 1rem' }}>{item.student_name}</td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <StatusBadge status={item.status} />
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                      {item.claimed_total || '—'}
                    </td>
                    <td
                      style={{
                        padding: '0.75rem 1rem',
                        textAlign: 'right',
                        fontWeight: 700,
                        color: item.proposed_total ? '#1e40af' : '#94a3b8',
                      }}
                    >
                      {item.proposed_total || '—'}
                    </td>
                    <td
                      style={{
                        padding: '0.75rem 1rem',
                        textAlign: 'right',
                        fontWeight: 700,
                        color: item.final_total ? '#059669' : '#94a3b8',
                      }}
                    >
                      {item.final_total || '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Meeting Record Modal */}
      <MeetingRecordModal
        isOpen={showMeetingModal}
        initialKind={selectedMeetingKind}
        existingMeeting={selectedMeetingKind === 'BCS' ? bcsMeeting : classMeeting}
        onClose={() => setShowMeetingModal(false)}
        onSubmit={handleRecordMeeting}
      />

      {/* Publish Confirm Dialog */}
      <ConfirmDialog
        isOpen={showPublishConfirm}
        title="Xác nhận công bố điểm rèn luyện dự kiến"
        message={`Điểm rèn luyện dự kiến của toàn bộ ${totalCases} sinh viên trong lớp sẽ được công bố công khai. Sinh viên sẽ có ${campaign?.appeal_period_hours || 48} giờ để bấm xác nhận hoặc gửi khiếu nại. Bạn có chắc chắn muốn công bố?`}
        confirmLabel="Công bố ngay"
        onConfirm={handlePublish}
        onCancel={() => setShowPublishConfirm(false)}
      />
    </div>
  );
};
