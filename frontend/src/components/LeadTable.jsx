import React, { useState } from 'react';
import { Download, Search, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import axios from 'axios';
import StatusPill from './StatusPill';

const API_BASE_URL = 'http://localhost:8000/api';

export default function LeadTable({ theme, results, jobStatus, jobId, error, isHistoryView = false }) {
  const isWorking = jobId && jobStatus !== 'completed' && jobStatus !== 'failed';
  const [expandedId, setExpandedId] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');

  // SMART CSV EXPORT 
  const handleExportCSV = () => {
    const headers = ["Company", "Domain", "Industry", "Location", "Score", "Reason", "Contact Name", "Designation", "LinkedIn", "Status", "Notes", "Follow Up Date"];
    let csvContent = headers.join(",") + "\n";

    results.forEach(company => {
      if (company.top_contacts && company.top_contacts.length > 0) {
        company.top_contacts.forEach(c => {
          const row = [
            `"${company.name || ''}"`, `"${company.domain || ''}"`, `"${company.industry || ''}"`, `"${company.location || ''}"`, `"${company.lead_score || ''}"`, `"${(company.reason || '').replace(/"/g, '""')}"`,
            `"${c.name || ''}"`, `"${c.designation || ''}"`, `"${c.linkedin_url || ''}"`, `"${c.contact_status || 'New'}"`, `"${(c.notes || '').replace(/"/g, '""')}"`, `"${c.follow_up_date || ''}"`
          ];
          csvContent += row.join(",") + "\n";
        });
      } else {
        const row = [`"${company.name}"`, `"${company.domain}"`, `"${company.industry}"`, `"${company.location}"`, `"${company.lead_score}"`, `"${(company.reason || '').replace(/"/g, '""')}"`, "","","","","",""];
        csvContent += row.join(",") + "\n";
      }
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = isHistoryView ? "valency_crm_database.csv" : "valency_live_leads.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleCRMUpdate = async (contactId, field, value) => {
    if (!contactId) return; 
    try {
      await axios.put(`${API_BASE_URL}/contacts/${contactId}`, { [field]: value });
    } catch (err) {
      console.error("Failed to save CRM update", err);
    }
  };

  // FILTERING LOGIC
  const filteredResults = results.filter(company => {
    // Check Search Box
    const matchesSearch = company.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (company.reason && company.reason.toLowerCase().includes(searchTerm.toLowerCase()));
    
    // Check Status Dropdown
    const matchesStatus = statusFilter === 'All' || 
      (company.top_contacts && company.top_contacts.some(c => (c.contact_status || 'New') === statusFilter));

    return matchesSearch && matchesStatus;
  });

  if (isWorking) {
    return <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: '6px', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><StatusPill status={jobStatus} /></div>;
  }

  if (jobStatus === 'idle' && !isHistoryView) {
    return <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: '6px', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: theme.textMuted, fontSize: '15px' }}>System ready. Please set campaign parameters and run generation.</div>;
  }

  const renderCompanyCard = (company) => {
    const isExpanded = expandedId === company.domain;
    return (
      <div key={company.domain} style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: '6px', marginBottom: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
        <div onClick={() => setExpandedId(isExpanded ? null : company.domain)} style={{ padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', background: isExpanded ? '#f8fafc' : theme.surface, transition: 'background 0.2s' }}>
          <div>
            <h3 style={{ margin: '0 0 6px', fontSize: '17px', fontWeight: '700', color: theme.text }}>{company.name}</h3>
            <a href={`https://${company.domain}`} target="_blank" rel="noreferrer" style={{ fontSize: '13px', color: theme.primary, textDecoration: 'none', fontWeight: '500' }} onClick={e => e.stopPropagation()}>{company.domain}</a>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <div style={{ textAlign: 'right' }}>
              <span style={{ display: 'block', fontSize: '20px', fontWeight: '800', color: company.lead_score >= 80 ? theme.primary : '#d97706' }}>{company.lead_score}</span>
              <span style={{ fontSize: '11px', fontWeight: '600', color: theme.textMuted, textTransform: 'uppercase' }}>AI Score</span>
            </div>
            {isExpanded ? <ChevronUp size={20} color={theme.textMuted} /> : <ChevronDown size={20} color={theme.textMuted} />}
          </div>
        </div>

        {isExpanded && (
          <div style={{ padding: '24px', borderTop: `1px solid ${theme.border}` }}>
            
            {/* DUPLICATE PREVENTION ALERT */}
            {company.duplicates_hidden > 0 && (
              <div style={{ background: '#fef3c7', color: '#92400e', padding: '12px 16px', borderRadius: '4px', fontSize: '13px', fontWeight: '600', marginBottom: '16px' }}>
                🛡️ {company.duplicates_hidden} duplicate contacts might be present.
              </div>
            )}

            <p style={{ fontSize: '14px', color: theme.text, lineHeight: '1.6', background: theme.bg, padding: '16px', borderRadius: '4px', marginBottom: '24px', borderLeft: `4px solid ${theme.primary}` }}>
              {company.reason}
            </p>
            {company.top_contacts?.length > 0 && (
              <div>
                <h4 style={{ fontSize: '13px', fontWeight: '700', color: theme.text, marginBottom: '12px', borderBottom: `1px solid ${theme.border}`, paddingBottom: '8px' }}>EXECUTIVE CONTACTS</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {company.top_contacts.map((c, idx) => (
                    <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1.5fr 1.5fr 2fr', gap: '16px', alignItems: 'start', padding: '16px', background: '#ffffff', borderRadius: '6px', border: `1px solid ${theme.border}` }}>
                      <div>
                        <a href={c.linkedin_url} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: theme.text, fontWeight: '700', fontSize: '14px', textDecoration: 'none' }}>
                          {c.name} <ExternalLink size={14} color={theme.textMuted} />
                        </a>
                        <p style={{ margin: '6px 0 0', fontSize: '13px', color: theme.textMuted }}>{c.designation}</p>
                      </div>
                      
                      {/* DATE PICKER & STATUS DROPDOWN WITH LABELS */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div>
                          <label style={{ fontSize: '11px', fontWeight: '700', color: theme.textMuted, display: 'block', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            📅 Follow-up Date
                          </label>
                          <input 
                            type="date" 
                            title="Follow-up Date"
                            defaultValue={c.follow_up_date || ""} 
                            onChange={(e) => handleCRMUpdate(c.id, "follow_up_date", e.target.value)} 
                            style={{ width: '100%', background: '#ffffff', border: `1px solid ${theme.border}`, color: theme.textMuted, padding: '8px 12px', borderRadius: '4px', fontSize: '13px', outline: 'none', cursor: 'pointer' }} 
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '11px', fontWeight: '700', color: theme.textMuted, display: 'block', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            📌 Lead Status
                          </label>
                          <select 
                            defaultValue={c.contact_status || "New"} 
                            onChange={(e) => handleCRMUpdate(c.id, "contact_status", e.target.value)} 
                            style={{ width: '100%', background: '#ffffff', border: `1px solid ${theme.border}`, color: theme.text, padding: '8px 12px', borderRadius: '4px', fontSize: '13px', outline: 'none', cursor: 'pointer' }}
                          >
                            <option value="New">New Lead</option>
                            <option value="Contacted">Contacted</option>
                            <option value="Replied">Replied</option>
                            <option value="Not Interested">Not Interested</option>
                          </select>
                        </div>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                        <label style={{ fontSize: '11px', fontWeight: '700', color: theme.textMuted, display: 'block', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            📝 Notes
                        </label>
                        <textarea 
                          defaultValue={c.notes || ""} 
                          onBlur={(e) => handleCRMUpdate(c.id, "notes", e.target.value)} 
                          placeholder="Add interaction notes..." 
                          style={{ width: '100%', flex: 1, background: '#ffffff', border: `1px solid ${theme.border}`, color: theme.text, padding: '10px 12px', borderRadius: '4px', fontSize: '13px', outline: 'none', minHeight: '90px', resize: 'vertical' }} 
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexShrink: 0 }}>
        
        {/* TOP SEARCH & STATUS FILTER BAR */}
        <div style={{ display: 'flex', gap: '12px', width: '550px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} color={theme.textMuted} style={{ position: 'absolute', left: '12px', top: '10px' }} />
            <input type="text" placeholder="Search companies or keywords..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} style={{ width: '100%', background: theme.surface, border: `1px solid ${theme.border}`, padding: '10px 12px 10px 36px', borderRadius: '4px', color: theme.text, outline: 'none', fontSize: '14px' }} />
          </div>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: '4px', padding: '10px 12px', fontSize: '14px', outline: 'none', color: theme.text, cursor: 'pointer', width: '160px' }}>
            <option value="All">All Statuses</option>
            <option value="New">New</option>
            <option value="Contacted">Contacted</option>
            <option value="Replied">Replied</option>
            <option value="Not Interested">Not Interested</option>
          </select>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {!isHistoryView && <StatusPill status={jobStatus} error={error} />}
          <button onClick={handleExportCSV} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: theme.surface, border: `1px solid ${theme.border}`, color: theme.text, padding: '10px 16px', borderRadius: '4px', cursor: 'pointer', fontSize: '13px', fontWeight: '600' }}>
            <Download size={16} /> Export CSV
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '12px' }}>
        {jobStatus === 'completed' && filteredResults.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: theme.textMuted, background: theme.surface, border: `1px dashed ${theme.border}`, borderRadius: '8px', marginTop: '20px' }}>
            <h3 style={{ margin: '0 0 8px', color: theme.text }}>No verified leads found.</h3>
            <p style={{ margin: 0, fontSize: '14px' }}>Try a broader industry keyword or adjust your filters.</p>
          </div>
        )}

        {isHistoryView ? (
          Object.entries(
            filteredResults.reduce((acc, company) => {
              const groupKey = `${company.industry || 'Unknown'} — ${company.location || 'Unknown'}`;
              if (!acc[groupKey]) acc[groupKey] = [];
              acc[groupKey].push(company);
              return acc;
            }, {})
          ).map(([groupKey, companies]) => (
            <div key={groupKey} style={{ marginBottom: '40px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '15px', fontWeight: '700', color: theme.text, margin: 0 }}>{groupKey}</h3>
                <div style={{ height: '1px', flex: 1, backgroundColor: theme.border }}></div>
              </div>
              {companies.map(company => renderCompanyCard(company))}
            </div>
          ))
        ) : (
          filteredResults.map(company => renderCompanyCard(company))
        )}
      </div>
    </div>
  );
}