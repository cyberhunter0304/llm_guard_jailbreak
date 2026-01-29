import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';

const AnalyticsDashboard = () => {
  const [sessions, setSessions] = useState([]);
  const [filteredSessions, setFilteredSessions] = useState([]);
  const [selectedBot, setSelectedBot] = useState(null);
  const [botDetails, setBotDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('overview'); // 'overview', 'analytics', or 'details'
  const [detailsTab, setDetailsTab] = useState('events');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [sortBy, setSortBy] = useState('date-desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(20);
  const [stats, setStats] = useState({
    totalSessions: 0,
    totalPrompts: 0,
    totalBlocked: 0,
    totalPII: 0,
    totalJailbreaks: 0,
    totalToxicity: 0
  });

  const BACKEND_URL = 'http://localhost:8000';

  useEffect(() => {
    fetchAllSessions();
  }, []);

  useEffect(() => {
    filterAndSortSessions();
  }, [sessions, searchTerm, filterType, sortBy]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filterType, sortBy]);

  const fetchAllSessions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/security`);
      const data = await response.json();
      
      setSessions(data.sessions || []);
      
      const totalStats = (data.sessions || []).reduce((acc, session) => ({
        totalSessions: acc.totalSessions + 1,
        totalPrompts: acc.totalPrompts + (session.total_prompts || 0),
        totalBlocked: acc.totalBlocked + (session.blocked_prompts || 0),
        totalPII: acc.totalPII + (session.pii_detections || 0),
        totalJailbreaks: acc.totalJailbreaks + (session.jailbreak_attempts || 0),
        totalToxicity: acc.totalToxicity + (session.toxicity_detections || 0)
      }), {
        totalSessions: 0,
        totalPrompts: 0,
        totalBlocked: 0,
        totalPII: 0,
        totalJailbreaks: 0,
        totalToxicity: 0
      });
      
      setStats(totalStats);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
      setLoading(false);
    }
  };

  const filterAndSortSessions = () => {
    let filtered = [...sessions];

    if (searchTerm) {
      filtered = filtered.filter(session =>
        session.bot_id.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (filterType === 'threats') {
      filtered = filtered.filter(session =>
        session.pii_detections > 0 || 
        session.jailbreak_attempts > 0 || 
        session.toxicity_detections > 0 ||
        session.blocked_prompts > 0
      );
    } else if (filterType === 'clean') {
      filtered = filtered.filter(session =>
        session.pii_detections === 0 && 
        session.jailbreak_attempts === 0 && 
        session.toxicity_detections === 0 &&
        session.blocked_prompts === 0
      );
    } else if (filterType === 'pii') {
      filtered = filtered.filter(session => session.pii_detections > 0);
    }

    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'date-desc':
          return new Date(b.created_at) - new Date(a.created_at);
        case 'date-asc':
          return new Date(a.created_at) - new Date(b.created_at);
        case 'threats-desc':
          const threatsA = (a.pii_detections || 0) + (a.jailbreak_attempts || 0) + (a.toxicity_detections || 0);
          const threatsB = (b.pii_detections || 0) + (b.jailbreak_attempts || 0) + (b.toxicity_detections || 0);
          return threatsB - threatsA;
        case 'prompts-desc':
          return (b.total_prompts || 0) - (a.total_prompts || 0);
        default:
          return 0;
      }
    });

    setFilteredSessions(filtered);
  };

  const fetchBotDetails = async (botId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/security/${botId}`);
      const data = await response.json();
      setBotDetails(data);
      setSelectedBot(botId);
      setView('details');
      setDetailsTab('events');
    } catch (error) {
      console.error('Failed to fetch bot details:', error);
    }
  };

  const deleteBotSession = async (botId) => {
    if (!window.confirm(`Are you sure you want to delete session ${botId.substring(0, 24)}...?`)) {
      return;
    }
    
    try {
      await fetch(`${BACKEND_URL}/api/security/${botId}`, {
        method: 'DELETE'
      });
      fetchAllSessions();
      if (selectedBot === botId) {
        setView('overview');
        setSelectedBot(null);
        setBotDetails(null);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const clearAllSessions = async () => {
    if (!window.confirm('⚠️ Are you sure you want to delete ALL sessions? This action cannot be undone.')) {
      return;
    }
    
    try {
      await Promise.all(sessions.map(session => 
        fetch(`${BACKEND_URL}/api/security/${session.bot_id}`, { method: 'DELETE' })
      ));
      fetchAllSessions();
      setView('overview');
      setSelectedBot(null);
      setBotDetails(null);
    } catch (error) {
      console.error('Failed to clear all sessions:', error);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString();
  };

  const getRelativeTime = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return formatDate(isoString);
  };

  const extractPIIData = (botDetails) => {
    if (!botDetails || !botDetails.security_events) return [];
    
    const piiData = [];
    botDetails.security_events.forEach((event, eventIndex) => {
      if (event.detections?.pii?.detected && event.detections.pii.entities) {
        event.detections.pii.entities.forEach((entity) => {
          piiData.push({
            eventIndex: eventIndex + 1,
            timestamp: event.timestamp,
            type: entity.entity_type || 'Unknown',
            value: entity.text || 'N/A',
            confidence: entity.score || 0,
            prompt: event.prompt
          });
        });
      }
    });
    
    return piiData;
  };

  const exportToCSV = () => {
    const csvData = sessions.map(session => ({
      'Bot ID': session.bot_id,
      'Created': formatDate(session.created_at),
      'Total Prompts': session.total_prompts,
      'Blocked': session.blocked_prompts,
      'PII': session.pii_detections,
      'Jailbreaks': session.jailbreak_attempts,
      'Toxicity': session.toxicity_detections
    }));

    const headers = Object.keys(csvData[0] || {}).join(',');
    const rows = csvData.map(row => Object.values(row).join(',')).join('\n');
    const csv = `${headers}\n${rows}`;
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security-analytics-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  // Chart data preparation
  const getThreatDistributionData = () => {
    const cleanSessions = sessions.filter(s => 
      s.pii_detections === 0 && s.jailbreak_attempts === 0 && s.toxicity_detections === 0
    ).length;
    
    return [
      { name: 'PII Detected', value: stats.totalPII, color: '#f59e0b' },
      { name: 'Jailbreak Attempts', value: stats.totalJailbreaks, color: '#ef4444' },
      { name: 'Toxicity', value: stats.totalToxicity, color: '#dc2626' },
      { name: 'Clean Sessions', value: cleanSessions, color: '#10b981' }
    ].filter(item => item.value > 0);
  };

  const getTimelineData = () => {
    const grouped = sessions.reduce((acc, session) => {
      const date = new Date(session.created_at).toLocaleDateString();
      if (!acc[date]) {
        acc[date] = { date, sessions: 0, threats: 0, prompts: 0 };
      }
      acc[date].sessions += 1;
      acc[date].prompts += session.total_prompts || 0;
      acc[date].threats += (session.pii_detections || 0) + (session.jailbreak_attempts || 0) + (session.toxicity_detections || 0);
      return acc;
    }, {});

    return Object.values(grouped).sort((a, b) => new Date(a.date) - new Date(b.date)).slice(-14);
  };

  const getThreatTypeData = () => {
    return [
      { name: 'PII', count: stats.totalPII, color: '#f59e0b' },
      { name: 'Jailbreak', count: stats.totalJailbreaks, color: '#ef4444' },
      { name: 'Toxicity', count: stats.totalToxicity, color: '#dc2626' }
    ].filter(item => item.count > 0);
  };

  const getTopThreateningSessions = () => {
    return [...sessions]
      .map(s => ({
        id: s.bot_id.substring(0, 12) + '...',
        threats: (s.pii_detections || 0) + (s.jailbreak_attempts || 0) + (s.toxicity_detections || 0)
      }))
      .filter(s => s.threats > 0)
      .sort((a, b) => b.threats - a.threats)
      .slice(0, 10);
  };

  // Pagination
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredSessions.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(filteredSessions.length / itemsPerPage);

  const paginate = (pageNumber) => setCurrentPage(pageNumber);

  const StatCard = ({ icon, label, value, color }) => (
    <div className="stat-card" style={{ borderLeftColor: color }}>
      <div className="stat-icon" style={{ color }}>{icon}</div>
      <div className="stat-content">
        <div className="stat-value">{value.toLocaleString()}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );

  const ThreatBadge = ({ type, count }) => {
    const colors = {
      pii: '#f59e0b',
      jailbreak: '#ef4444',
      toxicity: '#dc2626'
    };
    
    const labels = {
      pii: 'PII',
      jailbreak: 'JB',
      toxicity: 'TOX'
    };
    
    if (count === 0) return null;
    
    return (
      <span className="threat-badge" style={{ backgroundColor: colors[type] }}>
        {labels[type]}: {count}
      </span>
    );
  };

  return (
    <>
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          background: #f8fafc;
        }

        .dashboard-container {
          min-height: 100vh;
          padding: 24px;
          max-width: 1600px;
          margin: 0 auto;
        }

        .dashboard-header {
          background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
          color: white;
          padding: 32px;
          border-radius: 20px;
          margin-bottom: 28px;
          box-shadow: 0 8px 24px rgba(255, 107, 53, 0.25);
          position: relative;
          overflow: hidden;
        }

        .dashboard-header::before {
          content: '';
          position: absolute;
          top: 0;
          right: 0;
          width: 400px;
          height: 400px;
          background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
          border-radius: 50%;
          transform: translate(30%, -30%);
        }

        .header-content {
          position: relative;
          z-index: 1;
        }

        .dashboard-title {
          font-size: 32px;
          font-weight: 800;
          margin-bottom: 8px;
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .dashboard-subtitle {
          font-size: 16px;
          opacity: 0.95;
        }

        .header-stats {
          display: flex;
          gap: 32px;
          margin-top: 20px;
          padding-top: 20px;
          border-top: 1px solid rgba(255,255,255,0.2);
        }

        .header-stat {
          display: flex;
          flex-direction: column;
        }

        .header-stat-value {
          font-size: 28px;
          font-weight: 700;
        }

        .header-stat-label {
          font-size: 13px;
          opacity: 0.9;
          margin-top: 4px;
        }

        .view-toggle {
          display: flex;
          gap: 12px;
          margin-bottom: 24px;
        }

        .toggle-btn {
          padding: 12px 24px;
          border: none;
          border-radius: 12px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
          background: white;
          color: #6b7280;
          box-shadow: 0 2px 4px rgba(0,0,0,0.06);
        }

        .toggle-btn.active {
          background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
          color: white;
          box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
        }

        .toggle-btn:hover:not(.active) {
          background: #f9fafb;
          color: #FF6B35;
          transform: translateY(-2px);
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
          margin-bottom: 28px;
        }

        .stat-card {
          background: white;
          padding: 24px;
          border-radius: 16px;
          border-left: 4px solid;
          box-shadow: 0 2px 8px rgba(0,0,0,0.06);
          display: flex;
          gap: 16px;
          align-items: center;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .stat-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }

        .stat-icon {
          font-size: 36px;
          width: 56px;
          height: 56px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(255, 107, 53, 0.1);
          border-radius: 14px;
        }

        .stat-content {
          flex: 1;
        }

        .stat-value {
          font-size: 32px;
          font-weight: 700;
          color: #1f2937;
        }

        .stat-label {
          font-size: 14px;
          color: #6b7280;
          font-weight: 500;
          margin-top: 4px;
        }

        .charts-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
          gap: 24px;
          margin-bottom: 28px;
        }

        .chart-container {
          background: white;
          padding: 24px;
          border-radius: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }

        .chart-title {
          font-size: 18px;
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 20px;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .controls-section {
          background: white;
          padding: 20px;
          border-radius: 16px;
          margin-bottom: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }

        .controls-row {
          display: flex;
          gap: 16px;
          align-items: center;
          flex-wrap: wrap;
        }

        .search-box {
          flex: 1;
          min-width: 250px;
          position: relative;
        }

        .search-icon {
          position: absolute;
          left: 14px;
          top: 50%;
          transform: translateY(-50%);
          color: #9ca3af;
          font-size: 18px;
        }

        .search-input {
          width: 100%;
          padding: 12px 16px 12px 44px;
          border: 2px solid #e5e7eb;
          border-radius: 10px;
          font-size: 15px;
          transition: all 0.2s;
        }

        .search-input:focus {
          outline: none;
          border-color: #FF6B35;
          box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1);
        }

        .filter-group {
          display: flex;
          gap: 8px;
        }

        .filter-btn {
          padding: 10px 18px;
          border: 2px solid #e5e7eb;
          background: white;
          border-radius: 10px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          color: #6b7280;
        }

        .filter-btn:hover {
          border-color: #FF6B35;
          color: #FF6B35;
        }

        .filter-btn.active {
          background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
          color: white;
          border-color: transparent;
        }

        .select-wrapper {
          position: relative;
        }

        .sort-select {
          padding: 10px 36px 10px 16px;
          border: 2px solid #e5e7eb;
          border-radius: 10px;
          font-size: 14px;
          font-weight: 600;
          background: white;
          color: #374151;
          cursor: pointer;
          appearance: none;
          transition: all 0.2s;
        }

        .sort-select:focus {
          outline: none;
          border-color: #FF6B35;
        }

        .select-arrow {
          position: absolute;
          right: 12px;
          top: 50%;
          transform: translateY(-50%);
          pointer-events: none;
          color: #6b7280;
        }

        .action-buttons {
          display: flex;
          gap: 8px;
        }

        .icon-btn {
          padding: 10px 16px;
          border: 2px solid #e5e7eb;
          background: white;
          border-radius: 10px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          gap: 6px;
          color: #374151;
        }

        .icon-btn:hover {
          border-color: #FF6B35;
          color: #FF6B35;
        }

        .icon-btn.danger:hover {
          border-color: #ef4444;
          color: #ef4444;
          background: #fef2f2;
        }

        .results-info {
          margin-top: 12px;
          color: #6b7280;
          font-size: 14px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .pagination {
          display: flex;
          gap: 8px;
          align-items: center;
        }

        .page-btn {
          padding: 8px 12px;
          border: 2px solid #e5e7eb;
          background: white;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          color: #374151;
          min-width: 40px;
        }

        .page-btn:hover:not(:disabled) {
          border-color: #FF6B35;
          color: #FF6B35;
        }

        .page-btn.active {
          background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
          color: white;
          border-color: transparent;
        }

        .page-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .page-info {
          font-size: 14px;
          color: #6b7280;
          padding: 0 8px;
        }

        .sessions-container {
          background: white;
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }

        .section-title {
          font-size: 20px;
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 20px;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .sessions-table {
          width: 100%;
          border-collapse: collapse;
        }

        .sessions-table th {
          text-align: left;
          padding: 14px;
          background: #f9fafb;
          color: #6b7280;
          font-weight: 600;
          font-size: 13px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          border-bottom: 2px solid #e5e7eb;
        }

        .sessions-table td {
          padding: 16px 14px;
          border-bottom: 1px solid #f3f4f6;
          color: #374151;
        }

        .sessions-table tbody tr {
          cursor: pointer;
          transition: all 0.2s;
        }

        .sessions-table tbody tr:hover {
          background: #fffbeb;
          transform: scale(1.01);
          box-shadow: 0 2px 8px rgba(255, 107, 53, 0.15);
        }

        .bot-id {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          background: #f3f4f6;
          padding: 6px 10px;
          border-radius: 6px;
          font-size: 13px;
          color: #374151;
          font-weight: 600;
        }

        .time-info {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .time-relative {
          font-size: 14px;
          font-weight: 600;
          color: #374151;
        }

        .time-absolute {
          font-size: 12px;
          color: #9ca3af;
        }

        .threat-badges {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }

        .threat-badge {
          padding: 5px 10px;
          border-radius: 12px;
          color: white;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.3px;
        }

        .details-container {
          background: white;
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }

        .back-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 20px;
          background: #f3f4f6;
          color: #374151;
          border: none;
          border-radius: 10px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }

        .back-btn:hover {
          background: #FF6B35;
          color: white;
          transform: translateX(-4px);
        }

        .btn-delete-session {
          padding: 10px 20px;
          background: #ef4444;
          color: white;
          border: none;
          border-radius: 10px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .btn-delete-session:hover {
          background: #dc2626;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        }

        .details-tabs {
          display: flex;
          gap: 12px;
          margin-bottom: 24px;
          border-bottom: 2px solid #f3f4f6;
        }

        .tab-btn {
          padding: 12px 24px;
          border: none;
          background: transparent;
          color: #6b7280;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          transition: all 0.3s;
          margin-bottom: -2px;
        }

        .tab-btn.active {
          color: #FF6B35;
          border-bottom-color: #FF6B35;
        }

        .tab-btn:hover:not(.active) {
          color: #374151;
        }

        .bot-info-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
          padding: 20px;
          background: #f9fafb;
          border-radius: 12px;
        }

        .info-item {
          display: flex;
          flex-direction: column;
        }

        .info-label {
          font-size: 12px;
          color: #6b7280;
          font-weight: 600;
          text-transform: uppercase;
          margin-bottom: 4px;
        }

        .info-value {
          font-size: 16px;
          color: #1f2937;
          font-weight: 600;
        }

        .events-list {
          margin-top: 24px;
        }

        .event-card {
          background: #f9fafb;
          border-left: 4px solid;
          padding: 20px;
          border-radius: 10px;
          margin-bottom: 16px;
          transition: all 0.2s;
        }

        .event-card:hover {
          transform: translateX(4px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }

        .event-card.safe {
          border-left-color: #10b981;
        }

        .event-card.blocked {
          border-left-color: #ef4444;
        }

        .event-card.pii {
          border-left-color: #f59e0b;
        }

        .event-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .event-timestamp {
          font-size: 13px;
          color: #6b7280;
        }

        .event-status {
          padding: 6px 14px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 700;
          color: white;
        }

        .event-status.safe {
          background: #10b981;
        }

        .event-status.blocked {
          background: #ef4444;
        }

        .event-status.pii-detected {
          background: #f59e0b;
        }

        .event-content {
          margin-top: 12px;
        }

        .event-section {
          margin-bottom: 12px;
        }

        .event-section-title {
          font-size: 12px;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          margin-bottom: 6px;
        }

        .event-text {
          background: white;
          padding: 12px;
          border-radius: 8px;
          font-size: 14px;
          color: #374151;
          border: 1px solid #e5e7eb;
          line-height: 1.5;
        }

        .detection-tags {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-top: 8px;
        }

        .detection-tag {
          padding: 6px 12px;
          border-radius: 8px;
          font-size: 12px;
          font-weight: 600;
        }

        .detection-tag.prompt-injection {
          background: #fee2e2;
          color: #991b1b;
        }

        .detection-tag.toxicity {
          background: #fef3c7;
          color: #92400e;
        }

        .detection-tag.pii {
          background: #fef3c7;
          color: #92400e;
        }

        .detection-tag.safe {
          background: #d1fae5;
          color: #065f46;
        }

        .pii-table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 20px;
        }

        .pii-table th {
          text-align: left;
          padding: 14px;
          background: #fef3c7;
          color: #92400e;
          font-weight: 600;
          font-size: 13px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          border-bottom: 2px solid #f59e0b;
        }

        .pii-table td {
          padding: 16px 14px;
          border-bottom: 1px solid #fef3c7;
          color: #374151;
        }

        .pii-table tbody tr:hover {
          background: #fffbeb;
        }

        .pii-type {
          display: inline-block;
          padding: 4px 12px;
          background: #fef3c7;
          color: #92400e;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
        }

        .pii-value {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          background: #fef3c7;
          padding: 4px 8px;
          border-radius: 4px;
          color: #92400e;
          font-weight: 600;
        }

        .confidence-bar {
          width: 100%;
          height: 8px;
          background: #f3f4f6;
          border-radius: 4px;
          overflow: hidden;
        }

        .confidence-fill {
          height: 100%;
          background: linear-gradient(90deg, #f59e0b, #d97706);
          transition: width 0.3s;
        }

        .confidence-text {
          font-size: 12px;
          color: #6b7280;
          margin-top: 4px;
        }

        .pii-prompt-preview {
          font-size: 13px;
          color: #6b7280;
          max-width: 300px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .loading {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 400px;
          font-size: 18px;
          color: #6b7280;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #f3f4f6;
          border-top-color: #FF6B35;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-right: 12px;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: #6b7280;
        }

        .empty-state-icon {
          font-size: 64px;
          margin-bottom: 16px;
        }

        .empty-state-title {
          font-size: 20px;
          font-weight: 600;
          margin-bottom: 8px;
          color: #374151;
        }

        @media (max-width: 1024px) {
          .charts-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 768px) {
          .dashboard-container {
            padding: 16px;
          }

          .dashboard-title {
            font-size: 24px;
          }

          .header-stats {
            flex-direction: column;
            gap: 16px;
          }

          .controls-row {
            flex-direction: column;
          }

          .search-box {
            width: 100%;
          }

          .filter-group,
          .action-buttons {
            width: 100%;
            flex-wrap: wrap;
          }

          .stats-grid {
            grid-template-columns: 1fr;
          }

          .sessions-table {
            font-size: 12px;
          }

          .sessions-table th,
          .sessions-table td {
            padding: 10px 8px;
          }

          .bot-info-grid {
            grid-template-columns: 1fr;
          }

          .pagination {
            flex-wrap: wrap;
          }
        }
      `}</style>

      <div className="dashboard-container">
        <div className="dashboard-header">
          <div className="header-content">
            <div className="dashboard-title">
              <span>🛡️</span>
              <span>Security Analytics Dashboard</span>
            </div>
            <div className="dashboard-subtitle">
              Real-time monitoring of AI security guardrails and threat detection
            </div>
            <div className="header-stats">
              <div className="header-stat">
                <div className="header-stat-value">{stats.totalSessions.toLocaleString()}</div>
                <div className="header-stat-label">Active Sessions</div>
              </div>
              <div className="header-stat">
                <div className="header-stat-value">{stats.totalPrompts.toLocaleString()}</div>
                <div className="header-stat-label">Total Prompts</div>
              </div>
              <div className="header-stat">
                <div className="header-stat-value">{stats.totalBlocked.toLocaleString()}</div>
                <div className="header-stat-label">Blocked Threats</div>
              </div>
            </div>
          </div>
        </div>

        <div className="view-toggle">
          <button 
            className={`toggle-btn ${view === 'overview' ? 'active' : ''}`}
            onClick={() => setView('overview')}
          >
            📋 Sessions
          </button>
          <button 
            className={`toggle-btn ${view === 'analytics' ? 'active' : ''}`}
            onClick={() => setView('analytics')}
          >
            📊 Analytics
          </button>
          {selectedBot && (
            <button 
              className={`toggle-btn ${view === 'details' ? 'active' : ''}`}
              onClick={() => setView('details')}
            >
              🔍 Session Details
            </button>
          )}
        </div>

        {loading ? (
          <div className="loading">
            <div className="loading-spinner"></div>
            Loading analytics data...
          </div>
        ) : (
          <>
            {view === 'overview' ? (
              <>
                <div className="stats-grid">
                  <StatCard icon="💬" label="Total Sessions" value={stats.totalSessions} color="#3b82f6" />
                  <StatCard icon="📝" label="Total Prompts" value={stats.totalPrompts} color="#10b981" />
                  <StatCard icon="🚫" label="Blocked Prompts" value={stats.totalBlocked} color="#ef4444" />
                  <StatCard icon="🔒" label="PII Detections" value={stats.totalPII} color="#f59e0b" />
                  <StatCard icon="⚠️" label="Jailbreak Attempts" value={stats.totalJailbreaks} color="#dc2626" />
                  <StatCard icon="☣️" label="Toxicity Detected" value={stats.totalToxicity} color="#991b1b" />
                </div>

                <div className="controls-section">
                  <div className="controls-row">
                    <div className="search-box">
                      <div className="search-icon">🔍</div>
                      <input
                        type="text"
                        className="search-input"
                        placeholder="Search by Bot ID..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                    </div>

                    <div className="filter-group">
                      <button className={`filter-btn ${filterType === 'all' ? 'active' : ''}`} onClick={() => setFilterType('all')}>All</button>
                      <button className={`filter-btn ${filterType === 'threats' ? 'active' : ''}`} onClick={() => setFilterType('threats')}>⚠️ Threats</button>
                      <button className={`filter-btn ${filterType === 'pii' ? 'active' : ''}`} onClick={() => setFilterType('pii')}>🔒 PII</button>
                      <button className={`filter-btn ${filterType === 'clean' ? 'active' : ''}`} onClick={() => setFilterType('clean')}>✅ Clean</button>
                    </div>

                    <div className="select-wrapper">
                      <select className="sort-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                        <option value="date-desc">Newest First</option>
                        <option value="date-asc">Oldest First</option>
                        <option value="threats-desc">Most Threats</option>
                        <option value="prompts-desc">Most Prompts</option>
                      </select>
                      <span className="select-arrow">▼</span>
                    </div>

                    <div className="action-buttons">
                      <button className="icon-btn" onClick={exportToCSV}>📥 Export</button>
                      <button className="icon-btn" onClick={fetchAllSessions}>🔄 Refresh</button>
                      {sessions.length > 0 && (
                        <button className="icon-btn danger" onClick={clearAllSessions}>🗑️ Clear All</button>
                      )}
                    </div>
                  </div>

                  <div className="results-info">
                    <div>
                      Showing {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, filteredSessions.length)} of {filteredSessions.length} sessions
                    </div>
                    {totalPages > 1 && (
                      <div className="pagination">
                        <button className="page-btn" onClick={() => paginate(currentPage - 1)} disabled={currentPage === 1}>←</button>
                        {[...Array(Math.min(5, totalPages))].map((_, i) => {
                          let pageNum;
                          if (totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (currentPage <= 3) {
                            pageNum = i + 1;
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                          } else {
                            pageNum = currentPage - 2 + i;
                          }
                          return (
                            <button key={pageNum} className={`page-btn ${currentPage === pageNum ? 'active' : ''}`} onClick={() => paginate(pageNum)}>
                              {pageNum}
                            </button>
                          );
                        })}
                        {totalPages > 5 && <span className="page-info">... {totalPages}</span>}
                        <button className="page-btn" onClick={() => paginate(currentPage + 1)} disabled={currentPage === totalPages}>→</button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="sessions-container">
                  <div className="section-title">🤖 Bot Sessions ({filteredSessions.length})</div>

                  {filteredSessions.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-state-icon">{searchTerm || filterType !== 'all' ? '🔍' : '📭'}</div>
                      <div className="empty-state-title">{searchTerm || filterType !== 'all' ? 'No matching sessions' : 'No sessions yet'}</div>
                      <div>{searchTerm || filterType !== 'all' ? 'Try adjusting your search or filters' : 'Start a chat to see security analytics here'}</div>
                    </div>
                  ) : (
                    <table className="sessions-table">
                      <thead>
                        <tr>
                          <th>Bot ID</th>
                          <th>Created</th>
                          <th>Prompts</th>
                          <th>Threats Detected</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentItems.map((session) => (
                          <tr key={session.bot_id} onClick={() => fetchBotDetails(session.bot_id)}>
                            <td><span className="bot-id">{session.bot_id.substring(0, 24)}...</span></td>
                            <td>
                              <div className="time-info">
                                <div className="time-relative">{getRelativeTime(session.created_at)}</div>
                                <div className="time-absolute">{formatDate(session.created_at)}</div>
                              </div>
                            </td>
                            <td>
                              <strong>{session.total_prompts}</strong>
                              {session.blocked_prompts > 0 && (
                                <span style={{ color: '#ef4444', marginLeft: 8, fontSize: 13 }}>({session.blocked_prompts} blocked)</span>
                              )}
                            </td>
                            <td>
                              <div className="threat-badges">
                                <ThreatBadge type="pii" count={session.pii_detections} />
                                <ThreatBadge type="jailbreak" count={session.jailbreak_attempts} />
                                <ThreatBadge type="toxicity" count={session.toxicity_detections} />
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </>
            ) : view === 'analytics' ? (
              <>
                {/* Analytics View - Charts and Visualizations */}
                <div className="stats-grid">
                  <StatCard icon="💬" label="Total Sessions" value={stats.totalSessions} color="#3b82f6" />
                  <StatCard icon="📝" label="Total Prompts" value={stats.totalPrompts} color="#10b981" />
                  <StatCard icon="🚫" label="Blocked Prompts" value={stats.totalBlocked} color="#ef4444" />
                  <StatCard icon="🔒" label="PII Detections" value={stats.totalPII} color="#f59e0b" />
                  <StatCard icon="⚠️" label="Jailbreak Attempts" value={stats.totalJailbreaks} color="#dc2626" />
                  <StatCard icon="☣️" label="Toxicity Detected" value={stats.totalToxicity} color="#991b1b" />
                </div>

                <div className="charts-grid">
                  <div className="chart-container">
                    <div className="chart-title">📊 Threat Distribution</div>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={getThreatDistributionData()}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, value }) => value > 0 ? `${name}: ${value}` : ''}
                          outerRadius={100}
                          dataKey="value"
                        >
                          {getThreatDistributionData().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="chart-container">
                    <div className="chart-title">📈 Activity Timeline (Last 14 Days)</div>
                    <ResponsiveContainer width="100%" height={300}>
                      <AreaChart data={getTimelineData()}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Area type="monotone" dataKey="sessions" stackId="1" stroke="#3b82f6" fill="#3b82f6" name="Sessions" />
                        <Area type="monotone" dataKey="threats" stackId="1" stroke="#ef4444" fill="#ef4444" name="Threats" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="chart-container">
                    <div className="chart-title">⚠️ Threat Types Breakdown</div>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={getThreatTypeData()}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="count" name="Detections">
                          {getThreatTypeData().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="chart-container">
                    <div className="chart-title">🔥 Top Threatening Sessions</div>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={getTopThreateningSessions()} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" />
                        <YAxis dataKey="id" type="category" width={100} tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Bar dataKey="threats" fill="#ef4444" name="Total Threats" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Additional Analytics Info */}
                <div className="sessions-container">
                  <div className="section-title">📊 Analytics Summary</div>
                  <div style={{ padding: '20px', color: '#6b7280', lineHeight: '1.8' }}>
                    <p><strong>Detection Rate:</strong> {stats.totalSessions > 0 ? ((stats.totalBlocked / stats.totalPrompts * 100) || 0).toFixed(2) : 0}% of prompts were blocked</p>
                    <p><strong>PII Detection Rate:</strong> {stats.totalSessions > 0 ? ((sessions.filter(s => s.pii_detections > 0).length / stats.totalSessions * 100) || 0).toFixed(2) : 0}% of sessions contained PII</p>
                    <p><strong>Average Prompts per Session:</strong> {stats.totalSessions > 0 ? (stats.totalPrompts / stats.totalSessions).toFixed(2) : 0}</p>
                    <p><strong>Clean Sessions:</strong> {sessions.filter(s => s.pii_detections === 0 && s.jailbreak_attempts === 0 && s.toxicity_detections === 0 && s.blocked_prompts === 0).length} ({stats.totalSessions > 0 ? ((sessions.filter(s => s.pii_detections === 0 && s.jailbreak_attempts === 0 && s.toxicity_detections === 0 && s.blocked_prompts === 0).length / stats.totalSessions * 100) || 0).toFixed(2) : 0}%)</p>
                  </div>
                </div>
              </>
            ) : (
              botDetails && (
                <div className="details-container">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                    <button className="back-btn" onClick={() => setView('overview')}>← Back to Overview</button>
                    <button className="btn-delete-session" onClick={() => deleteBotSession(selectedBot)}>🗑️ Delete Session</button>
                  </div>

                  <div className="section-title">🔍 Session Details: {selectedBot.substring(0, 30)}...</div>

                  <div className="bot-info-grid">
                    <div className="info-item">
                      <div className="info-label">Bot ID</div>
                      <div className="info-value" style={{ fontSize: 13, fontFamily: 'monospace' }}>{botDetails.bot_id}</div>
                    </div>
                    <div className="info-item">
                      <div className="info-label">Created</div>
                      <div className="info-value">{formatDate(botDetails.created_at)}</div>
                    </div>
                    <div className="info-item">
                      <div className="info-label">Last Updated</div>
                      <div className="info-value">{formatDate(botDetails.last_updated)}</div>
                    </div>
                    <div className="info-item">
                      <div className="info-label">Total Prompts</div>
                      <div className="info-value">{botDetails.total_prompts}</div>
                    </div>
                    <div className="info-item">
                      <div className="info-label">Blocked</div>
                      <div className="info-value" style={{ color: '#ef4444' }}>{botDetails.blocked_prompts}</div>
                    </div>
                    <div className="info-item">
                      <div className="info-label">PII Detected</div>
                      <div className="info-value" style={{ color: '#f59e0b' }}>{botDetails.pii_detections}</div>
                    </div>
                  </div>

                  <div className="details-tabs">
                    <button className={`tab-btn ${detailsTab === 'events' ? 'active' : ''}`} onClick={() => setDetailsTab('events')}>
                      📋 Security Events
                    </button>
                    <button className={`tab-btn ${detailsTab === 'pii' ? 'active' : ''}`} onClick={() => setDetailsTab('pii')}>
                      🔒 PII Details
                    </button>
                  </div>

                  {detailsTab === 'events' ? (
                    <div className="events-list">
                      <div className="section-title">📋 Security Events ({botDetails.security_events?.length || 0})</div>

                      {botDetails.security_events?.length === 0 ? (
                        <div className="empty-state">
                          <div className="empty-state-icon">📭</div>
                          <div>No events recorded for this session</div>
                        </div>
                      ) : (
                        botDetails.security_events?.map((event, index) => {
                          const hasPII = event.detections?.pii?.detected;
                          const isBlocked = event.blocked;
                          
                          return (
                            <div key={index} className={`event-card ${isBlocked ? 'blocked' : hasPII ? 'pii' : 'safe'}`}>
                              <div className="event-header">
                                <div className="event-timestamp">🕐 {formatDate(event.timestamp)}</div>
                                <div className={`event-status ${isBlocked ? 'blocked' : hasPII ? 'pii-detected' : 'safe'}`}>
                                  {isBlocked ? '🚫 BLOCKED' : hasPII ? '🔒 PII DETECTED' : '✅ SAFE'}
                                </div>
                              </div>

                              <div className="event-content">
                                <div className="event-section">
                                  <div className="event-section-title">Original Prompt</div>
                                  <div className="event-text">{event.prompt}</div>
                                </div>

                                {event.anonymized_prompt && (
                                  <div className="event-section">
                                    <div className="event-section-title">Anonymized Prompt</div>
                                    <div className="event-text">{event.anonymized_prompt}</div>
                                  </div>
                                )}

                                {event.llm_response && (
                                  <div className="event-section">
                                    <div className="event-section-title">LLM Response</div>
                                    <div className="event-text">{event.llm_response}</div>
                                  </div>
                                )}

                                {event.block_reason && (
                                  <div className="event-section">
                                    <div className="event-section-title">Block Reason</div>
                                    <div className="event-text" style={{ color: '#ef4444' }}>{event.block_reason}</div>
                                  </div>
                                )}

                                <div className="detection-tags">
                                  {event.detections?.prompt_injection?.detected && (
                                    <div className="detection-tag prompt-injection">
                                      ⚠️ Prompt Injection (Risk: {(event.detections.prompt_injection.risk_score * 100).toFixed(0)}%)
                                    </div>
                                  )}
                                  {event.detections?.toxicity?.detected && (
                                    <div className="detection-tag toxicity">
                                      ☣️ Toxicity (Risk: {(event.detections.toxicity.risk_score * 100).toFixed(0)}%)
                                    </div>
                                  )}
                                  {event.detections?.pii?.detected && (
                                    <div className="detection-tag pii">
                                      🔒 PII: {event.detections.pii.entity_types?.join(', ')} ({event.detections.pii.entity_count} entities)
                                    </div>
                                  )}
                                  {!event.detections?.prompt_injection?.detected && 
                                   !event.detections?.toxicity?.detected && 
                                   !event.detections?.pii?.detected && (
                                    <div className="detection-tag safe">✅ No Threats Detected</div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  ) : (
                    <div className="pii-details">
                      <div className="section-title">🔒 PII Entities Detected ({extractPIIData(botDetails).length})</div>

                      {extractPIIData(botDetails).length === 0 ? (
                        <div className="empty-state">
                          <div className="empty-state-icon">🔓</div>
                          <div className="empty-state-title">No PII Detected</div>
                          <div>This session has no personally identifiable information</div>
                        </div>
                      ) : (
                        <table className="pii-table">
                          <thead>
                            <tr>
                              <th>Event #</th>
                              <th>Type</th>
                              <th>Value</th>
                              <th>Confidence</th>
                              <th>Timestamp</th>
                              <th>Prompt Context</th>
                            </tr>
                          </thead>
                          <tbody>
                            {extractPIIData(botDetails).map((pii, index) => (
                              <tr key={index}>
                                <td><strong>#{pii.eventIndex}</strong></td>
                                <td><span className="pii-type">{pii.type}</span></td>
                                <td><span className="pii-value">{pii.value}</span></td>
                                <td>
                                  <div className="confidence-bar">
                                    <div className="confidence-fill" style={{ width: `${pii.confidence * 100}%` }} />
                                  </div>
                                  <div className="confidence-text">{(pii.confidence * 100).toFixed(1)}%</div>
                                </td>
                                <td>{formatDate(pii.timestamp)}</td>
                                <td>
                                  <div className="pii-prompt-preview" title={pii.prompt}>{pii.prompt}</div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}
                </div>
              )
            )}
          </>
        )}
      </div>
    </>
  );
};

export default AnalyticsDashboard;