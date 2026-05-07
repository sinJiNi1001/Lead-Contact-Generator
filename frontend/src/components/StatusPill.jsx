import React from 'react';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

const STATUS_MAP = {
  queued:          { label: 'Queued',                   bg: '#2a1f00', border: '#5a3e00', color: '#EF9F27' },
  scraping_google: { label: 'Scanning Google...',       bg: '#001a2e', border: '#003d6b', color: '#60b4f0' },
  analyzing_ai:    { label: 'AI grading leads...',      bg: '#1a0a2e', border: '#3d1a6b', color: '#a78bfa' },
  completed:       { label: 'Analysis complete',        bg: '#001a10', border: '#0F6E56', color: '#1D9E75' },
  failed:          { label: 'Failed',                   bg: '#1a0000', border: '#6b1a1a', color: '#f87171' },
};

export default function StatusPill({ status, error }) {
  if (!status || status === 'idle') return null;

  const cfg = STATUS_MAP[status] || {
    label: status.replace(/_/g, ' '),
    bg: '#001a10', border: '#0F6E56', color: '#1D9E75',
  };

  const isLoading = status !== 'completed' && status !== 'failed';

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '7px',
      padding: '5px 12px',
      borderRadius: '20px',
      background: cfg.bg,
      border: `1px solid ${cfg.border}`,
      color: cfg.color,
      fontSize: '11px',
      fontFamily: "'JetBrains Mono', monospace",
      fontWeight: '500',
      letterSpacing: '0.04em',
    }}>
      {status === 'completed' && <CheckCircle2 size={12} />}
      {status === 'failed'    && <AlertCircle size={12} />}
      {isLoading              && <Loader2 size={12} className="animate-spin" />}
      <span>{status === 'failed' && error ? `Error: ${error}` : cfg.label}</span>
    </div>
  );
}