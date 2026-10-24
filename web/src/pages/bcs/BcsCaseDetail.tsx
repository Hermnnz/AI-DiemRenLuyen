import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { Deadline } from '../../components/Deadline';
import { SafeFilePreviewModal } from '../../components/staff/SafeFilePreviewModal';
import { SupplementRequestModal } from '../../components/staff/SupplementRequestModal';
import { api } from '../../api/client';
import { BcsCaseDetail as BcsCaseDetailType, EvidenceFile, SupplementKind } from '../../api/types';
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
} from 'lucide-react';

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

  // Modals state
  const [previewFile, setPreviewFile] = useState<EvidenceFile | null>(null);
  const [showSupplementModal, setShowSupplementModal] = useState<boolean>(false);
  const [showCompleteConfirm, setShowCompleteConfirm] = useState<boolean>(false);
  const [showHistory, setShowHistory] = useState<boolean>(false);

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
    } catch {
      // Fallback to staffStore mock
      const mockCase = staffStore.getCaseDetail(id);
      if (mockCase) {
        setCaseData(mockCase);
        initFormStates(mockCase);
      } else {
        setErrorMsg('Không tìm thấy dữ liệu hồ sơ yêu cầu.');
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
  };

  useEffect(() => {
    loadCase();
  }, [id]);

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
    const maxNum = parseFloat(claim.criterion.max_score);

    if (isNaN(scoreNum) || scoreNum < 0 || scoreNum > maxNum) {
      setErrorMsg(`Điểm duyệt cho [${claim.criterion.code}] phải từ 0.00 đến ${claim.criterion.max_score}.`);
      return;
    }

    if (claim.self_score !== approvedScore && !reason.trim()) {
      setErrorMsg(`Bắt buộc nhập lý do duyệt cho tiêu chí [${claim.criterion.code}] khi khác điểm tự khai (${claim.self_score}).`);
      return;
    }

    try {
      setSavingCriterionId(criterionId);
      try {
        await api.put(`/bcs/cases/${caseData.id}/claims/${criterionId}/review`, {
          approved_score: approvedScore,
          reason: reason.trim() ? reason.trim() : null,
          expected_version: caseData.version,
        });
      } catch {
        // Fallback to staffStore mock
        staffStore.reviewClaim(
          caseData.id,
          criterionId,
          approvedScore,
          reason.trim() ? reason.trim() : null,
          caseData.version
        );
      }

      setSuccessMsg(`Đã lưu quyết định chấm tiêu chí [${claim.criterion.code}].`);
      await loadCase();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string } })?.error?.message || 'Lỗi khi lưu điểm tiêu chí.';
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
      try {
        await api.post(`/bcs/cases/${caseData.id}/supplement-requests`, {
          kind,
          criterion_id: criterionId,
          reason,
          expected_version: caseData.version,
        });
      } catch {
        staffStore.createSupplementRequest(caseData.id, kind, criterionId, reason, caseData.version);
      }
      setSuccessMsg(`Đã gửi yêu cầu bổ sung ${kind === 'INFO' ? 'thông tin' : 'minh chứng'} đến sinh viên.`);
      await loadCase();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string } })?.error?.message || 'Lỗi khi tạo yêu cầu bổ sung.';
      setErrorMsg(msg);
      throw err;
    }
  };

  // Check if complete review is valid
  const validationError = useMemo(() => {
    if (!caseData) return null;
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
  }, [caseData, scores, reasons]);

  // Handle complete review
  const handleCompleteReview = async () => {
    if (!caseData) return;
    if (validationError) {
      setErrorMsg(validationError);
      return;
    }

    try {
      try {
        await api.post(`/bcs/cases/${caseData.id}/complete-review`, {
          expected_version: caseData.version,
        });
      } catch {
        staffStore.completeReview(caseData.id, caseData.version);
      }
      setShowCompleteConfirm(false);
      setSuccessMsg('Đã hoàn tất kiểm tra hồ sơ và chuyển sang trạng thái ĐÃ DUYỆT ĐIỂM DỰ KIẾN (PROPOSED).');
      await loadCase();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string } })?.error?.message || 'Lỗi khi hoàn tất kiểm tra hồ sơ.';
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
                  <div style={{ fontWeight: 600, color: '#0f172a' }}>
                    [{claim.criterion.code}] {claim.criterion.title}
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
                      disabled={isSaving || isProposedOrBeyond}
                      onClick={() => handleSaveClaim(claim.criterion.id)}
                      className="btn btn-secondary"
                      style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      title="Lưu tiêu chí này"
                    >
                      <Save size={12} /> {isSaving ? '...' : 'Lưu'}
                    </button>
                  </div>

                  {/* Input Score */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={{ fontSize: '0.8rem', color: '#475569', fontWeight: 500 }}>
                      Điểm được duyệt (Tối đa {claim.criterion.max_score}):
                    </label>
                    <input
                      type="text"
                      disabled={isProposedOrBeyond}
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
                      disabled={isProposedOrBeyond}
                      value={currentReason}
                      onChange={(e) =>
                        setReasons({
                          ...reasons,
                          [claim.criterion.id]: e.target.value,
                        })
                      }
                      placeholder={
                        isDiff
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
                    {isDiff && !currentReason.trim() && (
                      <div style={{ fontSize: '0.725rem', color: '#dc2626', marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <Info size={12} /> Bắt buộc nhập lý do khi điểm duyệt khác điểm sinh viên tự khai.
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
    </div>
  );
};
