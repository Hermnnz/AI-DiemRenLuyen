import React, { useState } from 'react';
import { Meeting, MeetingKind } from '../../api/types';
import { Calendar, X, AlertTriangle } from 'lucide-react';

interface MeetingRecordModalProps {
  isOpen: boolean;
  initialKind: MeetingKind;
  existingMeeting?: Meeting;
  onClose: () => void;
  onSubmit: (kind: MeetingKind, heldAt: string, note: string | null) => Promise<void> | void;
}

export const MeetingRecordModal: React.FC<MeetingRecordModalProps> = ({
  isOpen,
  initialKind,
  existingMeeting,
  onClose,
  onSubmit,
}) => {
  const [kind, setKind] = useState<MeetingKind>(initialKind);
  const [heldAt, setHeldAt] = useState<string>(
    existingMeeting?.held_at
      ? new Date(existingMeeting.held_at).toISOString().slice(0, 16)
      : new Date().toISOString().slice(0, 16)
  );
  const [note, setNote] = useState<string>(existingMeeting?.note || '');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!heldAt) {
      setError('Vui lòng chọn thời gian diễn ra cuộc họp.');
      return;
    }

    try {
      setSubmitting(true);
      const isoUtc = new Date(heldAt).toISOString();
      await onSubmit(kind, isoUtc, note.trim() ? note.trim() : null);
      onClose();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string } })?.error?.message || 'Có lỗi xảy ra khi lưu biên bản họp.';
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
          maxWidth: '520px',
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Calendar size={18} color="#1e40af" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#0f172a' }}>
              {existingMeeting ? 'Cập nhật' : 'Ghi nhận'} Biên bản Họp Bình xét
            </h3>
          </div>
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

          {/* Chọn loại cuộc họp */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: '#1e293b' }}>
              Loại cuộc họp:
            </label>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <label
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 0.75rem',
                  border: kind === 'BCS' ? '2px solid #1e40af' : '1px solid #cbd5e1',
                  borderRadius: '6px',
                  backgroundColor: kind === 'BCS' ? '#eff6ff' : '#ffffff',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                }}
              >
                <input
                  type="radio"
                  name="meetingKind"
                  value="BCS"
                  checked={kind === 'BCS'}
                  onChange={() => setKind('BCS')}
                />
                <span>1. Họp Ban cán sự</span>
              </label>

              <label
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 0.75rem',
                  border: kind === 'CLASS' ? '2px solid #1e40af' : '1px solid #cbd5e1',
                  borderRadius: '6px',
                  backgroundColor: kind === 'CLASS' ? '#eff6ff' : '#ffffff',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                }}
              >
                <input
                  type="radio"
                  name="meetingKind"
                  value="CLASS"
                  checked={kind === 'CLASS'}
                  onChange={() => setKind('CLASS')}
                />
                <span>2. Họp toàn thể Lớp</span>
              </label>
            </div>
          </div>

          {/* Thời gian họp */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: '#1e293b' }}>
              Thời gian diễn ra <span style={{ color: '#ef4444' }}>*</span>:
            </label>
            <input
              type="datetime-local"
              value={heldAt}
              onChange={(e) => setHeldAt(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.85rem',
              }}
            />
          </div>

          {/* Ghi chú biên bản */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: '#1e293b' }}>
              Nội dung biên bản tóm tắt / Nghị quyết cuộc họp:
            </label>
            <textarea
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Ví dụ: Lớp đã họp biểu quyết nhất trí 100% đối với bảng tổng hợp điểm dự kiến, có sự tham dự của GVCN."
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

          {/* Actions */}
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
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Đang lưu...' : 'Lưu biên bản họp'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
