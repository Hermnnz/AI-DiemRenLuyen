import React, { useState, useEffect, useRef } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { SafeFilePreviewModal } from '../../components/staff/SafeFilePreviewModal';
import { api } from '../../api/client';
import { AppealDetailItem, AppealResolution, EvidenceFile, Campaign, ScoreboardResponse, FinalHandoff } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import { EmptyPanel, LoadingPanel } from '../../components/UiStates';
import { CheckCircle2, AlertTriangle, Eye, ShieldCheck, Check, Lock } from 'lucide-react';

const isDemoMode = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';

export const BcsAppeals: React.FC = () => {
  const [campaign, setCampaign] = useState<Campaign | null>(isDemoMode ? staffStore.getCampaign() : null);
  const [appeals, setAppeals] = useState<AppealDetailItem[]>(isDemoMode ? staffStore.getAppeals() : []);
  const [scoreboard, setScoreboard] = useState<ScoreboardResponse | null>(isDemoMode ? staffStore.getScoreboard() : null);
  const [loading, setLoading] = useState(true);
  const [noCampaign, setNoCampaign] = useState(false);
  const [filter, setFilter] = useState<'ALL' | 'OPEN' | 'RESOLVED'>('ALL');

  // Form states per appeal ID
  const [resolutions, setResolutions] = useState<Record<string, AppealResolution>>({});
  const [newScores, setNewScores] = useState<Record<string, string>>({});
  const [bcsReasons, setBcsReasons] = useState<Record<string, string>>({});
  const [formErrors, setFormErrors] = useState<Record<string, { reason?: string; score?: string }>>({});
  const [submittingAppealId, setSubmittingAppealId] = useState<string | null>(null);
  const resolveLock = useRef<string | null>(null);

  // File preview
  const [previewFile, setPreviewFile] = useState<EvidenceFile | null>(null);

  // Finalize confirm modal
  const [showFinalizeConfirm, setShowFinalizeConfirm] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [handoff, setHandoff] = useState<FinalHandoff | null>(null);
  const [sendingHandoff, setSendingHandoff] = useState(false);
  const handoffLock = useRef(false);
  const finalizeLock = useRef(false);

  // Feedback alerts
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadAppeals = async () => {
    setLoading(true);
    setErrorMsg(null);
    setNoCampaign(false);
    try {
      const camp = await api.get<Campaign>('/bcs/campaigns/active');
      setCampaign(camp);
      if (camp.status === 'FINALIZED' && !isDemoMode) {
        setHandoff(await api.get<FinalHandoff>(`/bcs/campaigns/${camp.id}/handoff`));
      } else {
        setHandoff(null);
      }
      const [appealsResult, boardResult] = await Promise.allSettled([
        api.get<AppealDetailItem[]>(`/bcs/campaigns/${camp.id}/appeals`),
        api.get<ScoreboardResponse>(`/bcs/campaigns/${camp.id}/scoreboard`),
      ]);
      if (isDemoMode && (appealsResult.status === 'rejected' || boardResult.status === 'rejected')) {
        setAppeals(staffStore.getAppeals());
        setScoreboard(staffStore.getScoreboard());
      } else {
        setAppeals(appealsResult.status === 'fulfilled' ? appealsResult.value || [] : []);
        setScoreboard(boardResult.status === 'fulfilled' ? boardResult.value : null);
        if (appealsResult.status === 'rejected') {
          setErrorMsg('Chưa tải được danh sách khiếu nại. Hãy tải lại trang để tiếp tục xử lý.');
        } else if (boardResult.status === 'rejected') {
          setErrorMsg('Danh sách khiếu nại đã tải, nhưng chưa kiểm tra được điều kiện chốt điểm. Hãy tải lại trang trước khi chốt.');
        }
      }
    } catch (err: unknown) {
      if (isDemoMode) {
        setAppeals(staffStore.getAppeals());
        setCampaign(staffStore.getCampaign());
        setScoreboard(staffStore.getScoreboard());
      } else {
        setAppeals([]);
        setScoreboard(null);
        setCampaign(null);
        const errObj = err as { error?: { code?: string; message?: string }; message?: string };
        if (errObj?.error?.code === 'NOT_FOUND') {
          setNoCampaign(true);
          return;
        }
        const msg = errObj?.error?.message || errObj?.message || 'Không thể tải danh sách khiếu nại từ máy chủ.';
        setErrorMsg(msg);
      }
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

  const isFinalized = campaign ? campaign.status === 'FINALIZED' : false;
  const blockingCases = scoreboard?.items.filter((item) =>
    !['ACCEPTED', 'ACCEPTED_AUTO', 'RESOLVED', 'CLOSED_INCOMPLETE', 'CLOSED_NO_SUBMIT'].includes(item.status)
  ) ?? [];
  const canFinalize = campaign?.status === 'PUBLISHED' && scoreboard !== null &&
    openAppeals.length === 0 && blockingCases.length === 0 && !loading && !finalizing;

  const handleResolve = async (appealId: string) => {
    if (resolveLock.current) return;
    setErrorMsg(null);
    setSuccessMsg(null);

    const resolution = resolutions[appealId] || 'KEEP';
    const newScore = newScores[appealId] || '';
    const reason = (bcsReasons[appealId] || '').trim();

    if (!reason) {
      setFormErrors((prev) => ({ ...prev, [appealId]: { reason: 'Nhập lý do để sinh viên hiểu căn cứ kết luận.' } }));
      return;
    }

    if (resolution === 'ADJUST') {
      const scoreNum = Number(newScore.trim());
      if (!newScore.trim() || !Number.isFinite(scoreNum) || scoreNum < 0) {
        setFormErrors((prev) => ({ ...prev, [appealId]: { score: 'Nhập điểm mới không âm, ví dụ 8.00.' } }));
        return;
      }
    }
    setFormErrors((prev) => ({ ...prev, [appealId]: {} }));

    try {
      resolveLock.current = appealId;
      setSubmittingAppealId(appealId);
      if (isDemoMode) {
        staffStore.resolveAppeal(appealId, resolution, resolution === 'ADJUST' ? newScore : null, reason);
      } else {
        await api.post(`/bcs/appeals/${appealId}/resolve`, {
          resolution,
          new_score: resolution === 'ADJUST' ? newScore : null,
          reason,
        });
      }

      setSuccessMsg(`Đã giải quyết khiếu nại thành công (${resolution === 'KEEP' ? 'Giữ nguyên' : 'Điều chỉnh điểm'}).`);
      await loadAppeals();
    } catch (err: unknown) {
      const apiError = err as { error?: { code?: string; message?: string }; message?: string };
      const msg = apiError?.error?.message || apiError?.message || 'Không lưu được kết luận. Hãy kiểm tra thông tin rồi thử lại.';
      if (['INVALID_SCORE', 'SCORE_OUT_OF_BOUNDS', 'SCORE_REQUIRED'].includes(apiError?.error?.code || '')) {
        setFormErrors((prev) => ({ ...prev, [appealId]: { score: msg } }));
      } else {
        setErrorMsg(msg);
      }
    } finally {
      setSubmittingAppealId(null);
      resolveLock.current = null;
    }
  };

  const handleFinalize = async () => {
    if (!canFinalize || finalizeLock.current) return;
    finalizeLock.current = true;
    try {
      setFinalizing(true);
      setErrorMsg(null);
      if (isDemoMode) {
        staffStore.finalizeCampaign();
      } else if (campaign) {
        await api.post(`/bcs/campaigns/${campaign.id}/finalize`);
      }
      setShowFinalizeConfirm(false);
      setSuccessMsg('Đã chốt bảng điểm chính thức. Hãy gửi bảng điểm cho GVCN để hoàn tất bàn giao.');
      await loadAppeals();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message || (err as { message?: string })?.message || 'Lỗi khi chốt điểm đợt đánh giá.';
      setErrorMsg(msg);
    } finally {
      setFinalizing(false);
      finalizeLock.current = false;
    }
  };

  const handleSendHandoff = async () => {
    if (!campaign || !isFinalized || handoffLock.current || isDemoMode) return;
    handoffLock.current = true;
    setSendingHandoff(true);
    setErrorMsg(null);
    try {
      const result = await api.post<FinalHandoff>(`/bcs/campaigns/${campaign.id}/handoff`);
      setHandoff(result);
      setSuccessMsg('Đã gửi bảng điểm chính thức cho GVCN và lưu dấu vết bàn giao.');
    } catch (err: unknown) {
      setErrorMsg((err as { error?: { message?: string } })?.error?.message || 'Không gửi được bảng điểm. Hãy thử lại.');
    } finally {
      handoffLock.current = false;
      setSendingHandoff(false);
    }
  };

  if (noCampaign) {
    return <EmptyPanel title="Chưa có đợt đánh giá" description="Khi lớp có đợt đánh giá, danh sách khiếu nại sẽ xuất hiện tại đây." />;
  }

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
            {campaign && <StatusBadge status={campaign.status} />}
          </div>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Xem xét minh chứng và lý do khiếu nại, quyết định Giữ nguyên hoặc Điều chỉnh điểm
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.35rem' }}>
          {isFinalized ? (
            <div style={{ display: 'grid', gap: '0.5rem', justifyItems: 'end' }}>
              <div className="badge badge-success" style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}>
                <Lock size={15} /> Bảng điểm đã được chốt chính thức
              </div>
              {!isDemoMode && handoff?.status === 'NOT_SENT' && (
                <button type="button" className="btn btn-primary" disabled={sendingHandoff} onClick={() => void handleSendHandoff()}>
                  {sendingHandoff ? 'Đang gửi...' : 'Gửi bảng điểm chính thức cho GVCN'}
                </button>
              )}
              {handoff?.status === 'SENT' && <span role="status">Đã gửi GVCN lúc {new Date(handoff.sent_at || '').toLocaleString('vi-VN')}; đang chờ xác nhận nhận.</span>}
              {handoff?.status === 'RECEIVED' && <span role="status">GVCN đã xác nhận nhận lúc {new Date(handoff.received_at || '').toLocaleString('vi-VN')}.</span>}
            </div>
          ) : (
            <button
              type="button"
              disabled={!canFinalize}
              onClick={() => setShowFinalizeConfirm(true)}
              className="btn btn-primary"
              style={{ fontSize: '0.875rem' }}
              title="Chốt điểm chính thức cho toàn bộ lớp"
            >
              <Lock size={15} /> {finalizing ? 'Đang chốt...' : 'Chốt điểm cả lớp'}
            </button>
          )}
          {!isFinalized && !loading && !canFinalize && (
            <span style={{ maxWidth: '18rem', textAlign: 'right', fontSize: '0.75rem', color: '#64748b' }}>
              {!campaign || !scoreboard ? 'Chưa tải đủ dữ liệu. Hãy thử tải lại trang.'
                : campaign.status !== 'PUBLISHED' ? 'Chỉ có thể chốt sau khi công bố điểm dự kiến.'
                : openAppeals.length > 0 ? 'Còn ' + openAppeals.length + ' khiếu nại cần giải quyết.'
                : 'Còn ' + blockingCases.length + ' hồ sơ chưa hoàn tất phản hồi.'}
            </span>
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
          <LoadingPanel label="Đang tải danh sách khiếu nại" />
        ) : filteredAppeals.length === 0 ? (
          <EmptyPanel
            title={filter === 'ALL' ? 'Chưa có khiếu nại' : 'Không có khiếu nại trong mục này'}
            description={filter === 'OPEN'
              ? 'Các khiếu nại cần xử lý sẽ xuất hiện tại đây.'
              : 'Hãy chọn mục khác để xem các khiếu nại hiện có.'}
          />
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
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                          <label htmlFor={'appeal-score-' + appeal.id} style={{ fontSize: '0.8rem', color: '#475569' }}>Điểm mới</label>
                          <input
                            id={'appeal-score-' + appeal.id}
                            type="text"
                            inputMode="decimal"
                            value={currentNewScore}
                            onChange={(e) => {
                              setNewScores({ ...newScores, [appeal.id]: e.target.value });
                              setFormErrors((prev) => ({ ...prev, [appeal.id]: { ...prev[appeal.id], score: undefined } }));
                            }}
                            aria-invalid={Boolean(formErrors[appeal.id]?.score)}
                            aria-describedby={formErrors[appeal.id]?.score ? 'appeal-score-error-' + appeal.id : undefined}
                            placeholder="vd: 8.00"
                            style={{ width: '80px', padding: '0.25rem 0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
                          />
                          {formErrors[appeal.id]?.score && <span id={'appeal-score-error-' + appeal.id} className="form-error-text" role="alert">{formErrors[appeal.id].score}</span>}
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      <label htmlFor={'appeal-reason-' + appeal.id} style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>
                        Lý do kết luận của Ban cán sự
                      </label>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        <input
                          id={'appeal-reason-' + appeal.id}
                          type="text"
                          value={currentBcsReason}
                          onChange={(e) => {
                            setBcsReasons({ ...bcsReasons, [appeal.id]: e.target.value });
                            setFormErrors((prev) => ({ ...prev, [appeal.id]: { ...prev[appeal.id], reason: undefined } }));
                          }}
                          aria-invalid={Boolean(formErrors[appeal.id]?.reason)}
                          aria-describedby={formErrors[appeal.id]?.reason ? 'appeal-reason-error-' + appeal.id : undefined}
                          placeholder="Nêu căn cứ kết luận..."
                          style={{ flex: 1, minWidth: '240px', padding: '0.35rem 0.6rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.825rem' }}
                        />
                        <button
                          type="button"
                          disabled={isSubmitting}
                          onClick={() => handleResolve(appeal.id)}
                          className="btn btn-primary"
                          style={{ padding: '0.35rem 0.75rem', fontSize: '0.825rem' }}
                        >
                          {isSubmitting ? 'Đang lưu...' : 'Xác nhận kết luận'}
                        </button>
                      </div>
                      {formErrors[appeal.id]?.reason && <span id={'appeal-reason-error-' + appeal.id} className="form-error-text" role="alert">{formErrors[appeal.id].reason}</span>}
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
        message="Toàn bộ khiếu nại và hồ sơ đã được xử lý. Sau khi chốt, điểm chính thức sẽ được lưu; giáo viên chủ nhiệm có thể xem và xuất bảng điểm CSV. Xác nhận chốt điểm cả lớp?"
        confirmLabel="Xác nhận chốt điểm"
        isLoading={finalizing}
        onConfirm={handleFinalize}
        onCancel={() => setShowFinalizeConfirm(false)}
      />
    </div>
  );
};
