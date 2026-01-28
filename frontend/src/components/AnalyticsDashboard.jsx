import React, { useState, useEffect } from 'react';

const AnalyticsDashboard = () => {
  const [sessions, setSessions] = useState([]);
  const [selectedBot, setSelectedBot] = useState(null);
  const [botDetails, setBotDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('overview'); // 'overview' or 'details'
  const [detailsTab, setDetailsTab] = useState('events'); // 'events' or 'pii'
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

  const fetchAllSessions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/security`);
      const data = await response.json();
      
      setSessions(data.sessions || []);
      
      // Calculate overall statistics
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

  const fetchBotDetails = async (botId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/security/${botId}`);
      const data = await response.json();
      setBotDetails(data);
      setSelectedBot(botId);
      setView('details');
      setDetailsTab('events'); // Reset to events tab when viewing new bot
    } catch (error) {
      console.error('Failed to fetch bot details:', error);
    }
  };

  const deleteBotSession = async (botId) => {
    if (!window.confirm(`Are you sure you want to delete session ${botId}?`)) {
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

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString();
  };

  // Extract all PII entities from security events
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

  const StatCard = ({ icon, label, value, color }) => (
    <div className="stat-card" style={{ borderLeftColor: color }}>
      <div className="stat-icon" style={{ color }}>{icon}</div>
      <div className="stat-content">
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );

  const ThreatBadge = ({ type, count }) => {
    const colors = {
      pii: '#f59e0b',
      jailbreak: '#ef4444',
      toxicity: '#dc2626',
      blocked: '#991b1b'
    };
    
    if (count === 0) return null;
    
    return (
      <span className="threat-badge" style={{ backgroundColor: colors[type] }}>
        {count}
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
          background: #f3f4f6;
        }

        .dashboard-container {
          min-height: 100vh;
          padding: 20px;
        }

        .dashboard-header {
          background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
          color: white;
          padding: 30px;
          border-radius: 16px;
          margin-bottom: 30px;
          box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
        }

        .dashboard-title {
          font-size: 32px;
          font-weight: 800;
          margin-bottom: 8px;
        }

        .dashboard-subtitle {
          font-size: 16px;
          opacity: 0.95;
        }

        .view-toggle {
          display: flex;
          gap: 12px;
          margin-bottom: 24px;
        }

        .toggle-btn {
          padding: 12px 24px;
          border: none;
          border-radius: 10px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
          background: white;
          color: #6b7280;
        }

        .toggle-btn.active {
          background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
          color: white;
          box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
        }

        .toggle-btn:hover:not(.active) {
          background: #f3f4f6;
          color: #FF6B35;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
          margin-bottom: 30px;
        }

        .stat-card {
          background: white;
          padding: 24px;
          border-radius: 14px;
          border-left: 4px solid;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          display: flex;
          gap: 16px;
          align-items: center;
        }

        .stat-icon {
          font-size: 36px;
          width: 50px;
          height: 50px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(255, 107, 53, 0.1);
          border-radius: 12px;
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

        .sessions-container {
          background: white;
          border-radius: 14px;
          padding: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
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
        }

        .sessions-table td {
          padding: 16px 14px;
          border-top: 1px solid #f3f4f6;
          color: #374151;
        }

        .sessions-table tbody tr {
          cursor: pointer;
          transition: background 0.2s;
        }

        .sessions-table tbody tr:hover {
          background: #fef3c7;
        }

        .bot-id {
          font-family: monospace;
          background: #f3f4f6;
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 12px;
        }

        .threat-badges {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }

        .threat-badge {
          padding: 4px 10px;
          border-radius: 12px;
          color: white;
          font-size: 12px;
          font-weight: 600;
        }

        .action-btns {
          display: flex;
          gap: 8px;
        }

        .btn {
          padding: 8px 16px;
          border: none;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-view {
          background: #3b82f6;
          color: white;
        }

        .btn-view:hover {
          background: #2563eb;
        }

        .btn-delete {
          background: #ef4444;
          color: white;
        }

        .btn-delete:hover {
          background: #dc2626;
        }

        .details-container {
          background: white;
          border-radius: 14px;
          padding: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .back-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 20px;
          background: #f3f4f6;
          color: #374151;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          margin-bottom: 20px;
          transition: all 0.2s;
        }

        .back-btn:hover {
          background: #FF6B35;
          color: white;
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
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
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
          font-family: monospace;
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

        @media (max-width: 768px) {
          .dashboard-title {
            font-size: 24px;
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

          .pii-table {
            font-size: 12px;
          }

          .pii-table th,
          .pii-table td {
            padding: 10px 8px;
          }
        }
      `}</style>

      <div className="dashboard-container">
        {/* Header */}
        <div className="dashboard-header">
          <div className="dashboard-title">🛡️ Security Analytics Dashboard</div>
          <div className="dashboard-subtitle">
            Real-time monitoring of AI security guardrails and threat detection
          </div>
        </div>

        {/* View Toggle */}
        <div className="view-toggle">
          <button 
            className={`toggle-btn ${view === 'overview' ? 'active' : ''}`}
            onClick={() => setView('overview')}
          >
            📊 Overview
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
          <div className="loading">Loading analytics data...</div>
        ) : (
          <>
            {view === 'overview' ? (
              <>
                {/* Overall Statistics */}
                <div className="stats-grid">
                  <StatCard 
                    icon="💬" 
                    label="Total Sessions" 
                    value={stats.totalSessions}
                    color="#3b82f6"
                  />
                  <StatCard 
                    icon="📝" 
                    label="Total Prompts" 
                    value={stats.totalPrompts}
                    color="#10b981"
                  />
                  <StatCard 
                    icon="🚫" 
                    label="Blocked Prompts" 
                    value={stats.totalBlocked}
                    color="#ef4444"
                  />
                  <StatCard 
                    icon="🔒" 
                    label="PII Detections" 
                    value={stats.totalPII}
                    color="#f59e0b"
                  />
                  <StatCard 
                    icon="⚠️" 
                    label="Jailbreak Attempts" 
                    value={stats.totalJailbreaks}
                    color="#dc2626"
                  />
                  <StatCard 
                    icon="☣️" 
                    label="Toxicity Detected" 
                    value={stats.totalToxicity}
                    color="#991b1b"
                  />
                </div>

                {/* Sessions List */}
                <div className="sessions-container">
                  <div className="section-title">
                    🤖 Bot Sessions ({sessions.length})
                  </div>

                  {sessions.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-state-icon">📭</div>
                      <div className="empty-state-title">No sessions yet</div>
                      <div>Start a chat to see security analytics here</div>
                    </div>
                  ) : (
                    <table className="sessions-table">
                      <thead>
                        <tr>
                          <th>Bot ID</th>
                          <th>Created</th>
                          <th>Prompts</th>
                          <th>Threats Detected</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sessions.map((session) => (
                          <tr key={session.bot_id}>
                            <td>
                              <span className="bot-id">
                                {session.bot_id.substring(0, 24)}...
                              </span>
                            </td>
                            <td>{formatDate(session.created_at)}</td>
                            <td>
                              <strong>{session.total_prompts}</strong>
                              {session.blocked_prompts > 0 && (
                                <span style={{ color: '#ef4444', marginLeft: 8 }}>
                                  ({session.blocked_prompts} blocked)
                                </span>
                              )}
                            </td>
                            <td>
                              <div className="threat-badges">
                                <ThreatBadge type="pii" count={session.pii_detections} />
                                <ThreatBadge type="jailbreak" count={session.jailbreak_attempts} />
                                <ThreatBadge type="toxicity" count={session.toxicity_detections} />
                              </div>
                            </td>
                            <td>
                              <div className="action-btns">
                                <button 
                                  className="btn btn-view"
                                  onClick={() => fetchBotDetails(session.bot_id)}
                                >
                                  View
                                </button>
                                <button 
                                  className="btn btn-delete"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    deleteBotSession(session.bot_id);
                                  }}
                                >
                                  Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </>
            ) : (
              /* Bot Details View */
              botDetails && (
                <div className="details-container">
                  <button className="back-btn" onClick={() => setView('overview')}>
                    ← Back to Overview
                  </button>

                  <div className="section-title">
                    🔍 Session Details: {selectedBot.substring(0, 30)}...
                  </div>

                  {/* Bot Info */}
                  <div className="bot-info-grid">
                    <div className="info-item">
                      <div className="info-label">Bot ID</div>
                      <div className="info-value" style={{ fontSize: 13, fontFamily: 'monospace' }}>
                        {botDetails.bot_id}
                      </div>
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
                      <div className="info-value" style={{ color: '#ef4444' }}>
                        {botDetails.blocked_prompts}
                      </div>
                    </div>
                    <div className="info-item">
                      <div className="info-label">PII Detected</div>
                      <div className="info-value" style={{ color: '#f59e0b' }}>
                        {botDetails.pii_detections}
                      </div>
                    </div>
                  </div>

                  {/* Details Tabs */}
                  <div className="details-tabs">
                    <button 
                      className={`tab-btn ${detailsTab === 'events' ? 'active' : ''}`}
                      onClick={() => setDetailsTab('events')}
                    >
                      📋 Security Events
                    </button>
                    <button 
                      className={`tab-btn ${detailsTab === 'pii' ? 'active' : ''}`}
                      onClick={() => setDetailsTab('pii')}
                    >
                      🔒 PII Details
                    </button>
                  </div>

                  {/* Tab Content */}
                  {detailsTab === 'events' ? (
                    /* Events Timeline */
                    <div className="events-list">
                      <div className="section-title">
                        📋 Security Events ({botDetails.security_events?.length || 0})
                      </div>

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
                            <div 
                              key={index} 
                              className={`event-card ${isBlocked ? 'blocked' : hasPII ? 'pii' : 'safe'}`}
                            >
                              <div className="event-header">
                                <div className="event-timestamp">
                                🕐 {formatDate(event.timestamp)} 
                              </div>
                                <div className={`event-status ${isBlocked ? 'blocked' : hasPII ? 'pii-detected' : 'safe'}`}>
                                  {isBlocked ? '🚫 BLOCKED' : hasPII ? '🔒 PII DETECTED' : '✅ SAFE'}
                                </div>
                              </div>

                              <div className="event-content">
                                {/* Original Prompt */}
                                <div className="event-section">
                                  <div className="event-section-title">Original Prompt</div>
                                  <div className="event-text">{event.prompt}</div>
                                </div>

                                {/* Anonymized Prompt (if PII detected) */}
                                {event.anonymized_prompt && (
                                  <div className="event-section">
                                    <div className="event-section-title">Anonymized Prompt</div>
                                    <div className="event-text">{event.anonymized_prompt}</div>
                                  </div>
                                )}

                                {/* LLM Response */}
                                {event.llm_response && (
                                  <div className="event-section">
                                    <div className="event-section-title">LLM Response</div>
                                    <div className="event-text">{event.llm_response}</div>
                                  </div>
                                )}

                                {/* Block Reason */}
                                {event.block_reason && (
                                  <div className="event-section">
                                    <div className="event-section-title">Block Reason</div>
                                    <div className="event-text" style={{ color: '#ef4444' }}>
                                      {event.block_reason}
                                    </div>
                                  </div>
                                )}

                                {/* Detection Details */}
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
                                    <div className="detection-tag safe">
                                      ✅ No Threats Detected
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  ) : (
                    /* PII Details Tab */
                    <div className="pii-details">
                      <div className="section-title">
                        🔒 PII Entities Detected ({extractPIIData(botDetails).length})
                      </div>

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
                                <td>
                                  <strong>#{pii.eventIndex}</strong>
                                </td>
                                <td>
                                  <span className="pii-type">{pii.type}</span>
                                </td>
                                <td>
                                  <span className="pii-value">{pii.value}</span>
                                </td>
                                <td>
                                  <div className="confidence-bar">
                                    <div 
                                      className="confidence-fill" 
                                      style={{ width: `${pii.confidence * 100}%` }}
                                    />
                                  </div>
                                  <div className="confidence-text">
                                    {(pii.confidence * 100).toFixed(1)}%
                                  </div>
                                </td>
                                <td>{formatDate(pii.timestamp)}</td>
                                <td>
                                  <div className="pii-prompt-preview" title={pii.prompt}>
                                    {pii.prompt}
                                  </div>
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