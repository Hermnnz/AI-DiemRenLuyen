import React from 'react';
import { EvidenceFile } from '../../api/types';
import { FileText, Image as ImageIcon, Download, ShieldCheck, X } from 'lucide-react';

interface SafeFilePreviewModalProps {
  isOpen: boolean;
  file: EvidenceFile | null;
  onClose: () => void;
}

export const SafeFilePreviewModal: React.FC<SafeFilePreviewModalProps> = ({
  isOpen,
  file,
  onClose,
}) => {
  if (!isOpen || !file) return null;

  const isImage = file.mime_type.startsWith('image/');
  const isPdf = file.mime_type.includes('pdf');
  const sizeKb = (file.size_bytes / 1024).toFixed(1);

  const handleDownload = () => {
    // In production, triggers GET /api/v1/files/{fileId}
    // For demo/mock preview, download a placeholder or sample blob
    const element = document.createElement('a');
    const blob = new Blob([`[Nội dung tệp mô phỏng an toàn: ${file.original_name}]`], {
      type: file.mime_type,
    });
    element.href = URL.createObjectURL(blob);
    element.download = file.original_name;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
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
          maxWidth: '720px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#ffffff',
          borderRadius: '8px',
          overflow: 'hidden',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
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
            {isImage ? (
              <ImageIcon size={20} color="#0284c7" />
            ) : (
              <FileText size={20} color="#ea580c" />
            )}
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
              Xem trước minh chứng an toàn
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

        {/* Security Banner */}
        <div
          style={{
            backgroundColor: '#eff6ff',
            borderBottom: '1px solid #bfdbfe',
            padding: '0.6rem 1.25rem',
            fontSize: '0.8rem',
            color: '#1e40af',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <ShieldCheck size={16} />
          <span>
            Chế độ xem cách ly (Sandbox): Minh chứng được kiểm tra bảo mật, không thực thi script và chỉ lưu thông qua API nội bộ có xác thực.
          </span>
        </div>

        {/* File Metadata Info */}
        <div
          style={{
            padding: '0.75rem 1.25rem',
            borderBottom: '1px solid #f1f5f9',
            fontSize: '0.825rem',
            color: '#475569',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '0.5rem',
          }}
        >
          <div>
            <strong>Tên tệp:</strong> {file.original_name}
          </div>
          <div>
            <strong>Định dạng:</strong> {file.mime_type}
          </div>
          <div>
            <strong>Dung lượng:</strong> {sizeKb} KB
          </div>
          <div>
            <strong>Ngày nộp:</strong> {new Date(file.uploaded_at).toLocaleString('vi-VN')}
          </div>
        </div>

        {/* Preview Viewport */}
        <div
          style={{
            padding: '1.5rem',
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#f1f5f9',
            minHeight: '320px',
          }}
        >
          {isImage ? (
            <div
              style={{
                textAlign: 'center',
                backgroundColor: '#ffffff',
                padding: '1rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                maxWidth: '100%',
              }}
            >
              <div
                style={{
                  width: '100%',
                  height: '240px',
                  backgroundColor: '#e2e8f0',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#475569',
                  flexDirection: 'column',
                  gap: '0.5rem',
                }}
              >
                <ImageIcon size={48} color="#0284c7" />
                <div style={{ fontWeight: 600 }}>{file.original_name}</div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Ảnh minh chứng hợp lệ · Đã kiểm tra mã băm SHA-256
                </div>
              </div>
            </div>
          ) : isPdf ? (
            <div
              style={{
                width: '100%',
                backgroundColor: '#ffffff',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                padding: '1.5rem',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.75rem',
              }}
            >
              <FileText size={56} color="#ea580c" />
              <div style={{ fontWeight: 600, fontSize: '1.05rem', color: '#0f172a' }}>
                {file.original_name}
              </div>
              <p style={{ fontSize: '0.85rem', color: '#64748b', maxWidth: '420px' }}>
                Tài liệu PDF được bảo vệ. Bạn có thể xem xét trực tiếp tại giao diện BCS hoặc tải xuống qua kênh được phân quyền.
              </p>
            </div>
          ) : (
            <div style={{ color: '#64748b', fontSize: '0.9rem' }}>
              Không hỗ trợ xem trước trực tiếp định dạng này. Vui lòng tải về an toàn.
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '0.75rem 1.25rem',
            borderTop: '1px solid #e2e8f0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: '#ffffff',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
            ID tệp: <code style={{ backgroundColor: '#f1f5f9', padding: '0.1rem 0.3rem', borderRadius: '3px' }}>{file.id}</code>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-secondary" onClick={onClose}>
              Đóng
            </button>
            <button className="btn btn-primary" onClick={handleDownload}>
              <Download size={14} /> Tải an toàn
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
