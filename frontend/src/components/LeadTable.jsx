import React, { useEffect, useRef } from 'react';
import { Users, ExternalLink, Brain, TrendingUp } from 'lucide-react';
import StatusPill from './StatusPill';

/* ── Score ring ── */
function ScoreRing({ score }) {
  const ref = useRef(null);
  const color = score >= 80 ? '#1D9E75' : score >= 60 ? '#EF9F27' : '#E24B4A';
  const SIZE = 64, R = 26, CX = 32, CY = 32, SW = 5;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let prog = 0;
    const target = score / 100;
    const step = target / 35;

    function draw() {
      ctx.clearRect(0, 0, SIZE, SIZE);
      // track
      ctx.beginPath(); ctx.arc(CX, CY, R, 0, Math.PI * 2);
      ctx.strokeStyle = '#1a2e24'; ctx.lineWidth = SW; ctx.stroke();
      // fill
      ctx.beginPath(); ctx.arc(CX, CY, R, -Math.PI / 2, -Math.PI / 2 + prog * Math.PI * 2);
      ctx.strokeStyle = color; ctx.lineWidth = SW; ctx.lineCap = 'round'; ctx.stroke();
      if (prog < target) { prog = Math.min(prog + step, target); requestAnimationFrame(draw); }
    }
    requestAnimationFrame(draw);
  }, [score]);

  return (
    <div style={{ position: 'relative', width: SIZE, height: SIZE, flexShrink: 0 }}>
      <canvas ref={ref} width={SIZE} height={SIZE} />
      <span style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '14px', fontWeight: '700',
        fontFamily: "'JetBrains Mono', monospace",
        color,
      }}>{score}</span>
    </div>
  );
}

/* ── Signal tag ── */
function Tag({ label }) {
  return (
    <span style={{
      fontSize: '10px',
      fontFamily: "'JetBrains Mono', monospace",
      padding: '3px 9px',
      borderRadius: '4px',
      background: '#041a0f',
      border: '1px solid #0F6E56',
      color: '#5DCAA5',
      letterSpacing: '0.04em',
      whiteSpace: 'nowrap',
    }}>{label}</span>
  );
}

/* ── Contact card ── */
function ContactCard({ contact }) {
  const initials = contact.name === 'Unknown'
    ? '?'
    : contact.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();

  return (
    <a href={contact.linkedin_url} target="_blank" rel="noreferrer" style={{
      display: 'flex', alignItems: 'center', gap: '10px',
      padding: '10px 12px',
      background: '#060d08',
      border: '1px solid #1a2e24',
      borderRadius: '8px',
      textDecoration: 'none',
      transition: 'border-color 0.15s',
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = '#1D9E75'}
      onMouseLeave={e => e.currentTarget.style.borderColor = '#1a2e24'}
    >
      <div style={{
        width: '34px', height: '34px', borderRadius: '50%',
        background: '#0a2e1f',
        border: '1px solid #1D9E75',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
        fontSize: '11px', fontWeight: '700',
        fontFamily: "'JetBrains Mono', monospace",
        color: '#5DCAA5',
      }}>{initials}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontSize: '13px', fontWeight: '600', color: '#c8d9cc', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {contact.name}
        </p>
        <p style={{ margin: 0, fontSize: '11px', color: '#4a7a5e', fontFamily: "'JetBrains Mono', monospace" }}>
          {contact.designation}
        </p>
      </div>
      <ExternalLink size={12} color="#2d5a3d" />
    </a>
  );
}

/* ── Skeleton ── */
function Skeleton() {
  const box = (w, h) => (
    <div style={{ height: h, width: w, background: '#0d1710', borderRadius: '6px' }} />
  );
  return (
    <div style={{
      background: '#0a0f0c', border: '1px solid #1a2e24',
      borderRadius: '14px', padding: '20px',
      display: 'flex', flexDirection: 'column', gap: '14px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
          {box('55%', 18)} {box('35%', 12)}
        </div>
        <div style={{ width: 64, height: 64, borderRadius: '50%', background: '#0d1710' }} />
      </div>
      {box('100%', 1)}
      {box('100%', 60)}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        {box('100%', 54)} {box('100%', 54)}
      </div>
    </div>
  );
}

/* ── Lead card ── */
function LeadCard({ company }) {
  const signals = company.signals ? Object.keys(company.signals).slice(0, 4) : [];
  const confPct = company.confidence_score != null ? Math.round(company.confidence_score * 100) : null;
  const confColor = confPct >= 80 ? '#1D9E75' : confPct >= 60 ? '#EF9F27' : '#E24B4A';

  return (
    <div style={{
      background: '#0a0f0c',
      border: '1px solid #1a2e24',
      borderRadius: '14px',
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h2 style={{ margin: '0 0 4px', fontSize: '18px', fontWeight: '700', color: '#e8ede9', letterSpacing: '-0.01em' }}>
            {company.name}
          </h2>
          <a
            href={company.domain?.startsWith('http') ? company.domain : `https://${company.domain}`}
            target="_blank" rel="noreferrer"
            style={{ fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", color: '#1D9E75', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
          >
            {company.domain} <ExternalLink size={10} />
          </a>
          {signals.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
              {signals.map(s => <Tag key={s} label={s} />)}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
          <ScoreRing score={company.lead_score} />
          <span style={{ fontSize: '9px', fontFamily: "'JetBrains Mono', monospace", color: '#2d5a3d', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            lead score
          </span>
        </div>
      </div>

      <div style={{ borderTop: '1px solid #1a2e24' }} />

      {/* Reason */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
          <Brain size={12} color="#1D9E75" />
          <span style={{ fontSize: '10px', fontFamily: "'JetBrains Mono', monospace", color: '#4a7a5e', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            AI reasoning
          </span>
        </div>
        <p style={{
          margin: 0, fontSize: '13px', color: '#8aab94', lineHeight: '1.6',
          background: '#060d08', border: '1px solid #111c14',
          borderRadius: '8px', padding: '12px 14px',
          fontFamily: "'Syne', sans-serif",
        }}>
          {company.reason}
        </p>
      </div>

      {/* Confidence */}
      {confPct != null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <TrendingUp size={12} color="#4a7a5e" />
          <span style={{ fontSize: '10px', fontFamily: "'JetBrains Mono', monospace", color: '#4a7a5e', textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>
            Confidence
          </span>
          <div style={{ flex: 1, height: '3px', background: '#1a2e24', borderRadius: '2px', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${confPct}%`, background: confColor, borderRadius: '2px', transition: 'width 0.6s ease' }} />
          </div>
          <span style={{ fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", color: '#4a7a5e', minWidth: '32px', textAlign: 'right' }}>
            {confPct}%
          </span>
        </div>
      )}

      {/* Contacts */}
      {company.top_contacts?.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
            <Users size={12} color="#1D9E75" />
            <span style={{ fontSize: '10px', fontFamily: "'JetBrains Mono', monospace", color: '#4a7a5e', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              Key executives
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px' }}>
            {company.top_contacts.map((c, i) => <ContactCard key={i} contact={c} />)}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Main export ── */
export default function LeadTable({ results, jobStatus, jobId, error }) {
  const isWorking = jobId && jobStatus !== 'completed' && jobStatus !== 'failed';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Top bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '10px', fontFamily: "'JetBrains Mono', monospace", color: '#4a7a5e', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Results
          </span>
          {results.length > 0 && (
            <span style={{
              fontSize: '10px', fontFamily: "'JetBrains Mono', monospace",
              padding: '2px 9px', borderRadius: '20px',
              background: '#041a0f', border: '1px solid #0F6E56', color: '#1D9E75',
            }}>
              {results.length} leads
            </span>
          )}
        </div>
        <StatusPill status={jobStatus} error={error} />
      </div>

      {/* Loading */}
      {isWorking && <><Skeleton /><Skeleton /></>}

      {/* Idle */}
      {jobStatus === 'idle' && (
        <div style={{
          background: '#0a0f0c', border: '1px solid #1a2e24', borderRadius: '14px',
          minHeight: '400px', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: '14px',
        }}>
          <div style={{
            width: '52px', height: '52px', borderRadius: '50%',
            background: '#060d08', border: '1px solid #1a2e24',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Users size={22} color="#2d5a3d" />
          </div>
          <div style={{ textAlign: 'center' }}>
            <p style={{ margin: '0 0 4px', fontSize: '14px', color: '#4a7a5e', fontWeight: '500' }}>No leads yet</p>
            <p style={{ margin: 0, fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", color: '#2d5a3d' }}>
              Configure parameters and deploy AI to hunt for leads.
            </p>
          </div>
        </div>
      )}

      {/* Results */}
      {jobStatus === 'completed' && results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {results.map((company, i) => <LeadCard key={i} company={company} />)}
        </div>
      )}

      {/* Completed, no results */}
      {jobStatus === 'completed' && results.length === 0 && (
        <div style={{
          background: '#0a0f0c', border: '1px solid #1a2e24', borderRadius: '14px',
          minHeight: '300px', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: '8px',
        }}>
          <p style={{ margin: 0, fontSize: '13px', color: '#4a7a5e' }}>No qualified leads found.</p>
          <p style={{ margin: 0, fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", color: '#2d5a3d' }}>
            Try loosening AI strictness or expanding geography.
          </p>
        </div>
      )}
    </div>
  );
}