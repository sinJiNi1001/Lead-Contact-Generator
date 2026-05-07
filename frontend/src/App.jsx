import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Sun, Moon } from 'lucide-react';
import Dashboard from './components/Dashboard';
import LeadTable from './components/LeadTable';

const API_BASE_URL = 'http://localhost:8000/api';

// --- THEME ENGINE ---
const THEMES = {
  dark: { bg: '#080c0a', card: '#0a0f0c', text: '#e8ede9', textMuted: '#8aab94', border: '#1a2e24', primary: '#1D9E75', inputBg: '#060d08' },
  light: { bg: '#f0f4f1', card: '#ffffff', text: '#111c14', textMuted: '#4a7a5e', border: '#c3d6cb', primary: '#1D9E75', inputBg: '#f8faf9' }
};

export default function App() {
  const [isDark, setIsDark] = useState(true);
  const theme = isDark ? THEMES.dark : THEMES.light;

  const [formData, setFormData] = useState({
    industry: 'Software Development', location: 'Pune', locationGranularity: 'City Level',
    numLeads: 3, companySize: 'Mid-Market (51-500)', targetRoles: 'CTO, CEO',
    keywords: 'SaaS, B2B, scalable', exclusionKeywords: 'agency, non-profit', strictnessLevel: 8,
  });

  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState('idle');
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);

  const handleChange = (e) => setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setJobId(null); setJobStatus('queued'); setResults([]); setError(null);
    try {
      const response = await axios.post(`${API_BASE_URL}/generate-leads`, {
        industry: formData.industry, location: formData.location,
        sales_inputs: {
          'Number of Leads Required': formData.numLeads, 'Company Size': formData.companySize,
          'Target Roles': formData.targetRoles.split(',').map(r => r.trim()),
          'Keywords': formData.keywords, 'Exclusion Keywords': formData.exclusionKeywords,
          'Strictness Level': formData.strictnessLevel,
        },
      });
      setJobId(response.data.job_id);
    } catch (err) { setError('Failed to connect to backend.'); setJobStatus('failed'); }
  };

  useEffect(() => {
    let interval;
    if (jobId && jobStatus !== 'completed' && jobStatus !== 'failed') {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE_URL}/jobs/${jobId}`);
          
          // 1. Did the server restart and lose our job?
          if (res.data.error) {
            setError("The backend lost the job (Server likely reloaded). Check the Python terminal!");
            setJobStatus('failed');
            clearInterval(interval);
            return;
          }

          // 2. Otherwise, update the status normally
          setJobStatus(res.data.status);
          
          if (res.data.status === 'completed') {
            setResults(res.data.results);
            clearInterval(interval);
          } else if (res.data.status === 'failed') {
            setError(res.data.error);
            clearInterval(interval);
          }
        } catch (err) {
          console.error('Polling error:', err);
          setError('Lost connection to the backend server.');
          setJobStatus('failed');
          clearInterval(interval);
        }
      }, 2500);
    }
    return () => clearInterval(interval);
  }, [jobId, jobStatus]);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: theme.bg, color: theme.text, fontFamily: "'Syne', sans-serif", overflow: 'hidden', transition: 'background 0.3s' }}>
      
      {/* HEADER */}
      <header style={{ padding: '12px 24px', borderBottom: `1px solid ${theme.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: theme.card }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <img src="/static/logo.png" alt="Logo" style={{ height: '32px' }} onError={(e) => e.target.style.display = 'none'} />
          <h1 style={{ margin: 0, fontSize: '18px', fontWeight: '700' }}>Lead Contact Generator</h1>
        </div>
        <button onClick={() => setIsDark(!isDark)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: theme.text }}>
          {isDark ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </header>

      {/* MAIN CONTENT (NO SCROLL WINDOW) */}
      <main style={{ flex: 1, overflow: 'hidden', padding: '24px', maxWidth: '1400px', margin: '0 auto', width: '100%', display: 'grid', gridTemplateColumns: 'minmax(0, 380px) minmax(0, 1fr)', gap: '24px' }}>
        
        {/* LEFT COLUMN: FORM */}
        <div style={{ overflowY: 'auto', paddingRight: '10px' }}>
          <Dashboard theme={theme} formData={formData} handleChange={handleChange} handleSubmit={handleSubmit} jobStatus={jobStatus} />
        </div>

        {/* RIGHT COLUMN: RESULTS */}
        <div style={{ overflowY: 'auto', paddingRight: '10px' }}>
          <LeadTable theme={theme} results={results} jobStatus={jobStatus} jobId={jobId} error={error} />
        </div>

      </main>

      {/* FOOTER */}
      <footer style={{ padding: '8px', borderTop: `1px solid ${theme.border}`, textAlign: 'center', fontSize: '12px', background: theme.card, color: theme.textMuted }}>
        Copyright © 2008 : Valency Networks Private Limited.
      </footer>
    </div>
  );
}