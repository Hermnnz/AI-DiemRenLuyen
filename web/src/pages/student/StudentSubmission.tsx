import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { StudentCurrentResponse, Criterion, Claim, RuleCheckResponse } from '../../api/types';
import { api } from '../../api/client';
import { studentService } from '../../components/student/studentService';
import { CriterionCard } from '../../components/student/CriterionCard';
import { StudentScenarioBar } from '../../components/student/StudentScenarioBar';
import { PrintEvaluationFormModal } from '../../components/PrintEvaluationFormModal';
import '../../components/student/studentStyles.css';
import {
  Save,
  Send,
  AlertTriangle,
  CheckCircle2,
  Lock,
  RefreshCw,
  Info,
  ArrowLeft,
  Printer,
  Files,
  Layers,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const StudentSubmission: React.FC = () => {
  const [data, setData] = useState<StudentCurrentResponse | null>(null);
  const [claimsMap, setClaimsMap] = useState<Record<string, { self_score: string | null; student_note: string | null }>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [showConfirm, setShowConfirm] = useState<boolean>(false);
  const [showPrintModal, setShowPrintModal] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'danger' | 'info'; text: string } | null>(null);
  const [ruleChecks, setRuleChecks] = useState<RuleCheckResponse | null>(null);
  const [ruleError, setRuleError] = useState<string | null>(null);
  const [criterionErrors, setCriterionErrors] = useState<Record<string, string>>({});
  const [missingEvidenceCodes, setMissingEvidenceCodes] = useState<string[]>([]);
  const submitLock = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setValidationError(null);
      setFeedbackMessage(null);
      const res = await studentService.getCurrent();
      setData(res);

      // Khởi tạo map claims để theo dõi chỉnh sửa
      const initMap: Record<string, { self_score: string | null; student_note: string | null }> = {};
      for (const cl of res.claims) {
        initMap[cl.criterion_id] = {
          self_score: cl.self_score,
          student_note: cl.student_note,
        };
      }
      setClaimsMap(initMap);
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string } };
      setFeedbackMessage({
        type: 'danger',
        text: errObj?.error?.message || 'Không thể tải dữ liệu tự chấm.',
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const evidenceSignature = data?.claims.map((claim) => claim.evidence.map((file) => file.id).join(',')).join('|');
  useEffect(() => {
    if (!data || studentService.getMode() === 'mock') {
      setRuleChecks(null);
      return;
    }
    void api.get<RuleCheckResponse>(`/student/cases/${data.case.id}/rule-checks`)
      .then((result) => { setRuleChecks(result); setRuleError(null); })
      .catch(() => setRuleError('Chưa tải được cảnh báo kiểm tra hồ sơ.'));
  }, [data?.case.id, data?.case.version, evidenceSignature]);

  // Kiểm tra quyền chỉnh sửa form
  const isEditable = useMemo(() => {
    if (!data) return false;
    const { status } = data.case;
    const editableStatuses = ['DRAFT', 'NEEDS_INFO', 'NEEDS_PROOF'];
    if (!editableStatuses.includes(status)) return false;

    // Kiểm tra hạn chót
    const now = new Date().getTime();
    if (status === 'DRAFT') {
      const deadline = new Date(data.campaign.submission_deadline_at).getTime();
      return now < deadline;
    } else {
      // NEEDS_INFO hoặc NEEDS_PROOF: kiểm tra hạn của yêu cầu bổ sung
      const activeSupplement = data.supplement_requests?.find((r) => !r.fulfilled_at);
      if (activeSupplement) {
        const suppDeadline = new Date(activeSupplement.deadline_at).getTime();
        return now < suppDeadline;
      }
    }
    return true;
  }, [data]);

  // Group criteria into sections
  const sectionGroups = useMemo(() => {
    if (!data) return [];
    const groups: {
      code: string;
      title: string;
      maxScore: number;
      criteria: Criterion[];
    }[] = [];

    const map: Record<string, { code: string; title: string; maxScore: number; criteria: Criterion[] }> = {};

    data.criteria.forEach((crit) => {
      const secCode = crit.section_code || 'DEFAULT';
      if (!map[secCode]) {
        map[secCode] = {
          code: secCode,
          title: crit.section_title || 'Tiêu chí đánh giá',
          maxScore: parseFloat(crit.section_max_score || crit.max_score || '0'),
          criteria: [],
        };
        groups.push(map[secCode]);
      }
      map[secCode].criteria.push(crit);
    });

    return groups;
  }, [data]);

  // Calculate section subtotals and grand claimed total (respecting section caps)
  const { sectionSubtotals, claimedTotal } = useMemo(() => {
    if (!data || sectionGroups.length === 0) return { sectionSubtotals: {}, claimedTotal: '0.00' };

    const subtotals: Record<string, { raw: number; capped: number; max: number }> = {};
    let totalCapped = 0;

    sectionGroups.forEach((grp) => {
      let rawSum = 0;
      grp.criteria.forEach((cr) => {
        const val = claimsMap[cr.id]?.self_score;
        if (val) {
          rawSum += parseFloat(val) || 0;
        }
      });
      const cappedSum = grp.maxScore > 0 ? Math.min(rawSum, grp.maxScore) : rawSum;
      subtotals[grp.code] = {
        raw: rawSum,
        capped: cappedSum,
        max: grp.maxScore,
      };
      totalCapped += cappedSum;
    });

    const finalTotal = Math.min(totalCapped, 100);
    return {
      sectionSubtotals: subtotals,
      claimedTotal: finalTotal.toFixed(2),
    };
  }, [data, sectionGroups, claimsMap]);

  // Tổng điểm tối đa
  const maxTotal = useMemo(() => {
    if (!data) return '0.00';
    if (sectionGroups.length > 1) {
      return '100.00';
    }
    const sum = data.criteria.reduce((acc, c) => acc + (parseFloat(c.max_score) || 0), 0);
    return sum.toFixed(2);
  }, [data, sectionGroups]);

  const handleClaimChange = (criterionId: string, selfScore: string | null, studentNote: string | null) => {
    setCriterionErrors((prev) => {
      if (!prev[criterionId]) return prev;
      const next = { ...prev };
      delete next[criterionId];
      return next;
    });
    setClaimsMap((prev) => ({
      ...prev,
      [criterionId]: {
        self_score: selfScore,
        student_note: studentNote,
      },
    }));
  };

  const handleFileUpload = async (criterionId: string, file: File) => {
    if (!data) return;
    try {
      await studentService.uploadEvidence(data.case.id, criterionId, file);
      // Tải lại dữ liệu để cập nhật danh sách evidence
      const updated = await studentService.getCurrent();
      setData(updated);
      setCriterionErrors((prev) => {
        if (!prev[criterionId]) return prev;
        const next = { ...prev };
        delete next[criterionId];
        return next;
      });
      setFeedbackMessage({
        type: 'success',
        text: `Đã tải lên tệp "${file.name}" thành công.`,
      });
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string } };
      throw errObj;
    }
  };

  const handleFileRemove = async (criterionId: string, fileId: string) => {
    if (!data) return;
    try {
      await studentService.removeEvidence(data.case.id, criterionId, fileId);
      const updated = await studentService.getCurrent();
      setData(updated);
      setFeedbackMessage({
        type: 'info',
        text: 'Đã xóa tệp minh chứng.',
      });
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string } };
      setFeedbackMessage({
        type: 'danger',
        text: errObj?.error?.message || 'Không thể xóa tệp.',
      });
    }
  };

  // Lưu nháp toàn bộ các tiêu chí đã sửa
  const handleSaveDraft = async () => {
    if (!data || !isEditable) return;
    setIsSaving(true);
    setValidationError(null);
    setFeedbackMessage(null);

    try {
      let currentVer = data.case.version;
      for (const crit of data.criteria) {
        if (crit.code === '4e') continue; // Bỏ qua tiêu chí hệ thống khóa
        const item = claimsMap[crit.id];
        if (item) {
          const res = await studentService.saveClaim(
            data.case.id,
            crit.id,
            item.self_score,
            item.student_note,
            currentVer
          );
          currentVer = res.version;
        }
      }

      const updated = await studentService.getCurrent();
      setData(updated);
      setFeedbackMessage({
        type: 'success',
        text: 'Đã lưu bản nháp thành công! (Phiên bản v' + updated.case.version + ')',
      });
    } catch (err: unknown) {
      const errObj = err as { error?: { code?: string; message?: string } };
      if (errObj?.error?.code === 'CASE_CHANGED') {
        setFeedbackMessage({
          type: 'danger',
          text: 'Hồ sơ đã được cập nhật từ nơi khác. Vui lòng bấm "Tải lại dữ liệu".',
        });
      } else {
        setFeedbackMessage({
          type: 'danger',
          text: errObj?.error?.message || 'Lỗi khi lưu nháp.',
        });
      }
    } finally {
      setIsSaving(false);
    }
  };

  // Kiểm tra trước khi mở hộp xác nhận nộp
  const handlePreSubmit = () => {
    if (!data || !isEditable) return;
    setValidationError(null);

    const unScored: string[] = [];
    const missingEvidence: string[] = [];
    const nextErrors: Record<string, string> = {};

    for (const crit of data.criteria) {
      // Bỏ qua tiêu chí do hệ thống khóa (4e)
      if (crit.code === '4e') continue;

      const claim = claimsMap[crit.id];
      if (!claim || claim.self_score === null || claim.self_score.trim() === '') {
        unScored.push(crit.code);
        nextErrors[crit.id] = 'Hãy nhập điểm tự chấm trước khi nộp hồ sơ.';
      } else {
        const num = Number(claim.self_score.trim());
        if (!Number.isFinite(num) || num < 0 || num > Number(crit.max_score)) {
          unScored.push(`${crit.code} (điểm không hợp lệ)`);
          nextErrors[crit.id] = 'Điểm phải từ 0 đến ' + crit.max_score + '.';
        }
      }

      // Kiểm tra minh chứng bắt buộc
      const originalClaim = data.claims.find((c) => c.criterion_id === crit.id);
      if (crit.requires_evidence && (!originalClaim || !originalClaim.evidence || originalClaim.evidence.length === 0)) {
        missingEvidence.push(crit.code);
      }
    }

    if (unScored.length > 0) {
      setCriterionErrors(nextErrors);
      setValidationError(`Vui lòng tự chấm điểm hợp lệ cho các tiêu chí: ${unScored.join(', ')}.`);
      return;
    }

    setCriterionErrors({});
    setMissingEvidenceCodes(missingEvidence);
    setShowConfirm(true);
  };

  // Xác nhận nộp hồ sơ
  const handleConfirmSubmit = async () => {
    if (!data || submitLock.current) return;
    submitLock.current = true;
    setShowConfirm(false);
    setIsSubmitting(true);
    setValidationError(null);
    setFeedbackMessage(null);

    try {
      let currentVer = data.case.version;
      for (const crit of data.criteria) {
        if (crit.code === '4e') continue;
        const item = claimsMap[crit.id];
        if (item) {
          const res = await studentService.saveClaim(
            data.case.id,
            crit.id,
            item.self_score,
            item.student_note,
            currentVer
          );
          currentVer = res.version;
        }
      }

      const submitRes = await studentService.submitCase(data.case.id, currentVer);
      const updated = await studentService.getCurrent();
      setData(updated);

      if (submitRes.status === 'NEEDS_INFO') {
        setFeedbackMessage({
          type: 'info',
          text: `Hồ sơ đã được tiếp nhận nhưng thiếu thông tin bắt buộc. Trạng thái hiện tại: Cần bổ sung thông tin (NEEDS_INFO). Vui lòng bổ sung trước hạn.`,
        });
      } else if (submitRes.status === 'CLOSED_INCOMPLETE') {
        setFeedbackMessage({
          type: 'danger',
          text: 'Hồ sơ đã đóng do chưa hoàn tất yêu cầu bổ sung. Hãy liên hệ Ban cán sự để được hướng dẫn.',
        });
      } else {
        setFeedbackMessage({
          type: 'success',
          text: 'Nộp hồ sơ thành công! Hồ sơ đã được chuyển đến Ban cán sự lớp kiểm tra.',
        });
      }
    } catch (err: unknown) {
      const errObj = err as { error?: { code?: string; message?: string } };
      if (errObj?.error?.code === 'CASE_CHANGED') {
        setFeedbackMessage({
          type: 'danger',
          text: 'Hồ sơ đã thay đổi từ trước. Vui lòng tải lại dữ liệu và thử lại.',
        });
      } else {
        setFeedbackMessage({
          type: 'danger',
          text: errObj?.error?.message || 'Có lỗi xảy ra khi nộp hồ sơ.',
        });
      }
    } finally {
      setIsSubmitting(false);
      submitLock.current = false;
    }
  };

  if (isLoading) {
    return (
      <div className="container" style={{ padding: '1.5rem' }}>
        <StudentScenarioBar onScenarioChange={loadData} />
        <div className="card" style={{ padding: '2rem' }}>
          <div className="skeleton-line" style={{ width: '50%', height: '1.5rem' }} />
          <div className="skeleton-line" style={{ width: '80%', height: '1rem' }} />
          <div style={{ marginTop: '2rem' }}>
            <div className="skeleton-line" style={{ height: '6rem' }} />
            <div className="skeleton-line" style={{ height: '6rem' }} />
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container" style={{ padding: '1.5rem' }}>
        <StudentScenarioBar onScenarioChange={loadData} />
        <div className="student-alert student-alert-danger" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '1rem' }}>
          <AlertTriangle size={20} />
          <div>
            <strong>Lỗi tải dữ liệu:</strong> {feedbackMessage?.text || 'Không thể tải hồ sơ rèn luyện.'}
            <div style={{ marginTop: '0.75rem' }}>
              <button className="btn btn-outline" onClick={loadData}>
                <RefreshCw size={14} style={{ marginRight: '0.5rem' }} /> Thử lại
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const { campaign, case: studentCase, criteria, claims, supplement_requests } = data;
  const activeSupplement = supplement_requests?.find((r) => !r.fulfilled_at);

  return (
    <div>
      {/* 1. Thanh kịch bản hỗ trợ kiểm thử */}
      <StudentScenarioBar onScenarioChange={loadData} />

      {/* 2. Header trang */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <Link to="/student" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem' }}>
              <ArrowLeft size={16} /> Quay lại bảng tin
            </Link>
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
            Biểu mẫu Tự đánh giá & Nộp minh chứng
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Hồ sơ phiên bản v{studentCase.version} • {campaign.title}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setShowPrintModal(true)}
            style={{ fontSize: '0.85rem' }}
          >
            <Printer size={15} /> Xem & In phiếu (A4)
          </button>

          <StatusBadge status={studentCase.status} />
          {studentCase.status === 'NEEDS_INFO' || studentCase.status === 'NEEDS_PROOF' ? (
            activeSupplement ? (
              <Deadline isoString={activeSupplement.deadline_at} label="Hạn bổ sung" />
            ) : null
          ) : (
            <Deadline isoString={campaign.submission_deadline_at} label="Hạn nộp" />
          )}
        </div>
      </div>

      {/* 3. Banner phản hồi / thông báo kết quả */}
      {feedbackMessage && (
        <div className={`student-alert student-alert-${feedbackMessage.type}`}>
          {feedbackMessage.type === 'success' && <CheckCircle2 size={18} style={{ flexShrink: 0 }} />}
          {feedbackMessage.type === 'danger' && <AlertTriangle size={18} style={{ flexShrink: 0 }} />}
          {feedbackMessage.type === 'info' && <Info size={18} style={{ flexShrink: 0 }} />}
          <div style={{ flex: 1 }}>{feedbackMessage.text}</div>
        </div>
      )}

      {/* 4. Cảnh báo từ tầng kiểm tra bằng luật */}
      {(ruleError || (ruleChecks && ruleChecks.findings.length > 0)) && (
        <div
          style={{
            backgroundColor: '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: '6px',
            padding: '0.85rem 1rem',
            marginBottom: '1rem',
            color: '#92400e',
            fontSize: '0.875rem',
            display: 'flex',
            gap: '0.75rem',
            alignItems: 'flex-start',
          }}
        >
          <Files size={18} style={{ flexShrink: 0, marginTop: '2px' }} color="#d97706" />
          <div>
            <strong>Kiểm tra hồ sơ bằng luật:</strong>
            {ruleError && <div>{ruleError}</div>}
            <ul style={{ margin: '0.35rem 0 0 1.2rem', padding: 0 }}>
              {ruleChecks?.findings.map((finding, i) => (
                <li key={`${finding.code}-${i}`}>
                  {finding.criterion_code && <strong>[{finding.criterion_code}] </strong>}{finding.message}
                </li>
              ))}
            </ul>
            <div style={{ fontSize: '0.8rem', marginTop: '0.35rem', color: '#b45309' }}>
              Đây là cảnh báo để kiểm tra, không tự thay đổi điểm hoặc loại minh chứng.
            </div>
          </div>
        </div>
      )}

      {/* 5. Banner cảnh báo nếu form bị khóa không cho sửa */}
      {!isEditable && (
        <div className="student-alert student-alert-info">
          <Lock size={18} style={{ flexShrink: 0 }} />
          <div>
            <strong>Biểu mẫu đang ở chế độ xem:</strong>{' '}
            {studentCase.status === 'SUBMITTED' || studentCase.status === 'BCS_REVIEW'
              ? 'Hồ sơ đã được nộp và đang trong quá trình Ban cán sự kiểm tra. Bạn không thể chỉnh sửa lúc này.'
              : studentCase.status === 'PROPOSED' || studentCase.status === 'PUBLISHED'
              ? 'Điểm đánh giá đang được xét duyệt hoặc đã công bố. Vui lòng sang trang "Kết quả dự kiến" để xem chi tiết.'
              : studentCase.status.startsWith('CLOSED')
              ? 'Hồ sơ đã đóng, không còn hiệu lực chỉnh sửa.'
              : 'Đã quá thời hạn nộp hoặc hồ sơ không thuộc trạng thái cho phép chỉnh sửa.'}
          </div>
        </div>
      )}

      {/* 6. Cảnh báo lỗi xác thực */}
      {validationError && (
        <div className="student-alert student-alert-danger">
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <div>{validationError}</div>
        </div>
      )}

      {/* 7. Danh sách các tiêu chí đánh giá phân theo từng Điều (5 Mục) */}
      <div>
        {sectionGroups.map((group) => {
          const sub = sectionSubtotals[group.code] || { raw: 0, capped: 0, max: group.maxScore };
          const isOverCap = sub.raw > group.maxScore;

          return (
            <div key={group.code} style={{ marginBottom: '2rem' }}>
              {/* Section Header Card */}
              <div
                style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid #cbd5e1',
                  borderLeft: '4px solid #1e40af',
                  borderRadius: '6px',
                  padding: '0.85rem 1.25rem',
                  marginBottom: '1rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '0.75rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Layers size={18} color="#1e40af" />
                  <span style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>
                    {group.title}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.875rem' }}>
                  <div>
                    Tổng điểm mục:{' '}
                    <strong style={{ color: '#1e40af', fontSize: '1.05rem' }}>
                      {sub.capped.toFixed(2)}
                    </strong>{' '}
                    / {group.maxScore.toFixed(2)} điểm
                  </div>
                  {isOverCap && (
                    <span
                      style={{
                        fontSize: '0.75rem',
                        color: '#b45309',
                        backgroundColor: '#fef3c7',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        fontWeight: 600,
                      }}
                      title={`Tự chấm: ${sub.raw.toFixed(2)}đ. Điểm áp trần tối đa của mục là ${group.maxScore.toFixed(2)}đ`}
                    >
                      (Áp trần tối đa {group.maxScore}đ)
                    </span>
                  )}
                </div>
              </div>

              {/* Criteria in Section */}
              {group.criteria.map((crit) => {
                const claim = claims.find((c) => c.criterion_id === crit.id) || {
                  id: `temp-${crit.id}`,
                  criterion_id: crit.id,
                  self_score: null,
                  student_note: null,
                  approved_score: null,
                  bcs_reason: null,
                  evidence: [],
                };

                const suppReq = supplement_requests?.find(
                  (r) => !r.fulfilled_at && (r.criterion_id === crit.id || r.criterion_id === null)
                );

                return (
                  <CriterionCard
                    key={crit.id}
                    criterion={crit}
                    claim={claim}
                    supplementRequest={suppReq}
                    isEditable={isEditable}
                    onClaimChange={handleClaimChange}
                    onFileUpload={handleFileUpload}
                    onFileRemove={handleFileRemove}
                    submissionError={criterionErrors[crit.id]}
                    evidenceWarning={missingEvidenceCodes.includes(crit.code) && !claim.evidence?.length}
                  />
                );
              })}
            </div>
          );
        })}
      </div>

      {/* 8. Thanh tổng kết & Hành động (Sticky / Footer Card) */}
      <div className="card" style={{ marginTop: '1.5rem', position: 'sticky', bottom: '1rem', zIndex: 10 }}>
        <div className="student-action-bar" style={{ margin: 0, padding: 0, border: 'none' }}>
          <div>
            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Tổng điểm tự khai dự tính:</div>
            <div style={{ fontSize: '1.45rem', fontWeight: 700, color: '#1e40af' }}>
              {claimedTotal}{' '}
              <span style={{ fontSize: '0.95rem', color: '#64748b', fontWeight: 400 }}>
                / {maxTotal} điểm
              </span>
            </div>
          </div>

          <div className="btn-group" style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowPrintModal(true)}
              title="Xem và in phiếu tự đánh giá"
            >
              <Printer size={16} />
              <span>In phiếu</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleSaveDraft}
              disabled={!isEditable || isSaving || isSubmitting}
              title="Lưu lại điểm tự khai và ghi chú hiện tại"
            >
              <Save size={16} />
              <span>{isSaving ? 'Đang lưu...' : 'Lưu nháp'}</span>
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={handlePreSubmit}
              disabled={!isEditable || isSaving || isSubmitting}
              title="Gửi hồ sơ cho Ban cán sự lớp kiểm tra"
            >
              <Send size={16} />
              <span>
                {isSubmitting
                  ? 'Đang nộp...'
                  : studentCase.status === 'NEEDS_INFO' || studentCase.status === 'NEEDS_PROOF'
                  ? 'Nộp bổ sung'
                  : 'Nộp hồ sơ'}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* 9. Hộp thoại xác nhận nộp hồ sơ */}
      <ConfirmDialog
        isOpen={showConfirm}
        title="Xác nhận nộp hồ sơ rèn luyện"
        message={missingEvidenceCodes.length > 0
          ? 'Chưa có minh chứng bắt buộc ở tiêu chí ' + missingEvidenceCodes.join(', ') + '. Sau khi nộp, hồ sơ có thể chuyển sang trạng thái Cần bổ sung thông tin. Bạn có muốn tiếp tục?'
          : 'Sau khi nộp, hồ sơ sẽ được chuyển tới Ban cán sự lớp để kiểm tra. Bạn chỉ có thể sửa khi nhận yêu cầu bổ sung. Xác nhận nộp hồ sơ?'}
        confirmLabel="Xác nhận nộp hồ sơ"
        cancelLabel="Kiểm tra lại"
        isLoading={isSubmitting}
        onConfirm={handleConfirmSubmit}
        onCancel={() => setShowConfirm(false)}
      />

      {/* 10. Modal xem và in phiếu tự đánh giá A4 */}
      <PrintEvaluationFormModal
        isOpen={showPrintModal}
        onClose={() => setShowPrintModal(false)}
        campaignTitle={campaign.title}
        term={campaign.term}
        studentName="Sinh viên"
        studentCode="SV-CURRENT"
        criteria={criteria}
        claims={claims}
        claimedTotal={claimedTotal}
      />
    </div>
  );
};
