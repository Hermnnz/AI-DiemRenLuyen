import React from 'react';
import { STATUS_MAP } from '../tokens/tokens';

interface StatusBadgeProps {
  status: string;
  customLabel?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, customLabel, className = '' }) => {
  const info = STATUS_MAP[status] || { label: status, tone: 'neutral' };
  const label = customLabel || info.label;

  return (
    <span className={`badge badge-${info.tone} ${className}`}>
      <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', backgroundColor: 'currentColor' }} />
      {label}
    </span>
  );
};
