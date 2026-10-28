import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { Deadline } from '../../components/Deadline';
import { SafeFilePreviewModal } from '../../components/staff/SafeFilePreviewModal';
import { SupplementRequestModal } from '../../components/staff/SupplementRequestModal';
import { PrintEvaluationFormModal } from '../../components/PrintEvaluationFormModal';
import { api } from '../../api/client';
import { AiReviewRun, BcsCaseDetail as BcsCaseDetailType, EvidenceFile, SupplementKind, Criterion, Claim, RuleCheckResponse, ScoreSuggestionResponse } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import {
  FileText,
  AlertTriangle,
  History,
  Save,
  CheckCircle,
  Eye,
  Info,
  ShieldAlert,
  Printer,
  Layers,
  Loader2,
} from 'lucide-react';

const isDemoMode = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';
const aiPilotEnabled = import.meta.env?.VITE_AI_REVIEW_ENABLED === 'true' && !isDemoMode;

export const BcsCaseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [caseData, setCaseData] = useState<BcsCaseDetailType | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Edit states for scores and reasons per criterion
  const [scores, setScores] = useState<Record<string, string>>({});
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [savingCriterionId, setSavingCriterionId] = useState<string | null>(null);
  const [evidenceChoices, setEvidenceChoices] = useState<Record<string, string>>({});
  const [evidenceReasons, setEvidenceReasons] = useState<Record<string, string>>({});
  const [savingEvidenceId, setSavingEvidenceId] = useState<string | null>(null);
  const evidenceRequestLock = useRef(false);

  // Modals state
  const [previewFile, setPreviewFile] = useState<EvidenceFile | null>(null);
  const [showSupplementModal, setShowSupplementModal] = useState<boolean>(false);
  const [showCompleteConfirm, setShowCompleteConfirm] = useState<boolean>(false);
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [showPrintModal, setShowPrintModal] = useState<boolean>(false);
  const [aiRun, setAiRun] = useState<AiReviewRun | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const aiRequestLock = useRef(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [ruleChecks, setRuleChecks] = useState<RuleCheckResponse | null>(null);
  const [ruleError, setRuleError] = useState<string | null>(null);
  const [scoreSuggestions, setScoreSuggestions] = useState<ScoreSuggestionResponse | null>(null);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);

  // Load case detail
  const loadCase = async () => {
    if (!id) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.get<BcsCaseDetailType>(`/bcs/cases/${id}`);
      if (data) {
        setCaseData(data);
        initFormStates(data);
      }
    } catch (err: unknown) {
      if (isDemoMode) {
        const mockCase = staffStore.getCaseDetail(id);
        if (mockCase) {
          setCaseData(mockCase);
          initFormStates(mockCase);
        } else {
          setErrorMsg('Không tìm thấy dữ liệu hồ sơ yêu cầu.');
        }
      } else {
        const errObj = err as { error?: { message?: string }; message?: string };
        setErrorMsg(errObj?.error?.message || errObj?.message || 'Không thể tải chi tiết hồ sơ từ máy chủ.');
      }
    } finally {
      setLoading(false);
    }
  };

  const initFormStates = (data: BcsCaseDetailType) => {
    const initialScores: Record<string, string> = {};
    const initialReasons: Record<string, string> = {};

    data.claims.forEach((claim) => {
      initialScores[claim.criterion.id] =
        claim.approved_score !== null
          ? claim.approved_score
          : claim.self_score !== null
          ? claim.self_score
          : '0.00';
      initialReasons[claim.criterion.id] = claim.bcs_reason || '';
    });

    setScores(initialScores);
    setReasons(initialReasons);
    setEvidenceChoices(Object.fromEntries((data.evidence_decisions || []).map((item) => [item.evidence_file_id, item.decision])));
    setEvidenceReasons(Object.fromEntries((data.evidence_decisions || []).map((item) => [item.evidence_file_id, item.reason])));
  };

  useEffect(() => {
    loadCase();
  }, [id]);

  const loadAiRun = async () => {
    if (!id || !aiPilotEnabled) return;
    try {
      const response = await api.get<{ run: AiReviewRun | null }>(`/bcs/cases/${id}/ai-reviews/latest`);
      setAiRun(response.run);
      setAiError(null);
    } catch (err: unknown) {
      const message = (err as { error?: { message?: string } })?.error?.message;
      setAiError(message || 'Không tải được trạng thái phân tích.');
    }
  };

  useEffect(() => {
    if (aiPilotEnabled && caseData) void loadAiRun();
  }, [id, caseData?.version]);

  useEffect(() => {
    if (!id || !caseData || isDemoMode) return;
    void api.get<RuleCheckResponse>(`/bcs/cases/${id}/rule-checks`)
      .then((result) => { setRuleChecks(result); setRuleError(null); })
      .catch(() => setRuleError('Không tải được kết quả kiểm tra bằng luật.'));
  }, [id, caseData?.version]);

  useEffect(() => {
    if (!id || !caseData || isDemoMode) return;
    void api.get<ScoreSuggestionResponse>(`/bcs/cases/${id}/score-suggestions`)
      .then((result) => { setScoreSuggestions(result); setSuggestionError(null); })
      .catch(() => setSuggestionError('Không tải được điểm gợi ý theo luật.'));
  }, [id, caseData?.version, aiRun?.status]);

  useEffect(() => {
    if (!aiPilotEnabled || !aiRun || !['QUEUED', 'RUNNING'].includes(aiRun.status)) return;
    const timer = window.setInterval(() => void loadAiRun(), 5000);
    return () => window.clearInterval(timer);
  }, [id, aiRun?.status]);

  const handleQueueAiReview = async () => {
    if (!id || aiRequestLock.current) return;
    aiRequestLock.current = true;
    setAiBusy(true);
    setAiError(null);
    try {
      const run = await api.post<AiReviewRun>(`/bcs/cases/${id}/ai-reviews`);
      setAiRun(run);
    } catch (err: unknown) {
      const message = (err as { error?: { message?: string } })?.error?.message;
      setAiError(message || 'Không tạo được lượt phân tích.');
    } finally {
      aiRequestLock.current = false;
      setAiBusy(false);
    }
  };

  // Aggregate all evidence files
  const allEvidenceFiles = useMemo(() => {
    if (!caseData) return [];
    const files: (EvidenceFile & { criterionCode: string; criterionTitle: string })[] = [];
    caseData.claims.forEach((claim) => {
      claim.evidence.forEach((ev) => {
        files.push({
          ...ev,
          criterionCode: claim.criterion.code,
          criterionTitle: claim.criterion.title,
        });
      });
    });
    return files;
  }, [caseData]);

  // Calculated current proposed total
  const calculatedProposedTotal = useMemo(() => {
    let sum = 0;
    Object.values(scores).forEach((val) => {
      const n = parseFloat(val);
      if (!isNaN(n)) sum += n;
    });
    return sum.toFixed(2);
  }, [scores]);

  const visibleRuleChecks = aiRun?.result?.rule_checks && !aiRun.stale
    ? aiRun.result.rule_checks : ruleChecks;

  const pendingEvidenceIds = caseData?.evidence_review_required_ids?.filter((fileId) =>
    !['ACCEPT', 'REJECT_ITEM'].includes(
      caseData.evidence_decisions?.find((item) => item.evidence_file_id === fileId)?.decision || ''
    )
  ) || [];
  const pendingEvidenceCount = pendingEvidenceIds.length;

  const handleSaveEvidenceDecision = async (evidenceId: string) => {
    if (!caseData || evidenceRequestLock.current || isDemoMode) return;
    const decision = evidenceChoices[evidenceId];
    const reason = evidenceReasons[evidenceId]?.trim() || '';
    if (!decision) {
      setErrorMsg('Hãy chọn cách xử lý minh chứng trước khi lưu.');
      return;
    }
    if (!reason) {
      setErrorMsg('Hãy ghi căn cứ để BCS và sinh viên hiểu quyết định về minh chứng.');
      return;
    }
    evidenceRequestLock.current = true;
    setSavingEvidenceId(evidenceId);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await api.put(`/bcs/cases/${caseData.id}/evidence/${evidenceId}/decision`, {
        decision, reason, expected_version: caseData.version,
      });
      setSuccessMsg(decision === 'REQUEST_SUPPLEMENT'
        ? 'Đã gửi yêu cầu bổ sung minh chứng cho sinh viên.'
        : 'Đã lưu quyết định của BCS cho minh chứng.');
      await loadCase();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message
        || (err as { message?: string })?.message || 'Không lưu được quyết định. Hãy tải lại hồ sơ rồi thử lại.';
      setErrorMsg(msg);
    } finally {
      evidenceRequestLock.current = false;
      setSavingEvidenceId(null);
    }
  };

  // Handle single criterion review save
  const handleSaveClaim = async (criterionId: string) => {
    if (!caseData) return;
    setErrorMsg(null);
    setSuccessMsg(null);

    const approvedScore = scores[criterionId];
    const reason = reasons[criterionId] || '';
    const claim = caseData.claims.find((c) => c.criterion.id === criterionId);

    if (!claim) return;

    const scoreNum = parseFloat(approvedScore);
    const maxNum =
      claim.criterion.code === '8b'
        ? Math.min(parseFloat(claim.criterion.max_score), 2.0)
        : parseFloat(claim.criterion.max_score);

    if (isNaN(scoreNum) || scoreNum < 0 || scoreNum > maxNum) {
      setErrorMsg(
        `Điểm duyệt cho [${claim.criterion.code}] phải từ 0.00 đến ${maxNum.toFixed(2)}${
          claim.criterion.code === '8b' ? ' (Mục 8b tối đa 2.00đ theo quy chuẩn)' : ''
        }.`
      );
      return;
    }

    if ((caseData.draft_editable || claim.self_score !== approvedScore) && !reason.trim()) {
      setErrorMsg(`Bắt buộc nhập lý do duyệt cho tiêu chí [${claim.criterion.code}] khi khác điểm tự khai (${claim.self_score}).`);
      return;
    }
    if (caseData.draft_editable && Number(approvedScore) !== Number(claim.approved_score)
        && reason.trim() === (claim.bcs_reason || '').trim()) {
      setErrorMsg(`Điểm dự thảo [${claim.criterion.code}] thay đổi. Hãy cập nhật căn cứ điều chỉnh mới trước khi lưu.`);
      return;
    }

    try {
      setSavingCriterionId(criterionId);
      if (isDemoMode) {
        staffStore.reviewClaim(
          caseData.id,
          criterionId,
          approvedScore,
          reason.trim() ? reason.trim() : null,
          caseData.version
        );
      } else {
        await api.put(`/bcs/cases/${caseData.id}/claims/${criterionId}/review`, {
          approved_score: approvedScore,
          reason: reason.trim() ? reason.trim() : null,
          expected_version: caseData.version,
        });
      }

      setSuccessMsg(caseData.draft_editable
        ? `Đã lưu điều chỉnh dự thảo tiêu chí [${claim.criterion.code}]. BCS cần rà soát lại bảng điểm trước họp lớp.`
        : `Đã lưu quyết định chấm tiêu chí [${claim.criterion.code}].`);
      await loadCase();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message || (err as { message?: string })?.message || 'Lỗi khi lưu điểm tiêu chí.';
      setErrorMsg(msg);
    } finally {
      setSavingCriterionId(null);
    }
  };

  // Handle supplement request
  const handleSupplementSubmit = async (kind: SupplementKind, criterionId: string | null, reason: string) => {
    if (!caseData) return;
    setErrorMsg(null);
    try {
      if (isDemoMode) {
        staffStore.createSupplementRequest(caseData.id, kind, criterionId, reason, caseData.version);
      } else {
        await api.post(`/bcs/cases/${caseData.id}/supplement-requests`, {
          kind,
          criterion_id: criterionId,
          reason,
          expected_version: caseData.version,
        });
      }
      setSuccessMsg(`Đã gửi yêu cầu bổ sung ${kind === 'INFO' ? 'thông tin' : 'minh chứng'} đến sinh viên.`);
      await loadCase();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message || (err as { message?: string })?.message || 'Lỗi khi tạo yêu cầu bổ sung.';
      setErrorMsg(msg);
      throw err;
    }
  };

  // Check if complete review is valid
  const validationError = useMemo(() => {
    if (!caseData) return null;
    if (pendingEvidenceCount > 0) {
      return `Còn ${pendingEvidenceCount} minh chứng được gắn cờ hoặc đã phân tích AI chưa có quyết định cuối cùng của BCS.`;
    }
    for (const claim of caseData.claims) {
      const currentScore = scores[claim.criterion.id];
      const currentReason = reasons[claim.criterion.id];

      if (currentScore === undefined || currentScore === '' || isNaN(parseFloat(currentScore))) {
        return `Tiêu chí [${claim.criterion.code}] chưa có điểm duyệt.`;
      }

      const scoreNum = parseFloat(currentScore);
      const maxNum = parseFloat(claim.criterion.max_score);
      if (scoreNum < 0 || scoreNum > maxNum) {
        return `Điểm tiêu chí [${claim.criterion.code}] phải từ 0 đến ${claim.criterion.max_score}.`;
      }

      if (claim.self_score !== currentScore && (!currentReason || !currentReason.trim())) {
        return `Tiêu chí [${claim.criterion.code}] có điểm duyệt khác điểm tự khai nhưng chưa có lý do.`;
      }
    }
    return null;
  }, [caseData, scores, reasons, pendingEvidenceCount]);

  // Handle complete review
  const handleCompleteReview = async () => {
    if (!caseData) return;
    if (validationError) {
      setErrorMsg(validationError);
      return;
    }

    try {
      if (isDemoMode) {
        staffStore.completeReview(caseData.id, caseData.version);
      } else {
        await api.post(`/bcs/cases/${caseData.id}/complete-review`, {
          expected_version: caseData.version,
        });
      }
      setShowCompleteConfirm(false);
      setSuccessMsg('Đã hoàn tất kiểm tra hồ sơ và chuyển sang trạng thái ĐÃ DUYỆT ĐIỂM DỰ KIẾN (PROPOSED).');
      await loadCase();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message || (err as { message?: string })?.message || 'Lỗi khi hoàn tất kiểm tra hồ sơ.';
      setErrorMsg(msg);
    }
  };

  if (loading) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
        Đang tải dữ liệu hồ sơ chi tiết...
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <h3 style={{ color: '#dc2626' }}>{errorMsg || 'Không tìm thấy hồ sơ'}</h3>
        <Link to="/bcs/cases" className="btn btn-secondary" style={{ marginTop: '1rem' }}>
          Quay lại hàng chờ
        </Link>
      </div>
    );
  }

  const isProposedOrBeyond = [
    'PROPOSED',
    'PUBLISHED',
    'ACCEPTED',
    'ACCEPTED_AUTO',
    'APPEALED',
    'RESOLVED',
    'FINALIZED',
  ].includes(caseData.status);
  const canEditScores = !isProposedOrBeyond || !!caseData.draft_editable;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* 1. Header Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '1rem',
          backgroundColor: '#ffffff',
          padding: '1.25rem',
          borderRadius: '8px',
          border: '1px solid #e2e8f0',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <Link to="/bcs/cases" style={{ fontSize: '0.85rem', fontWeight: 500, color: '#1e40af' }}>
              ← Quay lại hàng chờ
            </Link>
            <span style={{ color: '#cbd5e1' }}>|</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
              Hồ sơ: {caseData.student.code} · {caseData.student.full_name}
            </h2>
            <StatusBadge status={caseData.status} />
            <span
              style={{
                fontSize: '0.75rem',
                backgroundColor: '#f1f5f9',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                color: '#475569',
                fontWeight: 600,
              }}
            >
              Phiên bản: {caseData.version}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', marginTop: '0.4rem', fontSize: '0.825rem', color: '#64748b', flexWrap: 'wrap' }}>
            <div>
              Lượt bổ sung: <strong style={{ color: '#0f172a' }}>INFO: {caseData.rounds.info}/{caseData.rounds.info_max}</strong> · <strong style={{ color: '#0f172a' }}>PROOF: {caseData.rounds.proof}/{caseData.rounds.proof_max}</strong>
            </div>
            {caseData.deadlines.supplement_at && (
              <div>
                Hạn sinh viên bổ sung: <Deadline isoString={caseData.deadlines.supplement_at} label="Hạn" />
              </div>
            )}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                color: '#b45309',
                backgroundColor: '#fef3c7',
                padding: '0.15rem 0.5rem',
                borderRadius: '4px',
                fontWeight: 600,
              }}
            >
              <ShieldAlert size={14} /> Chế độ kiểm tra thủ công — AI chưa kích hoạt
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setShowPrintModal(true)}
            style={{ fontSize: '0.825rem' }}
          >
            <Printer size={14} /> In phiếu đánh giá (A4)
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setShowHistory(!showHistory)}
            style={{ fontSize: '0.825rem' }}
          >
            <History size={14} /> Lịch sử
          </button>

          {!isProposedOrBeyond && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowSupplementModal(true)}
              style={{ fontSize: '0.825rem' }}
            >
              Yêu cầu bổ sung
            </button>
          )}

          {!isProposedOrBeyond && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                if (validationError) {
                  setErrorMsg(validationError);
                } else {
                  setShowCompleteConfirm(true);
                }
              }}
              style={{ fontSize: '0.825rem' }}
            >
              <CheckCircle size={14} /> Hoàn tất kiểm tra
            </button>
          )}
        </div>
      </div>

      {/* Notifications / Alerts */}
      {pendingEvidenceCount > 0 && (
        <div className="student-alert student-alert-warning" role="status">
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <span style={{ flex: 1 }}>
            Còn {pendingEvidenceCount} minh chứng cần kết luận. Mở tệp ở vùng “Minh chứng gốc”, chọn hướng xử lý, nhập căn cứ rồi bấm “Lưu quyết định minh chứng”.
          </span>
          <button type="button" className="btn btn-secondary" onClick={() =>
            document.getElementById(`evidence-review-${pendingEvidenceIds[0]}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }>
            Đến minh chứng cần xử lý
          </button>
        </div>
      )}
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
          <CheckCircle size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {!isDemoMode && (
        <section className="card" aria-label="Kiểm tra bằng luật">
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>Kiểm tra bằng luật</h3>
          {ruleError && <p role="alert" style={{ color: '#b91c1c' }}>{ruleError}</p>}
          {visibleRuleChecks && (
            <>
              <p style={{ fontSize: '0.85rem', color: '#475569', marginTop: '0.3rem' }}>
                {visibleRuleChecks.counts.flagged} mục cần xem · {visibleRuleChecks.counts.unknown} mục chưa đủ dữ liệu.
                {visibleRuleChecks.term_window.status === 'NOT_CONFIGURED'
                  ? ' Chưa cấu hình khoảng ngày học kỳ nên chưa thể xét ngày trên giấy.'
                  : ` Học kỳ: ${visibleRuleChecks.term_window.start_on} đến ${visibleRuleChecks.term_window.end_on}.`}
              </p>
              {visibleRuleChecks.findings.length === 0
                ? <p style={{ fontSize: '0.85rem', color: '#64748b' }}>Chưa thấy vấn đề trong dữ liệu có cấu trúc; Ban cán sự vẫn cần xem minh chứng gốc.</p>
                : <ul style={{ margin: '0.55rem 0 0 1.2rem', padding: 0, fontSize: '0.85rem' }}>
                    {visibleRuleChecks.findings.map((finding, index) => (
                      <li key={`${finding.code}-${index}`} style={{ marginBottom: '0.35rem', color: finding.level === 'FLAGGED' ? '#92400e' : '#475569' }}>
                        {finding.criterion_code && <strong>[{finding.criterion_code}] </strong>}{finding.message}
                      </li>
                    ))}
                  </ul>}
            </>
          )}
        </section>
      )}

      {!isDemoMode && (
        <section className="card" aria-label="Điểm gợi ý theo luật">
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>Điểm gợi ý theo luật</h3>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.3rem' }}>
            Chỉ hỗ trợ rà soát. Ban cán sự vẫn nhập, lưu và chốt điểm; hệ thống không tự áp dụng gợi ý.
          </p>
          {suggestionError && <p role="alert" style={{ color: '#b91c1c' }}>{suggestionError}</p>}
          {scoreSuggestions && (
            <>
              <p style={{ fontSize: '0.85rem', marginTop: '0.4rem' }}>
                {scoreSuggestions.ready_count} mục có gợi ý · {scoreSuggestions.review_required_count} mục cần Ban cán sự xem.
                {scoreSuggestions.draft_total !== null && ` Tổng gợi ý: ${scoreSuggestions.draft_total} điểm.`}
              </p>
              <details style={{ marginTop: '0.45rem' }}>
                <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Xem gợi ý từng tiêu chí</summary>
                <ul style={{ margin: '0.55rem 0 0 1.2rem', padding: 0, fontSize: '0.85rem' }}>
                  {scoreSuggestions.items.map((item) => (
                    <li key={item.criterion_id} style={{ marginBottom: '0.6rem' }}>
                      <strong>[{item.criterion_code}] {item.draft_score !== null ? `${item.draft_score} điểm` : 'Cần xem thủ công'}</strong>
                      <div>{item.reason}</div>
                      {item.calculation && <div style={{ color: '#475569' }}>{item.calculation}</div>}
                      <div style={{ color: '#64748b' }}>Nguồn quy tắc: {item.clause_id}</div>
                    </li>
                  ))}
                </ul>
              </details>
            </>
          )}
        </section>
      )}

      {aiPilotEnabled && (
        <section className="card" aria-label="Hỗ trợ phân tích minh chứng">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>Hỗ trợ phân tích minh chứng</h3>
              <p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                AI hỗ trợ đọc và đối chiếu minh chứng; Ban cán sự kiểm tra tệp gốc và chốt kết quả.
              </p>
            </div>
            {caseData.status === 'BCS_REVIEW' && (!aiRun || aiRun.stale) && (
              <button type="button" className="btn btn-secondary" onClick={handleQueueAiReview} disabled={aiBusy} aria-busy={aiBusy}>
                {aiBusy && <Loader2 size={14} className="ai-spinner" aria-hidden="true" />}
                <span role={aiBusy ? 'status' : undefined}>{aiBusy ? 'Đang gửi yêu cầu...' : 'Phân tích minh chứng'}</span>
              </button>
            )}
          </div>
          {aiError && <p role="alert" style={{ color: '#b91c1c', marginTop: '0.75rem' }}>{aiError}</p>}
          {aiRun && (
            <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: '#334155' }}>
              <div>
                Trạng thái: {['QUEUED', 'RUNNING'].includes(aiRun.status) && <Loader2 size={14} className="ai-spinner" aria-hidden="true" />} <strong>{({
                  QUEUED: 'Chờ xử lý', RUNNING: 'Đang xử lý', COMPLETED: 'Hoàn tất',
                  NEEDS_HUMAN: 'Cần Ban cán sự xem', FAILED: 'Lỗi xử lý', STALE: 'Hồ sơ đã đổi',
                } as Record<string, string>)[aiRun.status] || aiRun.status}</strong>
                {aiRun.stale && <span style={{ color: '#b45309' }}> · Kết quả cũ không còn hiệu lực</span>}
              </div>
              <div style={{ color: '#64748b', marginTop: '0.25rem' }}>Phiên bản hồ sơ: {aiRun.case_version} · Quy tắc: {aiRun.rubric_version}</div>
              {aiRun.error_code && <p role="status" style={{ color: '#b45309', marginTop: '0.35rem' }}>
                {aiRun.error_code === 'MODEL_RATE_LIMITED'
                  ? 'Gemini đang giới hạn lượt gọi. Hệ thống sẽ thử lại; Ban cán sự vẫn có thể xem thủ công.'
                  : `Chưa đọc được minh chứng (${aiRun.error_code}). Ban cán sự xem thủ công.`}
              </p>}
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                {aiRun.steps.map((step) => (
                  <span key={step.kind}>{step.kind === 'AI_READ' ? 'Đọc dữ liệu' : 'Đối chiếu minh chứng'}: {step.status}</span>
                ))}
              </div>
              {aiRun.result?.summary && <p style={{ marginTop: '0.5rem' }}>{aiRun.result.summary}</p>}
              {aiRun.steps.find((step) => step.kind === 'AI_READ')?.output?.files?.map((readFile) => {
                const evidence = allEvidenceFiles.find((file) => file.id === readFile.evidence_file_id);
                return (
                  <details key={readFile.evidence_file_id} style={{ marginTop: '0.6rem', borderTop: '1px solid #e2e8f0', paddingTop: '0.5rem' }}>
                    <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
                      {evidence?.original_name || readFile.evidence_file_id} · {readFile.readable ? 'Đã đọc' : 'Cần xem thủ công'}
                    </summary>
                    {evidence && <button type="button" className="btn btn-secondary" onClick={() => setPreviewFile(evidence)} style={{ marginTop: '0.5rem' }}>Mở minh chứng gốc</button>}
                    {!readFile.readable && <p>{readFile.unreadable_reason}</p>}
                    {readFile.facts.map((fact, index) => (
                      <p key={`${fact.kind}-${index}`} style={{ marginTop: '0.4rem' }}>
                        <strong>{fact.kind}:</strong> {fact.value} · trang {fact.page}<br />
                        <span style={{ color: '#64748b' }}>AI trích: “{fact.source_excerpt}” — cần đối chiếu với tệp gốc.</span>
                      </p>
                    ))}
                  </details>
                );
              })}
              {aiRun.steps.find((step) => step.kind === 'AI_TRANSPARENCY')?.output?.assessments?.map((assessment) => {
                const evidence = allEvidenceFiles.find((file) => file.id === assessment.evidence_file_id);
                const verdictLabel = { SUPPORTED: 'Nội dung phù hợp', FLAGGED: 'Cần kiểm tra', UNKNOWN: 'Chưa đủ căn cứ' }[assessment.verdict];
                return (
                  <details key={`assessment-${assessment.evidence_file_id}`} style={{ marginTop: '0.6rem', borderTop: '1px solid #e2e8f0', paddingTop: '0.5rem' }}>
                    <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
                      [{assessment.criterion_code}] {evidence?.original_name || assessment.evidence_file_id} · {verdictLabel}
                    </summary>
                    <p style={{ marginTop: '0.45rem' }}>{assessment.reason}</p>
                    <p style={{ color: '#64748b', marginTop: '0.3rem' }}>Điều khoản: {assessment.rule_clause_id} · {assessment.rule_text}</p>
                    {assessment.evidence_requirements && <p style={{ color: '#64748b' }}>Yêu cầu minh chứng: {assessment.evidence_requirements}</p>}
                    {assessment.citations.map((citation, index) => (
                      <p key={`citation-${index}`} style={{ marginTop: '0.3rem' }}>Trang {citation.page}: “{citation.source_excerpt}”</p>
                    ))}
                    {assessment.visual_signals.map((signal, index) => (
                      <p key={`signal-${index}`} style={{ color: signal.concern ? '#92400e' : '#475569' }}>
                        Dấu hiệu trên trang {signal.page}: {signal.description}
                      </p>
                    ))}
                    <p style={{ color: '#92400e', marginTop: '0.3rem' }}>
                      {assessment.authenticity === 'SUSPICIOUS'
                        ? 'Có dấu hiệu cần kiểm tra bản gốc và đơn vị cấp.'
                        : 'AI chưa xác minh được tính thật giả hoặc đơn vị cấp.'}
                    </p>
                    {assessment.limitations.map((limitation, index) => <p key={`limit-${index}`} style={{ color: '#64748b' }}>{limitation}</p>)}
                    {evidence && <button type="button" className="btn btn-secondary" onClick={() => setPreviewFile(evidence)}>Mở minh chứng gốc</button>}
                  </details>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* Audit History Panel */}
      {showHistory && (
        <div className="card" style={{ backgroundColor: '#f8fafc', border: '1px dashed #cbd5e1' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem', color: '#1e40af' }}>
            Nhật ký thao tác hồ sơ (Audit Trail)
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
            {caseData.history.map((h, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.25rem' }}>
                <span style={{ fontWeight: 600 }}>{h.action}</span>
                <span style={{ color: '#64748b' }}>Thực hiện bởi: {h.actor}</span>
                <span style={{ color: '#94a3b8' }}>{new Date(h.at).toLocaleString('vi-VN')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 2. 3-ZONE LAYOUT */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '1.25rem',
          alignItems: 'start',
        }}
      >
        {/* ================= VÙNG 1: MINH CHỨNG GỐC ================= */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', minHeight: '480px' }}>
          <div style={{ borderBottom: '2px solid #e2e8f0', paddingBottom: '0.6rem', marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#1e40af' }}>
              1. Minh chứng gốc ({allEvidenceFiles.length})
            </h3>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Kiểm tra an toàn</span>
          </div>

          <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.75rem' }}>
            Tất cả tệp PDF/JPG/PNG do sinh viên tải lên được kiểm tra mã băm SHA-256 và mở trong sandbox.
          </p>
          {pendingEvidenceCount > 0 && (
            <p role="status" style={{ fontSize: '0.8rem', color: '#9a3412', marginBottom: '0.75rem' }}>
              Còn {pendingEvidenceCount} minh chứng cần BCS kết luận trước khi hoàn tất hồ sơ.
            </p>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flex: 1 }}>
            {allEvidenceFiles.length === 0 ? (
              <div
                style={{
                  padding: '2rem',
                  textAlign: 'center',
                  backgroundColor: '#f8fafc',
                  borderRadius: '6px',
                  color: '#64748b',
                  fontSize: '0.85rem',
                }}
              >
                Sinh viên chưa đính kèm tệp minh chứng nào cho hồ sơ này.
              </div>
            ) : (
              allEvidenceFiles.map((file) => (
                <div
                  key={file.id}
                  id={`evidence-review-${file.id}`}
                  style={{
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    padding: '0.75rem',
                    backgroundColor: '#ffffff',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.35rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, fontSize: '0.85rem', color: '#0f172a' }}>
                      <FileText size={16} color="#0284c7" />
                      <span>{file.original_name}</span>
                    </div>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      {(file.size_bytes / 1024).toFixed(0)} KB
                    </span>
                  </div>

                  <div style={{ fontSize: '0.75rem', color: '#475569' }}>
                    Thuộc tiêu chí: <strong>[{file.criterionCode}] {file.criterionTitle}</strong>
                  </div>

                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Tải lên: {new Date(file.uploaded_at).toLocaleString('vi-VN')}
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.4rem' }}>
                    <button
                      type="button"
                      onClick={() => setPreviewFile(file)}
                      className="btn btn-secondary"
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', flex: 1 }}
                    >
                      <Eye size={12} /> Xem an toàn
                    </button>
                  </div>
                  {(() => {
                    const saved = caseData.evidence_decisions?.find((item) => item.evidence_file_id === file.id);
                    const required = caseData.evidence_review_required_ids?.includes(file.id) || false;
                    const editable = caseData.status === 'BCS_REVIEW' && !isDemoMode;
                    return (
                      <div style={{ borderTop: '1px solid #e2e8f0', marginTop: '0.5rem', paddingTop: '0.6rem', display: 'grid', gap: '0.45rem' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 600, color: required ? '#9a3412' : '#475569' }}>
                          {required ? 'Cần BCS kết luận' : 'Kết luận của BCS'}: {saved ? ({ ACCEPT: 'Chấp nhận', REQUEST_SUPPLEMENT: 'Đã yêu cầu bổ sung', REJECT_ITEM: 'Từ chối tệp', HOLD: 'Tạm giữ để xác minh' }[saved.decision]) : 'Chưa có'}
                        </span>
                        {saved && <p style={{ fontSize: '0.75rem', color: '#475569', margin: 0 }}>Căn cứ: {saved.reason}</p>}
                        {editable && (
                          <>
                            <label htmlFor={`decision-${file.id}`} style={{ fontSize: '0.75rem', fontWeight: 600 }}>Hướng xử lý minh chứng</label>
                            <select id={`decision-${file.id}`} value={evidenceChoices[file.id] || ''}
                              onChange={(event) => setEvidenceChoices((prev) => ({ ...prev, [file.id]: event.target.value }))}
                              disabled={savingEvidenceId !== null}>
                              <option value="">Chọn quyết định</option>
                              <option value="ACCEPT">Chấp nhận tệp</option>
                              <option value="REQUEST_SUPPLEMENT" disabled={caseData.rounds.proof >= caseData.rounds.proof_max}>Yêu cầu sinh viên bổ sung</option>
                              <option value="REJECT_ITEM">Từ chối tệp</option>
                              <option value="HOLD">Tạm giữ để xác minh</option>
                            </select>
                            <label htmlFor={`reason-${file.id}`} style={{ fontSize: '0.75rem', fontWeight: 600 }}>Căn cứ quyết định</label>
                            <textarea id={`reason-${file.id}`} rows={2} value={evidenceReasons[file.id] || ''}
                              onChange={(event) => setEvidenceReasons((prev) => ({ ...prev, [file.id]: event.target.value }))}
                              placeholder="Nêu thông tin đã đối chiếu và lý do chấp nhận hoặc xử lý tiếp"
                              disabled={savingEvidenceId !== null} />
                            <button type="button" className="btn btn-primary" disabled={savingEvidenceId !== null || !evidenceChoices[file.id] || !evidenceReasons[file.id]?.trim()}
                              onClick={() => void handleSaveEvidenceDecision(file.id)}>
                              {savingEvidenceId === file.id ? 'Đang lưu quyết định...' : 'Lưu quyết định minh chứng'}
                            </button>
                          </>
                        )}
                      </div>
                    );
                  })()}
                </div>
              ))
            )}
          </div>
        </div>

        {/* ================= VÙNG 2: TỰ KHAI & QUY ĐỊNH ================= */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', minHeight: '480px' }}>
          <div style={{ borderBottom: '2px solid #e2e8f0', paddingBottom: '0.6rem', marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#1e40af' }}>
              2. Tự khai & Quy định
            </h3>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
              {caseData.claims.length} tiêu chí
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {caseData.claims.map((claim) => (
              <div
                key={claim.criterion.id}
                style={{
                  borderBottom: '1px solid #f1f5f9',
                  paddingBottom: '0.75rem',
                  fontSize: '0.85rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#0f172a' }}>
                      [{claim.criterion.code}] {claim.criterion.title}
                    </div>
                    {claim.criterion.section_title && (
                      <div style={{ fontSize: '0.725rem', color: '#1e40af', fontWeight: 500, marginTop: '0.1rem' }}>
                        {claim.criterion.section_title}
                      </div>
                    )}
                  </div>
                  {claim.criterion.requires_evidence ? (
                    <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                      Cần minh chứng
                    </span>
                  ) : (
                    <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                      Không cần minh chứng
                    </span>
                  )}
                </div>

                <div style={{ color: '#64748b', fontSize: '0.775rem', marginTop: '0.2rem' }}>
                  {claim.criterion.description}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.4rem', backgroundColor: '#f8fafc', padding: '0.35rem 0.5rem', borderRadius: '4px' }}>
                  <span style={{ color: '#64748b' }}>Tối đa: {claim.criterion.max_score} điểm</span>
                  <span>
                    Sinh viên tự khai:{' '}
                    <strong style={{ color: '#0f172a', fontSize: '0.9rem' }}>
                      {claim.self_score !== null ? `${claim.self_score} đ` : 'Chưa nhập'}
                    </strong>
                    {claim.academic_gpa && (
                      <span style={{ fontSize: '0.75rem', color: '#2563eb', marginLeft: '0.35rem' }}>
                        (GPA: {claim.academic_gpa})
                      </span>
                    )}
                  </span>
                </div>

                {claim.student_note && (
                  <div style={{ marginTop: '0.35rem', fontStyle: 'italic', color: '#475569', fontSize: '0.8rem' }}>
                    Ghi chú SV: "{claim.student_note}"
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ================= VÙNG 3: QUYẾT ĐỊNH CỦA BCS ================= */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', minHeight: '480px' }}>
          <div style={{ borderBottom: '2px solid #e2e8f0', paddingBottom: '0.6rem', marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#1e40af' }}>
              3. Quyết định của BCS
            </h3>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#1e40af' }}>
              Tổng duyệt: {calculatedProposedTotal} đ
            </span>
          </div>
          {caseData.draft_editable && <p role="status" style={{ color: '#92400e', fontSize: '0.8rem' }}>
            Đang rà soát dự thảo sau họp BCS. Mọi điều chỉnh cần lý do và sẽ yêu cầu xác nhận lại bản dự thảo trước họp lớp.
          </p>}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1 }}>
            {caseData.claims.map((claim) => {
              const currentScore = scores[claim.criterion.id] || '';
              const currentReason = reasons[claim.criterion.id] || '';
              const isDiff = claim.self_score !== currentScore;
              const isSaving = savingCriterionId === claim.criterion.id;

              return (
                <div
                  key={claim.criterion.id}
                  style={{
                    backgroundColor: isDiff ? '#fffbeb' : '#f8fafc',
                    border: isDiff ? '1px solid #fde68a' : '1px solid #e2e8f0',
                    borderRadius: '6px',
                    padding: '0.75rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#0f172a' }}>
                      [{claim.criterion.code}] {claim.criterion.title}
                    </span>
                    <button
                      type="button"
                      disabled={isSaving || !canEditScores}
                      onClick={() => handleSaveClaim(claim.criterion.id)}
                      className="btn btn-secondary"
                      style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      title="Lưu tiêu chí này"
                    >
                      <Save size={12} /> {isSaving ? 'Đang lưu...' : caseData.draft_editable ? 'Lưu điều chỉnh' : 'Lưu điểm duyệt'}
                    </button>
                  </div>

                  {/* Quick Select Options for BCS */}
                  {claim.criterion.rule_config?.options && canEditScores && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.2rem' }}>
                      {claim.criterion.rule_config.options.map((opt, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => {
                            const valStr = opt.score.toFixed(2);
                            setScores({ ...scores, [claim.criterion.id]: valStr });
                            if (valStr !== claim.self_score && !reasons[claim.criterion.id]?.trim()) {
                              setReasons({
                                ...reasons,
                                [claim.criterion.id]: `Duyệt theo mức: ${opt.label}`,
                              });
                            }
                          }}
                          style={{
                            padding: '0.15rem 0.45rem',
                            fontSize: '0.7rem',
                            backgroundColor:
                              currentScore !== '' && parseFloat(currentScore) === opt.score
                                ? '#1e40af'
                                : '#e2e8f0',
                            color:
                              currentScore !== '' && parseFloat(currentScore) === opt.score
                                ? '#ffffff'
                                : '#334155',
                            border: 'none',
                            borderRadius: '3px',
                            cursor: 'pointer',
                          }}
                        >
                          {opt.label} ({opt.score}đ)
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Input Score */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={{ fontSize: '0.8rem', color: '#475569', fontWeight: 500 }}>
                      Điểm được duyệt (Tối đa {claim.criterion.code === '8b' ? '2.00' : claim.criterion.max_score}):
                    </label>
                    <input
                      type="text"
                      disabled={!canEditScores}
                      value={currentScore}
                      onChange={(e) =>
                        setScores({
                          ...scores,
                          [claim.criterion.id]: e.target.value,
                        })
                      }
                      style={{
                        width: '80px',
                        padding: '0.3rem 0.5rem',
                        borderRadius: '4px',
                        border: '1px solid #cbd5e1',
                        textAlign: 'right',
                        fontWeight: 700,
                        fontSize: '0.875rem',
                        color: '#0f172a',
                      }}
                    />
                  </div>

                  {/* Input Reason */}
                  <div>
                    <input
                      type="text"
                      disabled={!canEditScores}
                      value={currentReason}
                      onChange={(e) =>
                        setReasons({
                          ...reasons,
                          [claim.criterion.id]: e.target.value,
                        })
                      }
                      placeholder={
                        caseData.draft_editable
                          ? 'Bắt buộc nêu căn cứ điều chỉnh dự thảo...'
                          : isDiff
                          ? 'Bắt buộc nhập lý do vì điểm duyệt khác tự khai...'
                          : 'Lý do phê duyệt (tùy chọn)...'
                      }
                      style={{
                        width: '100%',
                        padding: '0.35rem 0.6rem',
                        borderRadius: '4px',
                        border: isDiff && !currentReason.trim() ? '1px solid #ef4444' : '1px solid #cbd5e1',
                        fontSize: '0.8rem',
                      }}
                    />
                    {(isDiff || caseData.draft_editable) && !currentReason.trim() && (
                      <div style={{ fontSize: '0.725rem', color: '#dc2626', marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <Info size={12} /> {caseData.draft_editable ? 'Bắt buộc ghi căn cứ điều chỉnh dự thảo.' : 'Bắt buộc nhập lý do khi điểm duyệt khác điểm sinh viên tự khai.'}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Safe File Preview Modal */}
      <SafeFilePreviewModal
        isOpen={previewFile !== null}
        file={previewFile}
        onClose={() => setPreviewFile(null)}
      />

      {/* Supplement Request Modal */}
      <SupplementRequestModal
        isOpen={showSupplementModal}
        criteria={caseData.claims.map((c) => c.criterion)}
        currentInfoRound={caseData.rounds.info}
        maxInfoRounds={caseData.rounds.info_max}
        currentProofRound={caseData.rounds.proof}
        maxProofRounds={caseData.rounds.proof_max}
        onClose={() => setShowSupplementModal(false)}
        onSubmit={handleSupplementSubmit}
      />

      {/* Complete Review Confirmation Modal */}
      <ConfirmDialog
        isOpen={showCompleteConfirm}
        title="Xác nhận Hoàn tất Kiểm tra Hồ sơ"
        message={`Hồ sơ của sinh viên ${caseData.student.code} · ${caseData.student.full_name} sẽ được chuyển sang trạng thái ĐÃ DUYỆT ĐIỂM DỰ KIẾN (PROPOSED) với tổng điểm là ${calculatedProposedTotal}. Bạn có chắc chắn muốn xác nhận?`}
        confirmLabel="Xác nhận hoàn tất"
        onConfirm={handleCompleteReview}
        onCancel={() => setShowCompleteConfirm(false)}
      />

      {/* Print Evaluation Form Modal */}
      <PrintEvaluationFormModal
        isOpen={showPrintModal}
        onClose={() => setShowPrintModal(false)}
        campaignTitle="Đánh giá kết quả rèn luyện"
        term="HK1-2026-2027"
        studentName={caseData.student.full_name}
        studentCode={caseData.student.code}
        showClassScores={isProposedOrBeyond}
        criteria={caseData.claims.map((c) => c.criterion)}
        claims={caseData.claims.map((c) => ({
          id: c.criterion.id,
          criterion_id: c.criterion.id,
          self_score: c.self_score,
          student_note: c.student_note,
          approved_score: c.approved_score,
          bcs_reason: c.bcs_reason,
          evidence: c.evidence,
        }))}
      />
    </div>
  );
};
