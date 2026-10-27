import React, { useRef, useState } from 'react';
import { Criterion, Claim, SupplementRequest } from '../../api/types';
import { EvidenceViewer } from './EvidenceViewer';
import { Upload, Loader2, AlertCircle, CheckCircle2, Lock, Info, Award } from 'lucide-react';

interface CriterionCardProps {
  criterion: Criterion;
  claim: Claim;
  supplementRequest?: SupplementRequest;
  isEditable: boolean;
  onClaimChange: (criterionId: string, selfScore: string | null, studentNote: string | null) => void;
  onFileUpload: (criterionId: string, file: File) => Promise<void>;
  onFileRemove: (criterionId: string, fileId: string) => Promise<void>;
  submissionError?: string;
  evidenceWarning?: boolean;
}

export const CriterionCard: React.FC<CriterionCardProps> = ({
  criterion,
  claim,
  supplementRequest,
  isEditable,
  onClaimChange,
  onFileUpload,
  onFileRemove,
  submissionError,
  evidenceWarning = false,
}) => {
  const isSystemLocked = criterion.code === '4e';
  const isCadreCriterion = ['8a', '8b', '8c'].includes(criterion.code);

  const [scoreInput, setScoreInput] = useState<string>(claim.self_score ?? '');
  const [noteInput, setNoteInput] = useState<string>(claim.student_note ?? '');
  const [scoreError, setScoreError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const uploadLock = useRef(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const maxScoreNum = parseFloat(criterion.max_score);

  const validateScore = (val: string): boolean => {
    if (val.trim() === '') {
      setScoreError(null);
      return true;
    }
    const num = Number(val.trim());
    if (!Number.isFinite(num)) {
      setScoreError('Điểm phải là chữ số hợp lệ.');
      return false;
    }
    if (num < 0) {
      setScoreError('Điểm tự chấm không được nhỏ hơn 0.');
      return false;
    }
    if (num > maxScoreNum) {
      setScoreError(`Điểm không được vượt quá tối đa ${criterion.max_score} điểm.`);
      return false;
    }
    setScoreError(null);
    return true;
  };

  const handleScoreChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isSystemLocked) return;
    const val = e.target.value;
    setScoreInput(val);
    validateScore(val);
    onClaimChange(criterion.id, val.trim() === '' ? null : val.trim(), noteInput);
  };

  const handleScoreBlur = () => {
    if (isSystemLocked) return;
    if (scoreInput.trim() !== '') {
      const num = Number(scoreInput.trim());
      if (Number.isFinite(num) && num >= 0 && num <= maxScoreNum) {
        const formatted = num.toFixed(2);
        setScoreInput(formatted);
        onClaimChange(criterion.id, formatted, noteInput);
      }
    }
  };

  const handleNoteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isSystemLocked) return;
    const val = e.target.value;
    setNoteInput(val);
    onClaimChange(criterion.id, scoreInput.trim() === '' ? null : scoreInput.trim(), val);
  };

  const handleSelectOption = (optScore: number, optLabel: string) => {
    if (!isEditable || isSystemLocked) return;
    const formatted = optScore.toFixed(2);
    setScoreInput(formatted);
    setScoreError(null);
    const newNote = noteInput.trim() ? noteInput : optLabel;
    if (!noteInput.trim()) setNoteInput(newNote);
    onClaimChange(criterion.id, formatted, newNote);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (uploadLock.current) return;
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setUploadError(null);

    // Validate client-side
    const validMimes = ['application/pdf', 'image/jpeg', 'image/png'];
    if (!validMimes.includes(file.type)) {
      setUploadError('Chỉ hỗ trợ tệp định dạng PDF, JPG hoặc PNG.');
      e.target.value = '';
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadError('Dung lượng tệp vượt quá giới hạn 10 MB.');
      e.target.value = '';
      return;
    }

    try {
      uploadLock.current = true;
      setIsUploading(true);
      await onFileUpload(criterion.id, file);
    } catch (err: unknown) {
      const errorObj = err as { error?: { message?: string } };
      setUploadError(errorObj?.error?.message || 'Lỗi khi tải tệp lên.');
    } finally {
      uploadLock.current = false;
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const hasEvidence = claim.evidence && claim.evidence.length > 0;
  const isFlagged = !!supplementRequest;
  const options = criterion.rule_config?.options;

  return (
    <div className={`criterion-card ${isFlagged ? 'flagged' : ''}`} style={{ marginBottom: '1.25rem' }}>
      {/* 1. Tiêu đề và điểm tối đa */}
      <div className="criterion-header">
        <div className="criterion-title-group">
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem' }}>
            <span className="criterion-code-title">
              {criterion.code}: {criterion.title}
            </span>

            {isSystemLocked && (
              <span
                style={{
                  fontSize: '0.75rem',
                  color: '#4338ca',
                  backgroundColor: '#e0e7ff',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <Lock size={12} /> Hệ thống quy đổi tự động (Khóa tự nhập)
              </span>
            )}

            {isCadreCriterion && (
              <span
                style={{
                  fontSize: '0.75rem',
                  color: '#b45309',
                  backgroundColor: '#fef3c7',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <Award size={12} /> Điểm tự khai sẽ được Ban cán sự xác minh
              </span>
            )}

            {criterion.requires_evidence && !isSystemLocked && (
              <span
                style={{
                  fontSize: '0.75rem',
                  color: hasEvidence ? '#15803d' : '#b91c1c',
                  backgroundColor: hasEvidence ? '#f0fdf4' : '#fef2f2',
                  padding: '0.15rem 0.5rem',
                  borderRadius: '4px',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                {hasEvidence ? (
                  <>
                    <CheckCircle2 size={12} />
                    <span>Đã có minh chứng</span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={12} />
                    <span>Bắt buộc minh chứng</span>
                  </>
                )}
              </span>
            )}
          </div>

          {criterion.description && (
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.25rem' }}>
              {criterion.description}
            </p>
          )}

          {criterion.evidence_notes && (
            <div
              style={{
                fontSize: '0.8rem',
                color: '#475569',
                backgroundColor: '#f8fafc',
                borderLeft: '3px solid #3b82f6',
                padding: '0.35rem 0.6rem',
                marginTop: '0.4rem',
                borderRadius: '0 4px 4px 0',
              }}
            >
              <strong>Yêu cầu minh chứng:</strong> {criterion.evidence_notes}
            </div>
          )}
        </div>

        <div className="criterion-max-badge">
          Tối đa: {criterion.max_score} điểm
        </div>
      </div>

      {/* 2. Cảnh báo yêu cầu bổ sung nếu có */}
      {supplementRequest && (
        <div className="student-alert student-alert-warning" style={{ margin: '0.75rem 0' }}>
          <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>Yêu cầu bổ sung (Lượt {supplementRequest.round_no}):</strong>{' '}
            {supplementRequest.reason}
          </div>
        </div>
      )}

      {/* 3. Trường hợp tiêu chí 4e (Khóa hệ thống) */}
      {isSystemLocked ? (
        <div
          style={{
            backgroundColor: claim.self_score !== null ? '#eff6ff' : '#f8fafc',
            border: claim.self_score !== null ? '1px solid #bfdbfe' : '1px dashed #cbd5e1',
            borderRadius: '6px',
            padding: '0.85rem 1rem',
            margin: '0.75rem 0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Lock size={16} color="#3b82f6" />
            <div>
              {claim.self_score !== null ? (
                <div>
                  <div style={{ fontWeight: 600, color: '#1e40af', fontSize: '0.95rem' }}>
                    Điểm quy đổi từ kết quả học tập: {claim.self_score} / {criterion.max_score} điểm
                  </div>
                  {claim.academic_gpa && (
                    <div style={{ fontSize: '0.825rem', color: '#475569', marginTop: '0.2rem' }}>
                      Điểm trung bình học kỳ (GPA): <strong>{claim.academic_gpa} / 4.0</strong>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ color: '#64748b', fontSize: '0.875rem' }}>
                  <span style={{ fontWeight: 600, color: '#0f172a' }}>Chưa có dữ liệu học tập từ Nhà trường.</span>{' '}
                  Điểm sẽ được cập nhật tự động khi Phòng Đào tạo nhập điểm GPA học kỳ (không tính là 0 điểm).
                </div>
              )}
            </div>
          </div>

          <div
            style={{
              fontSize: '0.75rem',
              color: '#64748b',
              backgroundColor: '#ffffff',
              border: '1px solid #e2e8f0',
              padding: '0.3rem 0.6rem',
              borderRadius: '4px',
            }}
          >
            Thang quy đổi: GPA 3.20–4.00 = 4đ | 2.00–3.19 = 2đ | &lt;2.00 = 0đ
          </div>
        </div>
      ) : (
        <>
          {/* Quick Option Select Buttons (nếu có định nghĩa mức điểm) */}
          {options && options.length > 0 && isEditable && (
            <div style={{ marginTop: '0.6rem', marginBottom: '0.6rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                Chọn nhanh mức điểm quy định:
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {options.map((opt, i) => {
                  const isSelected =
                    scoreInput !== '' && parseFloat(scoreInput) === opt.score;
                  return (
                    <button
                      key={i}
                      type="button"
                      onClick={() => handleSelectOption(opt.score, opt.label)}
                      style={{
                        padding: '0.25rem 0.6rem',
                        fontSize: '0.75rem',
                        fontWeight: isSelected ? 700 : 500,
                        backgroundColor: isSelected ? '#1e40af' : '#f1f5f9',
                        color: isSelected ? '#ffffff' : '#334155',
                        border: isSelected ? '1px solid #1e40af' : '1px solid #cbd5e1',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                      title={opt.note || opt.label}
                    >
                      {opt.label} ({opt.score}đ)
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Ô nhập liệu Điểm tự chấm & Ghi chú */}
          <div className="criterion-inputs-grid">
            <div className="form-group">
              <label className="form-label" htmlFor={`score-${criterion.id}`}>
                Điểm tự chấm
              </label>
              <input
                id={`score-${criterion.id}`}
                type="text"
                inputMode="decimal"
                className="form-input"
                placeholder="0.00"
                value={scoreInput}
                onChange={handleScoreChange}
                onBlur={handleScoreBlur}
                disabled={!isEditable}
                aria-invalid={Boolean(scoreError || submissionError)}
                aria-describedby={scoreError || submissionError ? 'score-error-' + criterion.id : undefined}
                style={{ fontWeight: 600, color: '#1e40af' }}
              />
              {(scoreError || submissionError) && (
                <span id={'score-error-' + criterion.id} className="form-error-text" role="alert">{scoreError || submissionError}</span>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor={`note-${criterion.id}`}>
                Ghi chú giải trình (nếu có)
              </label>
              <input
                id={`note-${criterion.id}`}
                type="text"
                className="form-input"
                placeholder="Ví dụ: Tham gia hoạt động X; Có chứng nhận..."
                value={noteInput}
                onChange={handleNoteChange}
                disabled={!isEditable}
              />
            </div>
          </div>

          {/* Vùng quản lý tệp minh chứng */}
          <div className="evidence-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#475569' }}>
                Tệp minh chứng ({claim.evidence?.length || 0})
              </span>

              {isEditable && (
                <label
                  className="btn btn-secondary"
                  aria-busy={isUploading}
                  style={{
                    padding: '0.3rem 0.75rem',
                    fontSize: '0.8125rem',
                    cursor: isUploading ? 'not-allowed' : 'pointer',
                    pointerEvents: isUploading ? 'none' : 'auto',
                  }}
                >
                  {isUploading ? <Loader2 size={14} className="upload-spinner" aria-hidden="true" /> : <Upload size={14} />}
                  <span role={isUploading ? 'status' : undefined}>{isUploading ? 'Đang tải lên...' : 'Tải minh chứng'}</span>
                  <input
                    type="file"
                    className="upload-file-input"
                    accept=".pdf,image/jpeg,image/png"
                    onChange={handleFileSelect}
                    disabled={isUploading}
                  />
                </label>
              )}
            </div>

            {uploadError && (
              <div className="student-alert student-alert-danger" style={{ marginTop: '0.5rem', padding: '0.5rem 0.75rem' }}>
                <AlertCircle size={16} />
                <span>{uploadError}</span>
              </div>
            )}
            {evidenceWarning && !uploadError && (
              <div className="student-alert student-alert-info" style={{ marginTop: '0.5rem', padding: '0.5rem 0.75rem' }}>
                <Info size={16} />
                <span>Tiêu chí này cần minh chứng. Tải tệp lên để tránh yêu cầu bổ sung sau khi nộp.</span>
              </div>
            )}

            {hasEvidence ? (
              <div className="evidence-files-list">
                {claim.evidence.map((file) => (
                  <EvidenceViewer
                    key={file.id}
                    evidence={file}
                    canRemove={isEditable}
                    onRemove={(fileId) => onFileRemove(criterion.id, fileId)}
                  />
                ))}
              </div>
            ) : (
              <div
                style={{
                  padding: '0.75rem',
                  backgroundColor: '#f8fafc',
                  borderRadius: '6px',
                  border: '1px dashed #cbd5e1',
                  textAlign: 'center',
                  fontSize: '0.8125rem',
                  color: '#94a3b8',
                  marginTop: '0.5rem',
                }}
              >
                Chưa có tệp minh chứng nào được đính kèm
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
