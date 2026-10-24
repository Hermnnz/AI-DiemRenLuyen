import React, { useState } from 'react';
import { Criterion, SupplementKind } from '../../api/types';
import { AlertTriangle, X } from 'lucide-react';

interface SupplementRequestModalProps {
  isOpen: boolean;
  criteria: Criterion[];
  currentInfoRound: number;
  maxInfoRounds: number;
  currentProofRound: number;
  maxProofRounds: number;
  onClose: () => void;
  onSubmit: (kind: SupplementKind, criterionId: string | null, reason: string) => Promise<void> | void;
}

export const SupplementRequestModal: React.FC<SupplementRequestModalProps> = ({
  isOpen,
  criteria,
  currentInfoRound,
  maxInfoRounds,
  currentProofRound,
  maxProofRounds,
  onClose,
  onSubmit,
}) => {
  const [kind, setKind] = useState<SupplementKind>('PROOF');
  const [criterionId, setCriterionId] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  if (!isOpen) return null;

  const isInfoLimitReached = currentInfoRound >= maxInfoRounds;
  const isProofLimitReached = currentProofRound >= maxProofRounds;
  const isSelectedKindExceeded = kind === 'INFO' ? isInfoLimitReached : isProofLimitReached;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (isSelectedKindExceeded) {
      setError(`Không thể gửi yêu cầu: Đã đạt giới hạn tối đa số lượt bổ sung ${kind === 'INFO' ? 'thông tin' : 'minh chứng'}.`);
      return;
    }

    if (!reason.trim()) {
      setError('Vui lòng nêu rõ lý do và nội dung cần sinh viên bổ sung.');
      return;
    }

    try {
      setSubmitting(true);
      await onSubmit(kind, criterionId ? criterionId : null, reason.trim());
      onClose();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string } })?.error?.message || 'Có lỗi xảy ra khi gửi yêu cầu.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '560px',
          backgroundColor: '#ffffff',
          borderRadius: '8px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
          padding: 0,
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1rem 1.25rem',
            borderBottom: '1px solid #e2e8f0',
            backgroundColor: '#f8fafc',
          }}
        >
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#0f172a' }}>
            Yêu cầu Sinh viên Bổ sung Hồ sơ
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: '#64748b',
              padding: '0.25rem',
            }}
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {error && (
            <div
              style={{
                backgroundColor: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#991b1b',
                padding: '0.65rem 0.85rem',
                borderRadius: '6px',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <AlertTriangle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* Loại yêu cầu */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: '#1e293b' }}>
              Loại bổ sung:
            </label>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <label
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.6rem 0.75rem',
                  border: kind === 'PROOF' ? '2px solid #1e40af' : '1px solid #cbd5e1',
                  borderRadius: '6px',
                  backgroundColor: kind === 'PROOF' ? '#eff6ff' : '#ffffff',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                }}
              >
                <input
                  type="radio"
                  name="kind"
                  value="PROOF"
                  checked={kind === 'PROOF'}
                  onChange={() => setKind('PROOF')}
                />
                <div>
                  <div>Bổ sung Minh chứng (PROOF)</div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    Đã dùng: {currentProofRound}/{maxProofRounds} lượt
                  </div>
                </div>
              </label>

              <label
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.6rem 0.75rem',
                  border: kind === 'INFO' ? '2px solid #1e40af' : '1px solid #cbd5e1',
                  borderRadius: '6px',
                  backgroundColor: kind === 'INFO' ? '#eff6ff' : '#ffffff',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                }}
              >
                <input
                  type="radio"
                  name="kind"
                  value="INFO"
                  checked={kind === 'INFO'}
                  onChange={() => setKind('INFO')}
                />
                <div>
                  <div>Bổ sung Thông tin (INFO)</div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    Đã dùng: {currentInfoRound}/{maxInfoRounds} lượt
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Tiêu chí liên quan */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: '#1e293b' }}>
              Tiêu chí liên quan (Tùy chọn):
            </label>
            <select
              value={criterionId}
              onChange={(e) => setCriterionId(e.target.value)}
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.85rem',
              }}
            >
              <option value="">-- Toàn bộ hồ sơ / Nhiều tiêu chí --</option>
              {criteria.map((c) => (
                <option key={c.id} value={c.id}>
                  [{c.code}] {c.title} (Tối đa {c.max_score} điểm)
                </option>
              ))}
            </select>
          </div>

          {/* Lý do và yêu cầu cụ thể */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: '#1e293b' }}>
              Nội dung yêu cầu bổ sung <span style={{ color: '#ef4444' }}>*</span>:
            </label>
            <textarea
              rows={4}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Ghi rõ lý do và hướng dẫn cụ thể (ví dụ: ảnh mờ cần chụp lại, thiếu bảng điểm có mộc đỏ, thông tin kê khai chưa rõ ràng...)"
              style={{
                width: '100%',
                padding: '0.6rem',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontFamily: 'inherit',
                resize: 'vertical',
              }}
            />
          </div>

          {isSelectedKindExceeded && (
            <div style={{ fontSize: '0.8rem', color: '#b91c1c', fontWeight: 500 }}>
              ⚠️ Đã đạt giới hạn trần số lượt cho loại bổ sung này. Hãy chọn loại khác hoặc hoàn tất kiểm tra dựa trên hồ sơ hiện có.
            </div>
          )}

          {/* Modal Actions */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '0.75rem',
              marginTop: '0.5rem',
              paddingTop: '0.75rem',
              borderTop: '1px solid #f1f5f9',
            }}
          >
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
              Hủy
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || isSelectedKindExceeded || !reason.trim()}
            >
              {submitting ? 'Đang gửi...' : 'Gửi yêu cầu bổ sung'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
