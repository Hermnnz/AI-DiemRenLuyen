import React, { useState } from 'react';
import { Criterion, Claim, SupplementRequest } from '../../api/types';
import { EvidenceViewer } from './EvidenceViewer';
import { Upload, AlertCircle, CheckCircle2 } from 'lucide-react';

interface CriterionCardProps {
  criterion: Criterion;
  claim: Claim;
  supplementRequest?: SupplementRequest;
  isEditable: boolean;
  onClaimChange: (criterionId: string, selfScore: string | null, studentNote: string | null) => void;
  onFileUpload: (criterionId: string, file: File) => Promise<void>;
  onFileRemove: (criterionId: string, fileId: string) => Promise<void>;
}

export const CriterionCard: React.FC<CriterionCardProps> = ({
  criterion,
  claim,
  supplementRequest,
  isEditable,
  onClaimChange,
  onFileUpload,
  onFileRemove,
}) => {
  const [scoreInput, setScoreInput] = useState<string>(claim.self_score ?? '');
  const [noteInput, setNoteInput] = useState<string>(claim.student_note ?? '');
  const [scoreError, setScoreError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const maxScoreNum = parseFloat(criterion.max_score);

  const validateScore = (val: string): boolean => {
    if (val.trim() === '') {
      setScoreError(null);
      return true;
    }
    const num = parseFloat(val);
    if (isNaN(num)) {
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
    const val = e.target.value;
    setScoreInput(val);
    validateScore(val);
    onClaimChange(criterion.id, val.trim() === '' ? null : val.trim(), noteInput);
  };

  const handleScoreBlur = () => {
    if (scoreInput.trim() !== '') {
      const num = parseFloat(scoreInput);
      if (!isNaN(num) && num >= 0 && num <= maxScoreNum) {
        const formatted = num.toFixed(2);
        setScoreInput(formatted);
        onClaimChange(criterion.id, formatted, noteInput);
      }
    }
  };

  const handleNoteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setNoteInput(val);
    onClaimChange(criterion.id, scoreInput.trim() === '' ? null : scoreInput.trim(), val);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
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
      setIsUploading(true);
      await onFileUpload(criterion.id, file);
    } catch (err: unknown) {
      const errorObj = err as { error?: { message?: string } };
      setUploadError(errorObj?.error?.message || 'Lỗi khi tải tệp lên.');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const hasEvidence = claim.evidence && claim.evidence.length > 0;
  const isFlagged = !!supplementRequest;

  return (
    <div className={`criterion-card ${isFlagged ? 'flagged' : ''}`}>
      {/* 1. Tiêu đề và điểm tối đa */}
      <div className="criterion-header">
        <div className="criterion-title-group">
          <div>
            <span className="criterion-code-title">
              {criterion.code}: {criterion.title}
            </span>
            {criterion.requires_evidence && (
              <span
                style={{
                  fontSize: '0.75rem',
                  color: hasEvidence ? '#15803d' : '#b91c1c',
                  backgroundColor: hasEvidence ? '#f0fdf4' : '#fef2f2',
                  padding: '0.15rem 0.5rem',
                  borderRadius: '4px',
                  fontWeight: 600,
                  marginLeft: '0.5rem',
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

      {/* 3. Ô nhập liệu Điểm tự chấm & Ghi chú */}
      <div className="criterion-inputs-grid">
        <div className="form-group">
          <label className="form-label" htmlFor={`score-${criterion.id}`}>
            Điểm tự chấm
          </label>
          <input
            id={`score-${criterion.id}`}
            type="text"
            className="form-input"
            placeholder="0.00"
            value={scoreInput}
            onChange={handleScoreChange}
            onBlur={handleScoreBlur}
            disabled={!isEditable}
            style={{ fontWeight: 600, color: '#1e40af' }}
          />
          {scoreError && <span className="form-error-text">{scoreError}</span>}
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor={`note-${criterion.id}`}>
            Ghi chú giải trình (nếu có)
          </label>
          <input
            id={`note-${criterion.id}`}
            type="text"
            className="form-input"
            placeholder="Ví dụ: GPA 3.4/4.0; Tham gia chiến dịch tình nguyện..."
            value={noteInput}
            onChange={handleNoteChange}
            disabled={!isEditable}
          />
        </div>
      </div>

      {/* 4. Vùng quản lý tệp minh chứng */}
      <div className="evidence-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#475569' }}>
            Tệp minh chứng ({claim.evidence?.length || 0})
          </span>

          {isEditable && (
            <label
              className="btn btn-secondary"
              style={{
                padding: '0.3rem 0.75rem',
                fontSize: '0.8125rem',
                cursor: isUploading ? 'not-allowed' : 'pointer',
              }}
            >
              <Upload size={14} />
              <span>{isUploading ? 'Đang tải lên...' : 'Tải minh chứng'}</span>
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
    </div>
  );
};
