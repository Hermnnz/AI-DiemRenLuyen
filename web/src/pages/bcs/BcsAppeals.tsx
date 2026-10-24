import React, { useState, useEffect } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { SafeFilePreviewModal } from '../../components/staff/SafeFilePreviewModal';
import { api } from '../../api/client';
import { AppealDetailItem, AppealResolution, EvidenceFile } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import { Scale, CheckCircle2, AlertTriangle, Eye, ShieldCheck, Check, Lock } from 'lucide-react';

export const BcsAppeals: React.FC = () => {
  const [campaign, setCampaign] = useState(staffStore.getCampaign());
  const [appeals, setAppeals] = useState<AppealDetailItem[]>(staffStore.getAppeals());
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<'ALL' | 'OPEN' | 'RESOLVED'>('ALL');

  // Form states per appeal ID
  const [resolutions, setResolutions] = useState<Record<string, AppealResolution>>({});
  const [newScores, setNewScores] = useState<Record<string, string>>({});
  const [bcsReasons, setBcsReasons] = useState<Record<string, string>>({});
  const [submittingAppealId, setSubmittingAppealId] = useState<string | null>(null);

  // File preview
  const [previewFile, setPreviewFile] = useState<EvidenceFile | null>(null);

  // Finalize confirm modal
  const [showFinalizeConfirm, setShowFinalizeConfirm] = useState(false);
  const [finalizing, setFinalizing] = useState(false);

  // Feedback alerts
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadAppeals = async () => {
    setLoading(true);
    try {
      const data = await api.get<AppealDetailItem[]>(`/bcs/campaigns/${campaign.id}/appeals`);
      if (data) setAppeals(data);
    } catch {
      setAppeals(staffStore.getAppeals());
      setCampaign(staffStore.getCampaign());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAppeals();
  }, []);

  const openAppeals = appeals.filter((a) => a.status === 'OPEN');
  const resolvedAppeals = appeals.filter((a) => a.status === 'RESOLVED');

  const filteredAppeals = appeals.filter((a) => {
    if (filter === 'OPEN') return a.status === 'OPEN';
    if (filter === 'RESOLVED') return a.status === 'RESOLVED';
    return true;
  });

  const isFinalized = campaign.status === 'FINALIZED';
  const canFinalize = openAppeals.length === 0 && !isFinalized;

  const handleResolve = async (appealId: string) => {
    setErrorMsg(null);
    setSuccessMsg(null);

    const resolution = resolutions[appealId] || 'KEEP';
    const newScore = newScores[appealId] || '';
    const reason = (bcsReasons[appealId] || '').trim();

    if (!reason) {
      setErrorMsg('Bắt buộc nhập lý do giải quyết khiếu nại để thông báo cho sinh viên.');
      return;
    }

    if (resolution === 'ADJUST') {
      const scoreNum = parseFloat(newScore);
      if (isNaN(scoreNum) || scoreNum < 0) {
        setErrorMsg('Vui lòng nhập điểm mới hợp lệ khi điều chỉnh.');
        return;
      }
    }

    try {
      setSubmittingAppealId(appealId);
      try {
        await api.post(`/bcs/appeals/${appealId}/resolve`, {
          resolution,
          new_score: resolution === 'ADJUST' ? newScore : null,
          reason,
        });
      } catch {
        staffStore.resolveAppeal(appealId, resolution, resolution === 'ADJUST' ? newScore : null, reason);
      }

      setSuccessMsg(`Đã giải quyết khiếu nại thành công (${resolution === 'KEEP' ? 'Giữ nguyên' : 'Điều chỉnh điểm'}).`);
      await loadAppeals();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string } })?.error?.message || 'Lỗi khi giải quyết khiếu nại.';
      setErrorMsg(msg);
    } finally {
      setSubmittingAppealId(null);
    }
  };

  const handleFinalize = async () => {
    try {
      setFinalizing(true);
      setErrorMsg(null);
      try {
        await api.post(`/bcs/campaigns/${campaign.id}/finalize`);
      } catch {
        staffStore.finalizeCampaign();
      }
      setShowFinalizeConfirm(false);
      setSuccessMsg('Đã chốt bảng điểm chính thức toàn bộ lớp thành công! Giáo viên chủ nhiệm đã có thể xem và tải CSV.');
      setCampaign(staffStore.getCampaign());
      await loadAppeals();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string } })?.error?.message || 'Lỗi khi chốt điểm đợt đánh giá.';
      setErrorMsg(msg);
    } finally {
      setFinalizing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* 1. Header & Finalize Action */}
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
              Danh sách Khiếu nại từ Sinh viên
            </h2>
            <StatusBadge status={campaign.status} />
          </div>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Xem xét minh chứng và lý do khiếu nại, quyết định Giữ nguyên hoặc Điều chỉnh điểm
          </p>
        </div>

        <div>
          {isFinalized ? (
            <div className="badge badge-success" style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}>
              <Lock size={15} /> Bảng điểm đã được chốt chính thức
            </div>
          ) : (
            <button
              type="button"
              disabled={!canFinalize || finalizing}
              onClick={() => setShowFinalizeConfirm(true)}
              className="btn btn-primary"
              style={{ fontSize: '0.875rem' }}
              title={openAppeals.length > 0 ? `Còn ${openAppeals.length} khiếu nại chưa giải quyết` : 'Chốt điểm cả lớp'}
            >
              <Lock size={15} /> {finalizing ? 'Đang chốt...' : 'Chốt điểm cả lớp'}
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

      {/* 2. Filter Navigation Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
        <button
          onClick={() => setFilter('ALL')}
          style={{
            padding: '0.4rem 0.75rem',
            borderRadius: '6px',
            border: 'none',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            backgroundColor: filter === 'ALL' ? '#eff6ff' : 'transparent',
            color: filter === 'ALL' ? '#1e40af' : '#64748b',
          }}
        >
          Tất cả khiếu nại ({appeals.length})
        </button>
        <button
          onClick={() => setFilter('OPEN')}
          style={{
            padding: '0.4rem 0.75rem',
            borderRadius: '6px',
            border: 'none',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            backgroundColor: filter === 'OPEN' ? '#fef2f2' : 'transparent',
            color: filter === 'OPEN' ? '#dc2626' : '#64748b',
          }}
        >
          Cần xử lý ({openAppeals.length})
        </button>
        <button
          onClick={() => setFilter('RESOLVED')}
          style={{
            padding: '0.4rem 0.75rem',
            borderRadius: '6px',
            border: 'none',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            backgroundColor: filter === 'RESOLVED' ? '#ecfdf5' : 'transparent',
            color: filter === 'RESOLVED' ? '#059669' : '#64748b',
          }}
        >
          Đã giải quyết ({resolvedAppeals.length})
        </button>
      </div>

      {/* 3. Appeals List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {loading ? (
          <div className="card" style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            Đang tải danh sách khiếu nại...
          </div>
        ) : filteredAppeals.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '2.5rem', color: '#64748b' }}>
            <Scale size={32} color="#94a3b8" style={{ margin: '0 auto 0.5rem' }} />
            <div>Không có khiếu nại nào trong mục này.</div>
          </div>
        ) : (
          filteredAppeals.map((appeal) => {
            const currentRes = resolutions[appeal.id] || 'KEEP';
            const currentNewScore = newScores[appeal.id] || '';
            const currentBcsReason = bcsReasons[appeal.id] || '';
            const isSubmitting = submittingAppealId === appeal.id;
            const isOpen = appeal.status === 'OPEN';

            return (
              <div
                key={appeal.id}
                className="card"
                style={{
                  borderLeft: isOpen ? '4px solid #dc2626' : '4px solid #059669',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '1rem',
                }}
              >
                {/* Header info */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontWeight: 700, fontSize: '1rem', color: '#0f172a' }}>
                        {appeal.student_code} · {appeal.student_name}
                      </span>
                      <span className={`badge ${isOpen ? 'badge-danger' : 'badge-success'}`}>
                        {isOpen ? 'Chờ BCS giải quyết' : 'Đã giải quyết'}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.825rem', color: '#64748b', marginTop: '0.2rem' }}>
                      Tiêu chí khiếu nại: <strong>[{appeal.criterion_code}] {appeal.criterion_title}</strong>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right', fontSize: '0.825rem', color: '#475569' }}>
                    <div>Sinh viên tự khai: <strong style={{ color: '#0f172a' }}>{appeal.self_score}</strong> đ</div>
                    <div>BCS đã chấm dự kiến: <strong style={{ color: '#1e40af' }}>{appeal.proposed_score}</strong> đ</div>
                  </div>
                </div>

                {/* Lý do sinh viên khiếu nại */}
                <div style={{ backgroundColor: '#f8fafc', padding: '0.75rem', borderRadius: '6px', fontSize: '0.85rem' }}>
                  <div style={{ fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                    Ý kiến / Lý do khiếu nại của sinh viên:
                  </div>
                  <div style={{ color: '#1e293b', fontStyle: 'italic' }}>
                    "{appeal.student_reason}"
                  </div>
                </div>

                {/* Evidence files */}
                {appeal.evidence && appeal.evidence.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>Minh chứng kèm theo:</span>
                    {appeal.evidence.map((ev) => (
                      <button
                        key={ev.id}
                        type="button"
                        onClick={() => setPreviewFile(ev)}
                        className="btn btn-secondary"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        <Eye size={12} /> {ev.original_name}
                      </button>
                    ))}
                  </div>
                )}

                {/* If RESOLVED: Display resolution result */}
                {!isOpen && (
                  <div
                    style={{
                      backgroundColor: '#ecfdf5',
                      border: '1px solid #a7f3d0',
                      borderRadius: '6px',
                      padding: '0.75rem',
                      fontSize: '0.85rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.25rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, color: '#065f46' }}>
                      <Check size={16} /> Kết luận của BCS: {appeal.resolution === 'KEEP' ? 'Giữ nguyên điểm' : `Điều chỉnh điểm thành ${appeal.new_score} đ`}
                    </div>
                    {appeal.bcs_reason && (
                      <div style={{ color: '#047857', fontSize: '0.8rem' }}>
                        Lý do giải quyết: {appeal.bcs_reason}
                      </div>
                    )}
                  </div>
                )}

                {/* If OPEN: Resolution Form */}
                {isOpen && (
                  <div
                    style={{
                      borderTop: '1px solid #f1f5f9',
                      paddingTop: '0.75rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.75rem',
                    }}
                  >
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#1e40af' }}>
                      Quyết định của Ban cán sự:
                    </div>

                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                        <input
                          type="radio"
                          name={`res-${appeal.id}`}
                          value="KEEP"
                          checked={currentRes === 'KEEP'}
                          onChange={() => setResolutions({ ...resolutions, [appeal.id]: 'KEEP' })}
                        />
                        <span>Giữ nguyên điểm ({appeal.proposed_score} đ)</span>
                      </label>

                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                        <input
                          type="radio"
                          name={`res-${appeal.id}`}
                          value="ADJUST"
                          checked={currentRes === 'ADJUST'}
                          onChange={() => setResolutions({ ...resolutions, [appeal.id]: 'ADJUST' })}
                        />
                        <span>Điều chỉnh điểm</span>
                      </label>

                      {currentRes === 'ADJUST' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Điểm mới:</span>
                          <input
                            type="text"
                            value={currentNewScore}
                            onChange={(e) => setNewScores({ ...newScores, [appeal.id]: e.target.value })}
                            placeholder="vd: 8.00"
                            style={{ width: '80px', padding: '0.25rem 0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
                          />
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      <input
                        type="text"
                        value={currentBcsReason}
                        onChange={(e) => setBcsReasons({ ...bcsReasons, [appeal.id]: e.target.value })}
                        placeholder="Bắt buộc nhập lý do kết luận của Ban cán sự..."
                        style={{ flex: 1, minWidth: '240px', padding: '0.35rem 0.6rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.825rem' }}
                      />
                      <button
                        type="button"
                        disabled={isSubmitting || !currentBcsReason.trim()}
                        onClick={() => handleResolve(appeal.id)}
                        className="btn btn-primary"
                        style={{ padding: '0.35rem 0.75rem', fontSize: '0.825rem' }}
                      >
                        {isSubmitting ? 'Đang lưu...' : 'Lưu kết luận'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Safe File Preview Modal */}
      <SafeFilePreviewModal
        isOpen={previewFile !== null}
        file={previewFile}
        onClose={() => setPreviewFile(null)}
      />

      {/* Finalize Confirmation Modal */}
      <ConfirmDialog
        isOpen={showFinalizeConfirm}
        title="Xác nhận chốt điểm rèn luyện toàn bộ lớp"
        message="Toàn bộ khiếu nại đã được giải quyết. Sau khi chốt, điểm rèn luyện chính thức sẽ được đóng băng bất biến trong snapshot. Giáo viên chủ nhiệm sẽ nhận được bảng điểm để xuất CSV. Bạn có chắc chắn muốn chốt điểm?"
        confirmLabel="Chốt điểm ngay"
        onConfirm={handleFinalize}
        onCancel={() => setShowFinalizeConfirm(false)}
      />
    </div>
  );
};
