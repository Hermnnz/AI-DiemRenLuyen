import React from 'react';

interface LoadingPanelProps {
  label: string;
}

export const LoadingPanel: React.FC<LoadingPanelProps> = ({ label }) => (
  <div className="card ui-loading-panel" role="status" aria-label={label}>
    <span className="sr-only">{label}</span>
    <div className="ui-skeleton ui-skeleton-title" aria-hidden="true" />
    <div className="ui-skeleton ui-skeleton-line" aria-hidden="true" />
    <div className="ui-skeleton ui-skeleton-line short" aria-hidden="true" />
    <div className="ui-skeleton ui-skeleton-card" aria-hidden="true" />
  </div>
);

interface EmptyPanelProps {
  title: string;
  description: string;
  children?: React.ReactNode;
}

export const EmptyPanel: React.FC<EmptyPanelProps> = ({ title, description, children }) => (
  <div className="card ui-empty-panel" role="status">
    <h3>{title}</h3>
    <p>{description}</p>
    {children && <div className="ui-empty-actions">{children}</div>}
  </div>
);
