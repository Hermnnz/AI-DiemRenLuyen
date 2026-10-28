import React from 'react';

interface DeadlineProps {
  isoString: string | null | undefined;
  label?: string;
  className?: string;
  kind?: 'deadline' | 'start';
}

export const Deadline: React.FC<DeadlineProps> = ({ isoString, label = 'Hạn chót', className = '', kind = 'deadline' }) => {
  if (!isoString) {
    return <span className={`text-muted ${className}`}>—</span>;
  }

  const date = new Date(isoString);
  const now = new Date();
  const isExpired = kind === 'deadline' && date.getTime() <= now.getTime();

  // Format to dd/MM/yyyy HH:mm in Vietnam time (UTC+7)
  const formatter = new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

  const formattedDate = formatter.format(date);

  return (
    <span
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        color: isExpired ? '#dc2626' : '#1e293b',
        fontWeight: isExpired ? 600 : 400,
        fontSize: '0.875rem',
      }}
      title={`Giờ Việt Nam (UTC+7): ${formattedDate}`}
    >
      <span>{label}:</span>
      <span>{formattedDate}</span>
      {isExpired && (
        <span
          style={{
            fontSize: '0.75rem',
            backgroundColor: '#fee2e2',
            color: '#b91c1c',
            padding: '0.1rem 0.35rem',
            borderRadius: '4px',
            marginLeft: '0.25rem',
          }}
        >
          (Đã hết hạn)
        </span>
      )}
    </span>
  );
};
