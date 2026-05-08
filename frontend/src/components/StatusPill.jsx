import React from 'react';
import { Loader2, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

export default function StatusPill({ status, error }) {
  const baseStyle = { 
    display: 'inline-flex', 
    alignItems: 'center', 
    gap: '6px', 
    padding: '6px 12px', 
    borderRadius: '999px', 
    fontSize: '13px', 
    fontWeight: '600',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  };

  if (status === 'queued' || status === 'starting') {
    return (
      <div style={{ ...baseStyle, backgroundColor: '#f1f5f9', color: '#64748b', border: '1px solid #e2e8f0' }}>
        <Clock size={14} /> Initializing Scan...
      </div>
    );
  }

  if (status === 'completed') {
    return (
      <div style={{ ...baseStyle, backgroundColor: '#ecfdf5', color: '#059669', border: '1px solid #a7f3d0' }}>
        <CheckCircle2 size={14} /> Scan Complete
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div style={{ ...baseStyle, backgroundColor: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca' }}>
        <AlertCircle size={14} /> {error || "Scan Failed"}
      </div>
    );
  }

  // Active working states (Scraping, Analyzing, Enriching)
  return (
    <div style={{ ...baseStyle, backgroundColor: '#f0f9ff', color: '#0284c7', border: '1px solid #bae6fd' }}>
      <Loader2 size={14} className="animate-spin" style={{ animation: 'spin 2s linear infinite' }} /> 
      {status.replace(/_/g, ' ')}
    </div>
  );
}