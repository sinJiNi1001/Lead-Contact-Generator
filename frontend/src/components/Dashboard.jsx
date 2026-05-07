import React from 'react';
import { Search, Loader2 } from 'lucide-react';

export default function Dashboard({ theme, formData, handleChange, handleSubmit, jobStatus }) {
  const isWorking = jobStatus !== 'idle' && jobStatus !== 'completed' && jobStatus !== 'failed';

  const inputStyle = { width: '100%', background: theme.inputBg, border: `1px solid ${theme.border}`, borderRadius: '6px', padding: '8px 12px', fontSize: '13px', color: theme.text, outline: 'none' };
  const labelStyle = { fontSize: '11px', color: theme.textMuted, textTransform: 'uppercase', marginBottom: '4px', display: 'block', fontWeight: 'bold' };
  const cardStyle = { background: theme.card, border: `1px solid ${theme.border}`, borderRadius: '10px', padding: '16px', marginBottom: '16px' };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column' }}>
      
      <div style={cardStyle}>
        <h3 style={{ fontSize: '12px', color: theme.primary, textTransform: 'uppercase', marginBottom: '12px', borderBottom: `1px solid ${theme.border}`, paddingBottom: '8px' }}>Core Target</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div><label style={labelStyle}>Industry</label><input style={inputStyle} type="text" name="industry" value={formData.industry} onChange={handleChange} /></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div><label style={labelStyle}>Geography</label><input style={inputStyle} type="text" name="location" value={formData.location} onChange={handleChange} /></div>
            <div><label style={labelStyle}>Max leads</label><input style={inputStyle} type="number" name="numLeads" value={formData.numLeads} onChange={handleChange} min={1} max={20} /></div>
          </div>
          <div>
            <label style={labelStyle}>Company size</label>
            <select style={inputStyle} name="companySize" value={formData.companySize} onChange={handleChange}>
              <option>Startup (1-50)</option><option>Mid-Market (51-500)</option><option>Enterprise (500+)</option>
            </select>
          </div>
        </div>
      </div>

      <div style={cardStyle}>
        <h3 style={{ fontSize: '12px', color: theme.primary, textTransform: 'uppercase', marginBottom: '12px', borderBottom: `1px solid ${theme.border}`, paddingBottom: '8px' }}>AI Parameters</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div><label style={labelStyle}>Target roles</label><input style={inputStyle} type="text" name="targetRoles" value={formData.targetRoles} onChange={handleChange} /></div>
          <div><label style={labelStyle}>Keywords</label><input style={inputStyle} type="text" name="keywords" value={formData.keywords} onChange={handleChange} /></div>
          <div>
            <label style={labelStyle}>AI strictness — {formData.strictnessLevel}/10</label>
            <input type="range" name="strictnessLevel" min="1" max="10" step="1" value={formData.strictnessLevel} onChange={handleChange} style={{ width: '100%', accentColor: theme.primary }} />
          </div>
        </div>
      </div>

      <button type="submit" disabled={isWorking} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '12px', background: theme.primary, border: 'none', borderRadius: '8px', color: '#fff', fontSize: '14px', fontWeight: 'bold', cursor: isWorking ? 'not-allowed' : 'pointer', opacity: isWorking ? 0.6 : 1 }}>
        {isWorking ? <><Loader2 size={16} className="animate-spin" /><span>Hunting...</span></> : <><Search size={16} /><span>Generate Leads</span></>}
      </button>
    </form>
  );
}