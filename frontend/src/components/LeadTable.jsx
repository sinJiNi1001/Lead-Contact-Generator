import React, { useState } from 'react';
import { Users, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import StatusPill from './StatusPill';

export default function LeadTable({ theme, results, jobStatus, jobId, error }) {
  const isWorking = jobId && jobStatus !== 'completed' && jobStatus !== 'failed';
  const [expandedIndex, setExpandedIndex] = useState(0); // Auto-expand the first result

  if (isWorking) {
    return (
      <div style={{ background: theme.card, border: `1px solid ${theme.border}`, borderRadius: '10px', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
        <StatusPill status={jobStatus} />
      </div>
    );
  }

  if (jobStatus === 'idle') {
    return (
      <div style={{ background: theme.card, border: `1px solid ${theme.border}`, borderRadius: '10px', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: theme.textMuted }}>
        Deploy AI to hunt for leads.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ fontSize: '14px', color: theme.textMuted, textTransform: 'uppercase', margin: 0 }}>Results ({results.length})</h2>
        <StatusPill status={jobStatus} error={error} />
      </div>

      {results.map((company, i) => {
        const isExpanded = expandedIndex === i;
        return (
          <div key={i} style={{ background: theme.card, border: `1px solid ${theme.border}`, borderRadius: '10px', overflow: 'hidden' }}>
            
            {/* COLLAPSIBLE HEADER */}
            <div onClick={() => setExpandedIndex(isExpanded ? -1 : i)} style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', background: isExpanded ? theme.inputBg : 'transparent' }}>
              <div>
                <h3 style={{ margin: '0 0 4px', fontSize: '16px', color: theme.text }}>{company.name}</h3>
                <a href={`https://${company.domain}`} target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: theme.primary, textDecoration: 'none' }} onClick={e => e.stopPropagation()}>
                  {company.domain}
                </a>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ textAlign: 'center' }}>
                  <span style={{ display: 'block', fontSize: '18px', fontWeight: 'bold', color: company.lead_score >= 80 ? theme.primary : '#EF9F27' }}>{company.lead_score}</span>
                  <span style={{ fontSize: '10px', color: theme.textMuted }}>SCORE</span>
                </div>
                {isExpanded ? <ChevronUp size={20} color={theme.textMuted} /> : <ChevronDown size={20} color={theme.textMuted} />}
              </div>
            </div>

            {/* COLLAPSIBLE BODY */}
            {isExpanded && (
              <div style={{ padding: '16px', borderTop: `1px solid ${theme.border}` }}>
                <p style={{ fontSize: '13px', color: theme.text, lineHeight: '1.5', background: theme.inputBg, padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
                  {company.reason}
                </p>

                {company.top_contacts?.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: '11px', color: theme.textMuted, textTransform: 'uppercase', marginBottom: '8px' }}>Key Executives</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      {company.top_contacts.map((c, idx) => (
                        <a key={idx} href={c.linkedin_url} target="_blank" rel="noreferrer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: theme.inputBg, border: `1px solid ${theme.border}`, borderRadius: '6px', textDecoration: 'none' }}>
                          <div style={{ overflow: 'hidden' }}>
                            <p style={{ margin: 0, fontSize: '13px', color: theme.text, fontWeight: 'bold', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{c.name}</p>
                            <p style={{ margin: 0, fontSize: '11px', color: theme.textMuted, whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{c.designation}</p>
                          </div>
                          <ExternalLink size={14} color={theme.primary} />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}