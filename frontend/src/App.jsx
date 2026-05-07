import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Dashboard from './components/Dashboard';
import LeadTable from './components/LeadTable';

const API_BASE_URL = 'http://localhost:8000/api';

export default function App() {
  const [formData, setFormData] = useState({
    industry: 'Software Development',
    location: 'Pune',
    locationGranularity: 'City Level',
    numLeads: 3,
    companySize: 'Mid-Market (51-500)',
    targetRoles: 'CTO, CEO',
    keywords: 'SaaS, B2B, scalable',
    exclusionKeywords: 'agency, non-profit',
    strictnessLevel: 8,
  });

  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState('idle');
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setJobId(null);
    setJobStatus('queued');
    setResults([]);
    setError(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/generate-leads`, {
        industry: formData.industry,
        location: formData.location,
        sales_inputs: {
          'Location Granularity': formData.locationGranularity,
          'Number of Leads Required': formData.numLeads,
          'Company Size': formData.companySize,
          'Target Roles': formData.targetRoles.split(',').map(r => r.trim()),
          'Keywords': formData.keywords,
          'Exclusion Keywords': formData.exclusionKeywords,
          'Strictness Level': formData.strictnessLevel,
        },
      });
      setJobId(response.data.job_id);
    } catch (err) {
      setError('Failed to connect to backend.');
      setJobStatus('failed');
    }
  };

  useEffect(() => {
    let interval;
    if (jobId && jobStatus !== 'completed' && jobStatus !== 'failed') {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE_URL}/jobs/${jobId}`);
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
        }
      }, 2500);
    }
    return () => clearInterval(interval);
  }, [jobId, jobStatus]);

  return (
    <div style={{
      minHeight: '100vh',
      background: '#080c0a',
      backgroundImage: `
        linear-gradient(rgba(29,158,117,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(29,158,117,0.03) 1px, transparent 1px)
      `,
      backgroundSize: '40px 40px',
      padding: '40px 24px',
      fontFamily: "'Syne', sans-serif",
    }}>
      <div style={{
        maxWidth: '1280px',
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 380px) minmax(0, 1fr)',
        gap: '32px',
        alignItems: 'start',
      }}>
        <Dashboard
          formData={formData}
          handleChange={handleChange}
          handleSubmit={handleSubmit}
          jobStatus={jobStatus}
        />
        <LeadTable
          results={results}
          jobStatus={jobStatus}
          jobId={jobId}
          error={error}
        />
      </div>
    </div>
  );
}