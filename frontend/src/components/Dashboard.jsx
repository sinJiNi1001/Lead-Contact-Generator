import React from 'react';
import { Crosshair, Search, Loader2, Zap, Sliders } from 'lucide-react';

const S = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  logoRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logoIcon: {
    width: '36px',
    height: '36px',
    borderRadius: '10px',
    background: '#0F6E56',
    border: '1px solid #1D9E75',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  logoTitle: {
    fontSize: '14px',
    fontWeight: '700',
    color: '#e8ede9',
    letterSpacing: '-0.01em',
    margin: 0,
  },
  logoSub: {
    fontSize: '10px',
    fontFamily: "'JetBrains Mono', monospace",
    color: '#1D9E75',
    letterSpacing: '0.1em',
    margin: 0,
  },
  card: {
    background: '#0a0f0c',
    border: '1px solid #1a2e24',
    borderRadius: '14px',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    paddingBottom: '12px',
    borderBottom: '1px solid #1a2e24',
  },
  sectionLabel: {
    fontSize: '10px',
    fontFamily: "'JetBrains Mono', monospace",
    color: '#4a7a5e',
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    margin: 0,
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '11px',
    fontFamily: "'JetBrains Mono', monospace",
    color: '#4a7a5e',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
  },
  input: {
    width: '100%',
    background: '#060d08',
    border: '1px solid #1a2e24',
    borderRadius: '8px',
    padding: '9px 14px',
    fontSize: '13px',
    fontFamily: "'JetBrains Mono', monospace",
    color: '#c8d9cc',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.15s',
  },
  row2: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
  },
  sliderRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  sliderNote: {
    fontSize: '10px',
    fontFamily: "'JetBrains Mono', monospace",
    color: '#2d5a3d',
  },
  strictVal: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: '#1D9E75',
    minWidth: '28px',
  },
  btn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '12px',
    background: '#0F6E56',
    border: '1px solid #1D9E75',
    borderRadius: '10px',
    color: '#fff',
    fontSize: '14px',
    fontFamily: "'Syne', sans-serif",
    fontWeight: '600',
    cursor: 'pointer',
    letterSpacing: '0.02em',
    transition: 'background 0.15s, transform 0.1s',
  },
  btnDisabled: {
    opacity: 0.45,
    cursor: 'not-allowed',
  },
};

function Field({ label, children }) {
  return (
    <div style={S.field}>
      <span style={S.label}>{label}</span>
      {children}
    </div>
  );
}

export default function Dashboard({ formData, handleChange, handleSubmit, jobStatus }) {
  const isWorking = jobStatus !== 'idle' && jobStatus !== 'completed' && jobStatus !== 'failed';

  return (
    <div style={S.root}>
      {/* Logo */}
      <div style={S.logoRow}>
        <div style={S.logoIcon}>
          <Crosshair size={18} color="#5DCAA5" />
        </div>
        <div>
          <p style={S.logoTitle}>Lead Intel Engine</p>
          <p style={S.logoSub}>AI-POWERED B2B</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* Section 1 */}
        <div style={S.card}>
          <div style={S.sectionHeader}>
            <Zap size={12} color="#1D9E75" />
            <span style={S.sectionLabel}>01 — Core target</span>
          </div>
          <div style={S.fieldGroup}>
            <Field label="Industry">
              <input
                style={S.input} type="text"
                name="industry" value={formData.industry} onChange={handleChange}
              />
            </Field>
            <div style={S.row2}>
              <Field label="Geography">
                <input style={S.input} type="text" name="location" value={formData.location} onChange={handleChange} />
              </Field>
              <Field label="Max leads">
                <input style={S.input} type="number" name="numLeads" value={formData.numLeads} onChange={handleChange} min={1} max={20} />
              </Field>
            </div>
            <Field label="Company size">
              <select style={S.input} name="companySize" value={formData.companySize} onChange={handleChange}>
                <option>Startup (1-50)</option>
                <option>Mid-Market (51-500)</option>
                <option>Enterprise (500+)</option>
              </select>
            </Field>
          </div>
        </div>

        {/* Section 2 */}
        <div style={S.card}>
          <div style={S.sectionHeader}>
            <Sliders size={12} color="#1D9E75" />
            <span style={S.sectionLabel}>02 — AI parameters</span>
          </div>
          <div style={S.fieldGroup}>
            <Field label="Target roles (comma separated)">
              <input style={S.input} type="text" name="targetRoles" value={formData.targetRoles} onChange={handleChange} placeholder="CTO, CEO" />
            </Field>
            <Field label="Must-have keywords">
              <input style={S.input} type="text" name="keywords" value={formData.keywords} onChange={handleChange} placeholder="SaaS, B2B, scalable" />
            </Field>
            <Field label="Exclusion keywords">
              <input style={S.input} type="text" name="exclusionKeywords" value={formData.exclusionKeywords} onChange={handleChange} placeholder="agency, non-profit" />
            </Field>
            <Field label={`AI strictness — ${formData.strictnessLevel}/10`}>
              <div style={S.sliderRow}>
                <span style={S.sliderNote}>loose</span>
                <input
                  type="range" name="strictnessLevel" min="1" max="10" step="1"
                  value={formData.strictnessLevel} onChange={handleChange}
                  style={{ flex: 1, accentColor: '#1D9E75', cursor: 'pointer' }}
                />
                <span style={S.sliderNote}>strict</span>
              </div>
            </Field>
          </div>
        </div>

        {/* Button */}
        <button
          type="submit"
          disabled={isWorking}
          style={{ ...S.btn, ...(isWorking ? S.btnDisabled : {}) }}
          onMouseEnter={e => { if (!isWorking) e.currentTarget.style.background = '#1D9E75'; }}
          onMouseLeave={e => { if (!isWorking) e.currentTarget.style.background = '#0F6E56'; }}
        >
          {isWorking
            ? <><Loader2 size={16} className="animate-spin" /><span>Hunting leads...</span></>
            : <><Search size={16} /><span>Generate leads</span></>
          }
        </button>
      </form>
    </div>
  );
}