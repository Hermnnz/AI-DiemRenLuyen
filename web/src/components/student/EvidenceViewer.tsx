import React, { useState } from 'react';
import { EvidenceFile } from '../../api/types';
import { FileText, Image as ImageIcon, Trash2, Download } from 'lucide-react';

interface EvidenceViewerProps {
  evidence: EvidenceFile;
  canRemove?: boolean;
  onRemove?: (fileId: string) => Promise<void>;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  evidence,
  canRemove = false,
  onRemove,
}) => {
  const [isRemoving, setIsRemoving] = useState(false);
  const isImage = evidence.mime_type.startsWith('image/');
  const sizeFormatted = (evidence.size_bytes / 1024).toFixed(1) + ' KB';

  const formatVnTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return new Intl.DateTimeFormat('vi-VN', {
        timeZone: 'Asia/Ho_Chi_Minh',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(d);
    } catch {
      return isoString;
    }
  };

  return (
    <div className="evidence-item">
      <div className="evidence-info">
        {isImage ? (
          <ImageIcon size={18} color="#0284c7" />
        ) : (
          <FileText size={18} color="#dc2626" />
        )}
        <div>
          <a
            href={`/api/v1/files/${evidence.id}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontWeight: 500, fontSize: '0.875rem', color: '#1e40af' }}
            title="Nhấn để xem hoặc tải tệp minh chứng"
          >
            {evidence.original_name}
          </a>
          <div className="evidence-meta">
            {sizeFormatted} • Tải lên: {formatVnTime(evidence.uploaded_at)}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <a
          href={`/api/v1/files/${evidence.id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-secondary"
          style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
          title="Tải tệp"
        >
          <Download size={14} />
          <span>Tải về</span>
        </a>

        {canRemove && onRemove && (
          <button
            type="button"
            onClick={async () => {
              if (isRemoving) return;
              setIsRemoving(true);
              try {
                await onRemove(evidence.id);
              } finally {
                setIsRemoving(false);
              }
            }}
            disabled={isRemoving}
            className="btn btn-secondary"
            style={{
              padding: '0.2rem 0.5rem',
              fontSize: '0.75rem',
              color: '#dc2626',
              borderColor: '#fca5a5',
            }}
            title="Xóa tệp minh chứng"
          >
            <Trash2 size={14} />
            <span>{isRemoving ? 'Đang xóa...' : 'Xóa'}</span>
          </button>
        )}
      </div>
    </div>
  );
};
