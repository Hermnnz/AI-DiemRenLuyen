import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { Deadline } from '../../components/Deadline';
import { SafeFilePreviewModal } from '../../components/staff/SafeFilePreviewModal';
import { SupplementRequestModal } from '../../components/staff/SupplementRequestModal';
import { PrintEvaluationFormModal } from '../../components/PrintEvaluationFormModal';
import { api } from '../../api/client';
import { AiReviewRun, BcsCaseDetail as BcsCaseDetailType, EvidenceFile, EvidenceScoreAdjustment, SupplementKind, Criterion, Claim, RuleCheckResponse, ScoreSuggestionResponse } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import {
  FileText,
  AlertTriangle,
  History,
  Save,
  CheckCircle,
  Eye,
  Info,
  Printer,
  Layers,
  Loader2,
  Lock,
} from 'lucide-react';

const isDemoMode = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';
const aiPilotEnabled = import.meta.env?.VITE_AI_REVIEW_ENABLED === 'true' && !isDemoMode;

export const isSystemCriterion = (criterion: Pick<Criterion, 'code' | 'rule_config' | 'allowed_input_roles'>): boolean => {
  return Boolean(
    criterion.code === '4e' ||
    criterion.code === 'e' ||
    criterion.rule_config?.type === 'GPA_CONVERSION' ||
    (criterion.allowed_input_roles &&
      criterion.allowed_input_roles.length > 0 &&
      !criterion.allowed_input_roles.includes('BCS') &&
      !criterion.allowed_input_roles.includes('STUDENT_CADRE') &&
      (criterion.allowed_input_roles.includes('SYSTEM') || criterion.allowed_input_roles.includes('ADMIN')))
  );
};

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
  const [savingAllScores, setSavingAllScores] = useState(false);
  const saveAllScoresLock = useRef(false);
  const [evidenceChoices, setEvidenceChoices] = useState<Record<string, string>>({});
  const [evidenceReasons, setEvidenceReasons] = useState<Record<string, string>>({});
  const [savingEvidenceId, setSavingEvidenceId] = useState<string | null>(null);
  const [reconsiderEvidenceIds, setReconsiderEvidenceIds] = useState<string[]>([]);
  const evidenceRequestLock = useRef(false);

  // Modals state
  const [previewFile, setPreviewFile] = useState<EvidenceFile | null>(null);
  const [showSupplementModal, setShowSupplementModal] = useState<boolean>(false);
  const [showCompleteConfirm, setShowCompleteConfirm] = useState<boolean>(false);
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [showPrintModal, setShowPrintModal] = useState<boolean>(false);
  const [aiRun, setAiRun] = useState<AiReviewRun | null>(null);
  const [aiRunLoading, setAiRunLoading] = useState(aiPilotEnabled);
  const [aiError, setAiError] = useState<string | null>(null);
  const [ruleChecks, setRuleChecks] = useState<RuleCheckResponse | null>(null);
  const [ruleError, setRuleError] = useState<string | null>(null);
  const [scoreSuggestions, setScoreSuggestions] = useState<ScoreSuggestionResponse | null>(null);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);

  // Load case detail
  const loadCase = async (preserveScoreDrafts = false) => {
    if (!id) return;
    const draftScores = scores;
    const draftReasons = reasons;
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.get<BcsCaseDetailType>(`/bcs/cases/${id}`);
      if (data) {
        setCaseData(data);
        initFormStates(data);
        if (preserveScoreDrafts) {
          setScores(draftScores);
          setReasons(draftReasons);
        }
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
      const isSystem = isSystemCriterion(claim.criterion);
      initialScores[claim.criterion.id] =
        claim.approved_score !== null
          ? claim.approved_score
          : isSystem
          ? (claim.self_score !== null ? claim.self_score : '0.00')
          : data.status === 'BCS_REVIEW' && claim.self_score !== null
          ? claim.self_score
          : data.status === 'BCS_REVIEW' ? '0.00' : '';
      initialReasons[claim.criterion.id] = claim.bcs_reason || (isSystem ? 'Nhà trường tự động quy đổi từ kết quả học tập TBCHK' : '');
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
      if (response.run && !['QUEUED', 'RUNNING'].includes(response.run.status)) {
        // AI finishes without changing case.version. Refresh its evidence
        // decisions without overwriting the score form the BCS is editing.
        const detail = await api.get<BcsCaseDetailType>(`/bcs/cases/${id}`);
        setCaseData(detail);
      }
    } catch (err: unknown) {
      const message = (err as { error?: { message?: string } })?.error?.message;
      setAiError(message || 'Không tải được trạng thái phân tích.');
    } finally {
      setAiRunLoading(false);
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

  // Aggregate all evidence files
  const allEvidenceFiles = useMemo(() => {
    if (!caseData) return [];
    const files: (EvidenceFile & { criterionCode: string; criterionTitle: string; criterionId: string })[] = [];
    caseData.claims.forEach((claim) => {
      claim.evidence.forEach((ev) => {
        files.push({
          ...ev,
          criterionCode: claim.criterion.code,
          criterionTitle: claim.criterion.title,
          criterionId: claim.criterion.id,
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
  const aiPending = aiPilotEnabled && !aiError && !aiRun?.stale &&
    (aiRunLoading || (!!aiRun && ['QUEUED', 'RUNNING'].includes(aiRun.status)));

  const getAiVerificationReason = (fileId: string, criterionCode: string, criterionId: string) => {
    // 1. Kiểm tra AI_READ (tệp không đọc được, mờ hoặc sai định dạng)
    const readStep = aiRun?.steps?.find((s) => s.kind === 'AI_READ');
    const readFile = readStep?.output?.files?.find((f) => f.evidence_file_id === fileId);
    if (readFile && readFile.readable === false) {
      return {
        title: 'Tệp không thể đọc hoặc trích xuất nội dung',
        reason: readFile.unreadable_reason || 'Ảnh/tài liệu bị mờ, không nhận diện được ký tự hoặc sai định dạng kỹ thuật.',
        badgeType: 'danger' as const,
      };
    }

    // 2. Kiểm tra AI_TRANSPARENCY (đối chiếu tiêu chí, độ tin cậy, can thiệp ảnh)
    const transStep = aiRun?.steps?.find((s) => s.kind === 'AI_TRANSPARENCY');
    const assessment = transStep?.output?.assessments?.find((a) => a.evidence_file_id === fileId);
    if (assessment) {
      // Dấu hiệu bất thường hình ảnh / nghi vấn giả mạo
      const visualConcern = assessment.visual_signals?.find((s) => s.concern);
      if (visualConcern || assessment.authenticity === 'SUSPICIOUS') {
        return {
          title: 'AI phát hiện bất thường hình ảnh / nghi vấn can thiệp',
          reason: visualConcern?.description || 'Hình ảnh có dấu hiệu bị cắt ghép, chỉnh sửa hoặc tính xác thực không đảm bảo. Cần BCS đối chiếu trực tiếp tệp gốc.',
          badgeType: 'danger' as const,
        };
      }

      // Đánh giá verdict
      if (assessment.verdict === 'FLAGGED') {
        return {
          title: 'AI đối chiếu: Không phù hợp tiêu chí',
          reason: assessment.reason || 'Nội dung minh chứng không đáp ứng điều kiện quy định của tiêu chí.',
          badgeType: 'warning' as const,
        };
      }
      if (assessment.verdict === 'UNKNOWN') {
        return {
          title: 'AI đối chiếu: Chưa đủ thông tin xác thực',
          reason: assessment.reason || 'Thiếu dữ kiện rõ ràng (ngày diễn ra, tên người nhận, đơn vị ban hành) để AI tự động công nhận.',
          badgeType: 'warning' as const,
        };
      }

      // Both confidence checks use the threshold returned by the backend.
      const threshold = aiRun?.result?.auto_accept_threshold ?? 0.7;
      const conf = assessment.confidence ?? 0;
      const selfConf = assessment.self_review?.confidence ?? 0;
      if (conf < threshold || (assessment.self_review && selfConf < threshold)) {
        const lowestConf = assessment.self_review && selfConf < conf ? selfConf : conf;
        return {
          title: `Độ tin cậy AI chưa đạt ngưỡng tự động duyệt (${Math.round(lowestConf * 100)}% < ${Math.round(threshold * 100)}%)`,
          reason: assessment.reason || assessment.self_review?.reason || `Độ tin cậy phân tích chưa đạt ngưỡng ${Math.round(threshold * 100)}% để hệ thống tự động chấp nhận.`,
          badgeType: 'warning' as const,
        };
      }

      if (assessment.self_review?.issues && assessment.self_review.issues.length > 0) {
        return {
          title: 'AI tự rà soát phát hiện vấn đề',
          reason: assessment.self_review.issues.join('; '),
          badgeType: 'warning' as const,
        };
      }

      if (assessment.reason) {
        return {
          title: 'Kết quả phân tích AI',
          reason: assessment.reason,
          badgeType: 'info' as const,
        };
      }
    }

    // 3. Kiểm tra các cảnh báo từ hệ thống luật (Rule Check Findings)
    if (visibleRuleChecks?.findings && visibleRuleChecks.findings.length > 0) {
      const finding = visibleRuleChecks.findings.find(
        (f) => f.evidence_file_ids?.includes(fileId) || f.criterion_code === criterionCode || f.criterion_id === criterionId
      );
      if (finding) {
        return {
          title: `Quy tắc kiểm tra tự động cảnh báo (${finding.level === 'FLAGGED' ? 'Cần xem xét' : 'Thiếu dữ liệu'})`,
          reason: finding.message,
          badgeType: 'warning' as const,
        };
      }
    }

    // 4. Tiêu chí đặc thù theo quy chế (8a, 8b, 8c)
    if (['8a', '8b', '8c'].includes(criterionCode)) {
      return {
        title: 'Tiêu chí đặc thù bắt buộc BCS thẩm định',
        reason: 'Theo quy chế, mục khen thưởng / công tác cán bộ lớp bắt buộc Ban cán sự lớp trực tiếp thẩm định minh chứng.',
        badgeType: 'info' as const,
      };
    }

    // 5. Gợi ý điểm rà soát thủ công
    if (scoreSuggestions?.items) {
      const item = scoreSuggestions.items.find(
        (it) => it.criterion_code === criterionCode || it.evidence_file_ids?.includes(fileId)
      );
      if (item && item.status === 'REVIEW_REQUIRED' && item.reason) {
        return {
          title: 'Hệ thống yêu cầu rà soát thủ công',
          reason: item.reason,
          badgeType: 'warning' as const,
        };
      }
    }

    // 6. AI đang phân tích
    if (aiPending) {
      return {
        title: 'Đang phân tích tự động',
        reason: 'Hệ thống AI đang đọc tệp và đối chiếu quy chế...',
        badgeType: 'info' as const,
      };
    }

    // 7. Mặc định minh chứng cần thẩm định
    return {
      title: 'Minh chứng cần Ban cán sự thẩm định',
      reason: 'Minh chứng chưa đáp ứng điều kiện tự động chấp nhận (cần đối chiếu ngày diễn ra, đơn vị cấp hoặc thẩm quyền xác nhận).',
      badgeType: 'neutral' as const,
    };
  };

  const handleSaveEvidenceDecision = async (evidenceId: string, aiReason?: string) => {
    if (!caseData || evidenceRequestLock.current || isDemoMode) return;
    const decision = evidenceChoices[evidenceId];
    if (!decision) {
      setErrorMsg('Hãy chọn cách xử lý minh chứng trước khi lưu.');
      return;
    }

    // Tự động thiết lập lý do căn cứ hợp lệ cho backend theo quyết định của BCS và kết quả kiểm chứng
    let reason = '';
    if (decision === 'ACCEPT') {
      reason = 'BCS đã đối chiếu trực tiếp tệp gốc và xác nhận minh chứng phù hợp tiêu chí.';
    } else if (decision === 'REQUEST_SUPPLEMENT') {
      reason = aiReason
        ? `Yêu cầu bổ sung minh chứng do: ${aiReason}`
        : 'Yêu cầu sinh viên bổ sung minh chứng rõ ràng, hợp lệ theo quy chế.';
    } else if (decision === 'REJECT_ITEM') {
      reason = aiReason
        ? `Từ chối minh chứng theo kết quả kiểm chứng: ${aiReason}`
        : 'Từ chối tệp minh chứng không hợp lệ theo quy chế.';
    } else if (decision === 'HOLD') {
      reason = 'BCS tạm giữ tệp minh chứng để liên hệ đơn vị cấp hoặc GVCN xác minh thêm.';
    } else {
      reason = 'BCS đã rà soát và lưu quyết định xử lý minh chứng.';
    }

    evidenceRequestLock.current = true;
    setSavingEvidenceId(evidenceId);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const result = await api.put<{ score_adjustment?: EvidenceScoreAdjustment | null }>(`/bcs/cases/${caseData.id}/evidence/${evidenceId}/decision`, {
        decision, reason, expected_version: caseData.version,
      });
      await loadCase(decision !== 'REQUEST_SUPPLEMENT');
      const adjustment = result.score_adjustment;
      if (adjustment) {
        // Refresh only the affected criterion; preserve drafts for other items.
        setScores((previous) => ({ ...previous, [adjustment.criterion_id]: adjustment.approved_score }));
        setReasons((previous) => ({ ...previous, [adjustment.criterion_id]: adjustment.bcs_reason }));
      }
      setSuccessMsg(adjustment
        ? 'Đã từ chối toàn bộ minh chứng của tiêu chí và tự lưu điểm duyệt về 0. Tổng điểm đã được cập nhật.'
        : decision === 'REQUEST_SUPPLEMENT'
        ? 'Đã gửi yêu cầu bổ sung minh chứng cho sinh viên.'
        : 'Đã lưu quyết định của BCS cho minh chứng.');
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
    const isSystem = isSystemCriterion(claim.criterion);
    if (isSystem) {
      setErrorMsg(`Tiêu chí [${claim.criterion.code}] do Nhà trường tự động quy đổi từ kết quả học tập, Ban cán sự không tự chỉnh sửa.`);
      return;
    }
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

  const handleSaveAllClaims = async () => {
    if (!caseData || caseData.status !== 'BCS_REVIEW' || saveAllScoresLock.current) return;
    const items = [];
    for (const claim of caseData.claims) {
      const isSystem = isSystemCriterion(claim.criterion);
      const approvedScore = (scores[claim.criterion.id] || '').trim();
      const reason = (reasons[claim.criterion.id] || '').trim();
      const scoreNum = Number(approvedScore);
      const maxNum = claim.criterion.code === '8b'
        ? Math.min(Number(claim.criterion.max_score), 2)
        : Number(claim.criterion.max_score);
      if (!approvedScore || !Number.isFinite(scoreNum) || scoreNum < 0 || scoreNum > maxNum) {
        setErrorMsg(`Điểm tiêu chí [${claim.criterion.code}] phải từ 0 đến ${maxNum.toFixed(2)}.`);
        return;
      }
      if (!isSystem && claim.self_score !== null && scoreNum !== Number(claim.self_score) && !reason) {
        setErrorMsg(`Tiêu chí [${claim.criterion.code}] cần lý do vì điểm BCS khác điểm sinh viên tự khai.`);
        return;
      }
      const finalReason = isSystem
        ? (reason || claim.bcs_reason || 'Nhà trường tự động quy đổi từ kết quả học tập TBCHK')
        : (reason || null);
      items.push({ criterion_id: claim.criterion.id, approved_score: approvedScore, reason: finalReason });
    }

    saveAllScoresLock.current = true;
    setSavingAllScores(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      if (isDemoMode) {
        let version = caseData.version;
        for (const item of items) {
          version = staffStore.reviewClaim(caseData.id, item.criterion_id, item.approved_score, item.reason, version).version;
        }
      } else {
        await api.post(`/bcs/cases/${caseData.id}/claims/review-batch`, {
          items, expected_version: caseData.version,
        });
      }
      await loadCase();
      setSuccessMsg(`Đã lưu điểm BCS cho ${items.length} tiêu chí. Hãy kiểm tra minh chứng cần kết luận trước khi hoàn tất.`);
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message
        || (err as { message?: string })?.message || 'Không lưu được toàn bộ điểm BCS. Hãy tải lại hồ sơ rồi thử lại.';
      setErrorMsg(msg);
    } finally {
      saveAllScoresLock.current = false;
      setSavingAllScores(false);
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
    if (aiPending && pendingEvidenceCount > 0) {
      return 'AI đang xét minh chứng. Hãy đợi kết quả trước khi hoàn tất hồ sơ; BCS có thể xem tệp và chuẩn bị điểm.';
    }
    if (pendingEvidenceCount > 0) {
      return `Còn ${pendingEvidenceCount} minh chứng được gắn cờ hoặc đã phân tích AI chưa có quyết định cuối cùng của BCS.`;
    }
    for (const claim of caseData.claims) {
      const isSystem = isSystemCriterion(claim.criterion);
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

      if (!isSystem && claim.self_score !== null && Number(claim.self_score) !== scoreNum && (!currentReason || !currentReason.trim())) {
        return `Tiêu chí [${claim.criterion.code}] có điểm duyệt khác điểm tự khai nhưng chưa có lý do.`;
      }
      if (claim.approved_score === null) {
        return `Tiêu chí [${claim.criterion.code}] chưa được lưu điểm duyệt. Hãy bấm “Lưu toàn bộ điểm BCS” trước khi hoàn tất.`;
      }
      if (Number(claim.approved_score) !== scoreNum ||
          (!isSystem && (claim.bcs_reason || '').trim() !== (currentReason || '').trim())) {
        return `Tiêu chí [${claim.criterion.code}] có thay đổi chưa lưu. Hãy bấm “Lưu toàn bộ điểm BCS” trước khi hoàn tất.`;
      }
    }
    return null;
  }, [caseData, scores, reasons, pendingEvidenceCount, aiPending]);

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
  const isReviewOpen = caseData.status === 'BCS_REVIEW';
  const canEditScores = isReviewOpen || !!caseData.draft_editable;
  const hasUnsavedScores = isReviewOpen && caseData.claims.some((claim) => {
    const isSystem = isSystemCriterion(claim.criterion);
    return (
      claim.approved_score === null ||
      Number(scores[claim.criterion.id]) !== Number(claim.approved_score) ||
      (!isSystem && (reasons[claim.criterion.id] || '').trim() !== (claim.bcs_reason || '').trim())
    );
  });

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

          {isReviewOpen && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowSupplementModal(true)}
              style={{ fontSize: '0.825rem' }}
            >
              Yêu cầu bổ sung
            </button>
          )}

          {isReviewOpen && (
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
      {!isReviewOpen && !isProposedOrBeyond && (
        <div className="student-alert student-alert-warning" role="status">
          <Info size={18} style={{ flexShrink: 0 }} />
          <span>
            {caseData.status === 'CLOSED_INCOMPLETE'
              ? 'Hồ sơ đã đóng vì chưa hoàn tất bổ sung. BCS chỉ có thể xem lại; không thể chấm điểm, kết luận minh chứng hoặc hoàn tất kiểm tra trên hồ sơ này.'
              : 'Hồ sơ chưa ở bước BCS kiểm tra. Các quyết định và điểm lớp hiện chỉ để xem.'}
          </span>
        </div>
      )}
      {isReviewOpen && pendingEvidenceCount > 0 && (
        <div className="student-alert student-alert-warning" role="status">
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <span style={{ flex: 1 }}>
            {aiPending
              ? 'AI đang xét minh chứng. Các tệp đạt điều kiện sẽ tự được chấp nhận; hãy đợi kết quả trước khi xử lý ngoại lệ.'
              : `Còn ${pendingEvidenceCount} minh chứng cần kết luận. Mở tệp ở vùng “Minh chứng gốc”, chọn hướng xử lý, nhập căn cứ rồi bấm “Lưu quyết định minh chứng”.`}
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
          {isReviewOpen && pendingEvidenceCount > 0 && (
            <p role="status" style={{ fontSize: '0.8rem', color: '#9a3412', marginBottom: '0.75rem' }}>
              {aiPending
                ? `AI đang xét ${pendingEvidenceCount} minh chứng. Tệp đạt điều kiện sẽ tự được chấp nhận; BCS chỉ cần kết luận các tệp còn lại.`
                : `Còn ${pendingEvidenceCount} minh chứng cần BCS kết luận trước khi hoàn tất hồ sơ.`}
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
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, fontSize: '0.85rem', color: '#0f172a', minWidth: 0, flex: 1 }}>
                      <FileText size={16} color="#0284c7" style={{ flexShrink: 0 }} />
                      <span
                        style={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          display: 'inline-block',
                          minWidth: 0,
                        }}
                        title={file.original_name}
                      >
                        {file.original_name}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.75rem', color: '#64748b', flexShrink: 0 }}>
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
                    const autoAccepted = caseData.auto_accepted_evidence?.find((item) => item.evidence_file_id === file.id);
                    const editable = isReviewOpen && !isDemoMode;
                    const aiReasonInfo = getAiVerificationReason(file.id, file.criterionCode, file.criterionId);

                    return (
                      <div style={{ borderTop: '1px solid #e2e8f0', marginTop: '0.5rem', paddingTop: '0.6rem', display: 'grid', gap: '0.45rem' }}>
                        {autoAccepted && (
                          <div
                            role="status"
                            style={{
                              padding: '0.5rem',
                              background: saved?.decision === 'REJECT_ITEM' ? '#fef2f2' : '#ecfdf5',
                              border: saved?.decision === 'REJECT_ITEM' ? '1px solid #fecaca' : '1px solid #a7f3d0',
                              borderRadius: '0.4rem',
                              color: saved?.decision === 'REJECT_ITEM' ? '#991b1b' : '#065f46',
                              fontSize: '0.78rem',
                            }}
                          >
                            {saved?.decision === 'REJECT_ITEM' ? 'BCS đã bác kết luận AI tạm chấp nhận' : 'AI tạm chấp nhận minh chứng'} (đối chiếu {(autoAccepted.confidence * 100).toFixed(0)}%, tự rà soát {(autoAccepted.self_confidence * 100).toFixed(0)}%; cả hai phải từ {(autoAccepted.threshold * 100).toFixed(0)}% trở lên). BCS chốt điểm và ghi lý do nếu bác kết luận AI.
                          </div>
                        )}

                        {!autoAccepted && (
                          <div
                            style={{
                              backgroundColor: aiReasonInfo.badgeType === 'danger' ? '#fef2f2' : '#fffbeb',
                              border: `1px solid ${aiReasonInfo.badgeType === 'danger' ? '#fecaca' : '#fde68a'}`,
                              borderLeft: `4px solid ${aiReasonInfo.badgeType === 'danger' ? '#ef4444' : '#f59e0b'}`,
                              borderRadius: '4px',
                              padding: '0.5rem 0.65rem',
                              fontSize: '0.78rem',
                            }}
                          >
                            <div
                              style={{
                                fontWeight: 700,
                                color: aiReasonInfo.badgeType === 'danger' ? '#991b1b' : '#92400e',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                marginBottom: '0.2rem',
                              }}
                            >
                              <AlertTriangle size={13} color={aiReasonInfo.badgeType === 'danger' ? '#dc2626' : '#d97706'} style={{ flexShrink: 0 }} />
                              <span>Lý do cần kiểm chứng (từ Hệ thống AI):</span>
                            </div>
                            <div style={{ color: aiReasonInfo.badgeType === 'danger' ? '#7f1d1d' : '#78350f', lineHeight: 1.45 }}>
                              <strong>{aiReasonInfo.title}:</strong> {aiReasonInfo.reason}
                            </div>
                          </div>
                        )}

                        {(required || saved || !autoAccepted) && (
                          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: required ? '#9a3412' : '#475569' }}>
                            {aiPending && required && !saved
                              ? 'Đang chờ AI xét minh chứng'
                              : <>{required && isReviewOpen ? 'Cần BCS kết luận' : 'Kết luận của BCS'}: {saved ? ({ ACCEPT: 'Chấp nhận', REQUEST_SUPPLEMENT: 'Đã yêu cầu bổ sung', REJECT_ITEM: 'Từ chối tệp', HOLD: 'Tạm giữ để xác minh' }[saved.decision]) : 'Chưa có'}</>}
                          </span>
                        )}

                        {saved && (
                          <p style={{ fontSize: '0.75rem', color: '#475569', margin: 0 }}>
                            Căn cứ đã lưu: {saved.reason}
                          </p>
                        )}

                        {editable && autoAccepted && !reconsiderEvidenceIds.includes(file.id) && (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => {
                              setReconsiderEvidenceIds((previous) => [...previous, file.id]);
                              setEvidenceChoices((previous) => ({ ...previous, [file.id]: 'REJECT_ITEM' }));
                            }}
                          >
                            {saved ? 'Sửa quyết định BCS' : 'BCS xem xét lại / bác kết luận AI'}
                          </button>
                        )}

                        {editable && !aiPending && (!autoAccepted || reconsiderEvidenceIds.includes(file.id)) && (
                          <>
                            <label htmlFor={`decision-${file.id}`} style={{ fontSize: '0.75rem', fontWeight: 600, color: '#334155' }}>
                              Hướng xử lý minh chứng
                            </label>
                            <select
                              id={`decision-${file.id}`}
                              value={evidenceChoices[file.id] || ''}
                              onChange={(event) => {
                                const decision = event.target.value;
                                setEvidenceChoices((prev) => ({ ...prev, [file.id]: decision }));
                              }}
                              disabled={savingEvidenceId !== null}
                              style={{
                                fontFamily: 'inherit',
                                fontSize: '0.8rem',
                                color: '#0f172a',
                                backgroundColor: '#ffffff',
                                border: '1px solid #cbd5e1',
                                borderRadius: '4px',
                                padding: '0.4rem 0.6rem',
                                width: '100%',
                              }}
                            >
                              <option value="">Chọn quyết định</option>
                              <option value="ACCEPT">Chấp nhận tệp</option>
                              <option value="REQUEST_SUPPLEMENT" disabled={caseData.rounds.proof >= caseData.rounds.proof_max}>
                                Yêu cầu sinh viên bổ sung
                              </option>
                              <option value="REJECT_ITEM">Từ chối tệp</option>
                              <option value="HOLD">Tạm giữ để xác minh</option>
                            </select>

                            <button
                              type="button"
                              className="btn btn-primary"
                              disabled={savingEvidenceId !== null || !evidenceChoices[file.id]}
                              onClick={() => void handleSaveEvidenceDecision(file.id, aiReasonInfo.reason)}
                              style={{
                                fontSize: '0.8rem',
                                padding: '0.4rem 0.75rem',
                              }}
                            >
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
                      {claim.self_score !== null ? `${claim.self_score} đ` : isSystemCriterion(claim.criterion) ? 'Hệ thống quy đổi' : 'Chưa nhập'}
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
              {isProposedOrBeyond ? `Tổng duyệt: ${calculatedProposedTotal} đ`
                : isReviewOpen ? `Tổng đang rà soát: ${calculatedProposedTotal} đ`
                : 'Điểm lớp: Chưa duyệt'}
            </span>
          </div>
          {isReviewOpen && <p role="status" style={{ color: '#64748b', fontSize: '0.8rem' }}>
            Điểm đang rà soát có thể được điền từ điểm sinh viên tự khai; chỉ trở thành điểm lớp sau khi BCS lưu từng mục và hoàn tất kiểm tra.
          </p>}
          {caseData.draft_editable && <p role="status" style={{ color: '#92400e', fontSize: '0.8rem' }}>
            Đang rà soát dự thảo sau họp BCS. Mọi điều chỉnh cần lý do và sẽ yêu cầu xác nhận lại bản dự thảo trước họp lớp.
          </p>}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1 }}>
            {caseData.claims.map((claim) => {
              const isSystem = isSystemCriterion(claim.criterion);
              const allRejected = claim.evidence.length > 0 && claim.evidence.every((file) =>
                caseData.evidence_decisions?.some((item) => item.evidence_file_id === file.id && item.decision === 'REJECT_ITEM'));
              const currentScore = scores[claim.criterion.id] || '';
              const currentReason = reasons[claim.criterion.id] || '';
              const isDiff = !isSystem && (isReviewOpen || isProposedOrBeyond) && claim.self_score !== null && claim.self_score !== currentScore;
              const isSaving = savingCriterionId === claim.criterion.id;
              const scoreHasUnsavedChanges = !isSystem && (claim.approved_score === null ||
                Number(currentScore) !== Number(claim.approved_score) ||
                currentReason.trim() !== (claim.bcs_reason || '').trim());

              return (
                <div
                  key={claim.criterion.id}
                  style={{
                    backgroundColor: isSystem ? '#f8fafc' : isDiff ? '#fffbeb' : '#f8fafc',
                    border: isSystem ? '1px dashed #cbd5e1' : isDiff ? '1px solid #fde68a' : '1px solid #e2e8f0',
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
                    {isSystem ? (
                      <span
                        style={{
                          fontSize: '0.72rem',
                          color: '#475569',
                          backgroundColor: '#e2e8f0',
                          padding: '0.15rem 0.5rem',
                          borderRadius: '4px',
                          fontWeight: 600,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                        }}
                      >
                        <Lock size={11} /> Nhà trường quy đổi
                      </span>
                    ) : isReviewOpen ? (
                      <span style={{ fontSize: '0.72rem', color: scoreHasUnsavedChanges ? '#9a3412' : '#047857' }}>
                        {claim.approved_score === null ? 'Chưa lưu quyết định BCS' : scoreHasUnsavedChanges ? 'Có thay đổi chưa lưu' : 'Đã lưu quyết định BCS'}
                      </span>
                    ) : null}
                    {!isSystem && caseData.draft_editable && (
                      <button
                        type="button"
                        disabled={isSaving || !canEditScores}
                        onClick={() => handleSaveClaim(claim.criterion.id)}
                        className="btn btn-secondary"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                        title="Lưu tiêu chí này"
                      >
                        <Save size={12} /> {isSaving ? 'Đang lưu...' : 'Lưu điều chỉnh'}
                      </button>
                    )}
                  </div>

                  {/* Quick Select Options for BCS (only if not system criterion) */}
                  {!isSystem && !allRejected && claim.criterion.rule_config?.options && canEditScores && (
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
                      {isSystem
                        ? 'Điểm kết quả học tập quy đổi (Tối đa 4.00):'
                        : isReviewOpen
                        ? 'Điểm BCS đang rà soát'
                        : isProposedOrBeyond
                        ? 'Điểm BCS đã duyệt'
                        : 'Điểm BCS chưa duyệt'}{' '}
                      {!isSystem && `(Tối đa ${claim.criterion.code === '8b' ? '2.00' : claim.criterion.max_score}):`}
                    </label>
                    <input
                      type="text"
                      disabled={isSystem || allRejected || !canEditScores}
                      readOnly={isSystem || allRejected}
                      value={currentScore}
                      onChange={(e) => {
                        if (isSystem) return;
                        setScores({
                          ...scores,
                          [claim.criterion.id]: e.target.value,
                        });
                      }}
                      style={{
                        width: '80px',
                        padding: '0.3rem 0.5rem',
                        borderRadius: '4px',
                        border: '1px solid #cbd5e1',
                        textAlign: 'right',
                        fontWeight: 700,
                        fontSize: '0.875rem',
                        color: isSystem ? '#64748b' : '#0f172a',
                        backgroundColor: isSystem ? '#f1f5f9' : '#ffffff',
                        cursor: isSystem ? 'not-allowed' : 'text',
                      }}
                      title={isSystem ? 'Tiêu chí do Nhà trường tự động quy đổi và thừa nhận sau khi lên hệ thống nhà trường' : undefined}
                    />
                  </div>

                  {/* Input Reason or System Notice */}
                  {isSystem ? (
                    <div
                      style={{
                        backgroundColor: '#f1f5f9',
                        borderRadius: '4px',
                        padding: '0.45rem 0.65rem',
                        fontSize: '0.75rem',
                        color: '#475569',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        border: '1px solid #e2e8f0',
                      }}
                    >
                      <Info size={14} color="#64748b" style={{ flexShrink: 0 }} />
                      <span>
                        Tiêu chí này do Nhà trường tự động thừa nhận điểm từ kết quả học tập (TBCHK). Ban cán sự không cần và không được chỉnh sửa.
                      </span>
                    </div>
                  ) : (isDiff || caseData.draft_editable) ? (
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
                            : 'Bắt buộc nhập lý do vì điểm duyệt khác tự khai...'
                        }
                        style={{
                          width: '100%',
                          padding: '0.35rem 0.6rem',
                          borderRadius: '4px',
                          border: canEditScores && !currentReason.trim() ? '1px solid #ef4444' : '1px solid #cbd5e1',
                          fontSize: '0.8rem',
                          fontFamily: 'inherit',
                        }}
                      />
                      {canEditScores && !currentReason.trim() && (
                        <div style={{ fontSize: '0.725rem', color: '#dc2626', marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <Info size={12} /> {caseData.draft_editable ? 'Bắt buộc ghi căn cứ điều chỉnh dự thảo.' : 'Bắt buộc nhập lý do khi điểm duyệt khác điểm sinh viên tự khai.'}
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
          {isReviewOpen && (
            <button type="button" className="btn btn-primary" onClick={() => void handleSaveAllClaims()}
              disabled={savingAllScores || !hasUnsavedScores}
              style={{ marginTop: '1rem', alignSelf: 'flex-end' }}>
              <Save size={16} /> {savingAllScores ? 'Đang lưu toàn bộ điểm...' : hasUnsavedScores ? 'Lưu toàn bộ điểm BCS' : 'Đã lưu toàn bộ điểm BCS'}
            </button>
          )}
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
