import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MapPin, Briefcase, List, Play, Database, Search } from 'lucide-react';
import LeadTable from './components/LeadTable';

const API_BASE_URL = 'http://localhost:8000/api';

// PROFESSIONAL ENTERPRISE LIGHT THEME
const theme = {
  bg: '#f1f5f9',          // Soft light gray for the main canvas
  surface: '#ffffff',     // Pure white for header and cards
  border: '#e2e8f0',      // Crisp light border
  text: '#0f172a',        // Deep slate for readable text
  textMuted: '#64748b',   // Muted slate for labels and secondary text
  primary: '#0284c7',     // Corporate trust blue
  danger: '#ef4444',
  success: '#10b981'
};

export default function App() {
  const [activeTab, setActiveTab] = useState('search'); 
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState('idle');
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [historyData, setHistoryData] = useState([]);

  const [industry, setIndustry] = useState('Finance');
  const [location, setLocation] = useState('Baner, Pune');
  const [numLeads, setNumLeads] = useState(3);
  const [targetRoles, setTargetRoles] = useState('CTO, CEO');
  const [keywords, setKeywords] = useState('SaaS, B2B');
  

  const loadHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/history`);
      setHistoryData(res.data);
    } catch (err) {
      console.error("Failed to load history", err);
    }
  };

  const startJob = async (e) => {
    e.preventDefault();
    setJobId(null);
    setResults([]);
    setError(null);
    setJobStatus('starting');
    setActiveTab('search'); 

    const payload = {
      industry,
      location,
      sales_inputs: {
        "Number of Leads Required": parseInt(numLeads),
        "Target Roles": targetRoles.split(',').map(r => r.trim()),
        "Keywords": keywords,
        "Company Size": "Any"
      }
    };

    try {
      const res = await axios.post(`${API_BASE_URL}/generate-leads`, payload);
      setJobId(res.data.job_id);
      setJobStatus('queued');
    } catch (err) {
      setError("Failed to start AI job.");
      setJobStatus('failed');
    }
  };

  useEffect(() => {
    let intervalId;
    const checkStatus = async () => {
      if (!jobId) return;
      try {
        const res = await axios.get(`${API_BASE_URL}/jobs/${jobId}`);
        const data = res.data;
        setJobStatus(data.status);
        if (data.status === 'completed') {
          setResults(data.results || []);
          clearInterval(intervalId);
        } else if (data.status === 'failed') {
          setError(data.error || "Job failed internally.");
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    };

    if (jobId && jobStatus !== 'completed' && jobStatus !== 'failed') {
      intervalId = setInterval(checkStatus, 3000); 
    }
    return () => clearInterval(intervalId);
  }, [jobId, jobStatus]);

  // Clean form input styling
  const inputStyle = {
    width: '100%', 
    background: '#ffffff', 
    border: `1px solid ${theme.border}`, 
    color: theme.text, 
    padding: '10px 12px', 
    borderRadius: '4px',
    outline: 'none', 
    fontSize: '14px',
    boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)'
  };

  const labelStyle = {
    display: 'flex', 
    alignItems: 'center', 
    gap: '6px', 
    fontSize: '13px', 
    fontWeight: '600', 
    marginBottom: '6px', 
    color: theme.textMuted
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', backgroundColor: theme.bg, color: theme.text, fontFamily: 'system-ui, -apple-system, sans-serif', overflow: 'hidden' }}>
      
      {/* PURE WHITE HEADER WITH LOGO */}
      <div style={{ height: '70px', backgroundColor: theme.surface, borderBottom: `1px solid ${theme.border}`, boxShadow: '0 1px 3px rgba(0,0,0,0.05)', display: 'flex', alignItems: 'center', padding: '0 32px', justifyContent: 'space-between', flexShrink: 0, zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
           {/* LOGO SOURCED FROM PUBLIC DIRECTORY */}
           <img src="/static/logo.png" alt="Company Logo" style={{ height: '40px', objectFit: 'contain' }} />
           <div style={{ height: '24px', width: '1px', backgroundColor: theme.border, margin: '0 8px' }}></div>
           <h1 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: theme.text, letterSpacing: '0.5px' }}>
             LEAD CONTACT GENERATOR
           </h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: theme.textMuted, fontWeight: '500' }}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: jobStatus === 'completed' || jobStatus === 'idle' ? theme.textMuted : theme.primary }}></span>
          System Status: <span style={{ color: theme.text, textTransform: 'capitalize' }}>{jobStatus}</span>
        </div>
      </div>

      {/* MAIN WORKSPACE */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* LEFT SIDEBAR: Search Parameters */}
        <div style={{ width: '380px', backgroundColor: theme.surface, borderRight: `1px solid ${theme.border}`, padding: '32px 24px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
          
          <h2 style={{ fontSize: '16px', fontWeight: '700', margin: '0 0 24px 0', color: theme.text }}>Campaign Parameters</h2>

          <form onSubmit={startJob} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <label style={labelStyle}><Briefcase size={14} /> Target Industry</label>
              <input required type="text" value={industry} onChange={e => setIndustry(e.target.value)} style={inputStyle} />
            </div>

            <div>
              <label style={labelStyle}><MapPin size={14} /> Enter City [city mandatory, location optional]</label>
              <input required type="text" value={location} onChange={e => setLocation(e.target.value)} style={inputStyle} />
            </div>

            <div>
              <label style={labelStyle}><List size={14} /> Target Roles</label>
              <input required type="text" value={targetRoles} onChange={e => setTargetRoles(e.target.value)} style={inputStyle} />
            </div>

            <div>
              <label style={labelStyle}><Search size={14} /> Website Keywords</label>
              <textarea required value={keywords} onChange={e => setKeywords(e.target.value)} style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }} />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 0', borderTop: `1px solid ${theme.border}`, marginTop: '8px' }}>
              <label style={{ fontSize: '14px', fontWeight: '600', color: theme.text }}>Volume Required</label>
              <input required type="number" min="1" max="50" value={numLeads} onChange={e => setNumLeads(e.target.value)} style={{ ...inputStyle, width: '80px', textAlign: 'center', padding: '8px' }} />
            </div>

            <button type="submit" disabled={jobStatus !== 'idle' && jobStatus !== 'completed' && jobStatus !== 'failed'}
              style={{ background: theme.primary, color: '#ffffff', border: 'none', padding: '14px', borderRadius: '4px', fontWeight: '600', fontSize: '15px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', boxShadow: '0 2px 4px rgba(2, 132, 199, 0.2)', transition: 'opacity 0.2s', opacity: (jobStatus !== 'idle' && jobStatus !== 'completed' && jobStatus !== 'failed') ? 0.6 : 1 }}>
              <Play size={16} fill="currentColor" /> Run Generation
            </button>
          </form>
        </div>

        {/* RIGHT MAIN AREA: Data Table */}
        <div style={{ flex: 1, padding: '32px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          
          {/* Top Tabs */}
          <div style={{ display: 'flex', gap: '12px', borderBottom: `1px solid ${theme.border}`, paddingBottom: '16px', marginBottom: '24px', flexShrink: 0 }}>
            <button onClick={() => setActiveTab('search')}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', background: activeTab === 'search' ? '#f8fafc' : 'transparent', color: activeTab === 'search' ? theme.primary : theme.textMuted, border: activeTab === 'search' ? `1px solid ${theme.border}` : '1px solid transparent', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: '600', fontSize: '14px', transition: 'all 0.2s' }}>
              Live Generation
            </button>
            <button onClick={() => { setActiveTab('history'); loadHistory(); }}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', background: activeTab === 'history' ? '#f8fafc' : 'transparent', color: activeTab === 'history' ? theme.primary : theme.textMuted, border: activeTab === 'history' ? `1px solid ${theme.border}` : '1px solid transparent', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: '600', fontSize: '14px', transition: 'all 0.2s' }}>
              <Database size={16} /> Search History
            </button>
          </div>

          <div style={{ flex: 1, overflow: 'hidden' }}>
            {activeTab === 'search' ? (
              <LeadTable theme={theme} results={results} jobStatus={jobStatus} jobId={jobId} error={error} />
            ) : (
              <LeadTable theme={theme} results={historyData} jobStatus="completed" isHistoryView={true} />
            )}
          </div>
        </div>

      </div>

      {/* FOOTER */}
      <div style={{ height: '48px', backgroundColor: '#e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 32px', fontSize: '13px', color: '#475569', flexShrink: 0, zIndex: 10, fontWeight: '500' }}>
        <span>Copyright &copy; 2008 : Valency Networks Private Limited.</span>
      </div>

    </div>
  );
}