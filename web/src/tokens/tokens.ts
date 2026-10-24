export const tokens = {
  colors: {
    primary: '#1e40af', // Blue 800
    primaryHover: '#1d4ed8',
    background: '#f8fafc',
    surface: '#ffffff',
    border: '#e2e8f0',
    textMain: '#0f172a',
    textMuted: '#64748b',

    // Status colors
    status: {
      success: {
        bg: '#ecfdf5',
        text: '#065f46',
        border: '#a7f3d0',
      },
      warning: {
        bg: '#fffbeb',
        text: '#92400e',
        border: '#fde68a',
      },
      danger: {
        bg: '#fef2f2',
        text: '#991b1b',
        border: '#fecaca',
      },
      info: {
        bg: '#eff6ff',
        text: '#1e40af',
        border: '#bfdbfe',
      },
      neutral: {
        bg: '#f1f5f9',
        text: '#475569',
        border: '#cbd5e1',
      },
    },
  },
  spacing: {
    sidebarWidth: '240px',
    contentMaxWidth: '1200px',
  },
};

export const STATUS_MAP: Record<string, { label: string; tone: 'success' | 'warning' | 'danger' | 'info' | 'neutral' }> = {
  // Campaign statuses
  DRAFT: { label: 'Bản nháp', tone: 'neutral' },
  SCHEDULED: { label: 'Đã lên lịch', tone: 'neutral' },
  OPEN: { label: 'Đang mở nộp', tone: 'warning' },
  REVIEW: { label: 'Đang kiểm tra', tone: 'info' },
  PUBLISHED: { label: 'Đã công bố điểm', tone: 'info' },
  FINALIZED: { label: 'Đã chốt chính thức', tone: 'success' },

  // Case statuses
  SUBMITTED: { label: 'Đã nộp — Chờ xử lý', tone: 'warning' },
  NEEDS_INFO: { label: 'Cần bổ sung thông tin', tone: 'warning' },
  BCS_REVIEW: { label: 'BCS đang kiểm tra', tone: 'info' },
  NEEDS_PROOF: { label: 'Cần bổ sung minh chứng', tone: 'warning' },
  PROPOSED: { label: 'Đã duyệt điểm dự kiến', tone: 'info' },
  ACCEPTED: { label: 'Sinh viên đã đồng ý', tone: 'success' },
  ACCEPTED_AUTO: { label: 'Tự động chấp nhận (quá hạn)', tone: 'success' },
  APPEALED: { label: 'Đang có khiếu nại', tone: 'warning' },
  RESOLVED: { label: 'Đã xử lý khiếu nại', tone: 'success' },
  CLOSED_INCOMPLETE: { label: 'Đóng — Không hoàn tất', tone: 'danger' },
  CLOSED_NO_SUBMIT: { label: 'Đóng — Không nộp', tone: 'danger' },
};
