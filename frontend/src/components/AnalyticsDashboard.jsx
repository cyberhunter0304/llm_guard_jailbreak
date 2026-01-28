import React, { useState, useEffect } from 'react';

/**
 * ANALYTICS DASHBOARD with PII Detection
 * Displays: Flagged Content and Bots with Issues
 * PII is ONLY shown inside individual bot details (not on main dashboard)
 */

const AnalyticsDashboard = () => {
  const [overview, setOverview] = useState(null);
  const [bots, setBots] = useState([]);
  const [selectedBot, setSelectedBot] = useState(null);
  const [flaggedRequests, setFlaggedRequests] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('bots'); // bots, flagged, issues
  const [error, setError] = useState(null);
  
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

  const fetchOverview = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/analytics/overview`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setOverview(data);
      setError(null);
    } catch (error) {
      console.error('Failed to fetch:', error);
      setError('Connection failed');
    }
  };

  const fetchBots = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/analytics/bots?limit=100`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setBots(data.bots || []);
      
      // Collect all flagged requests
      const flagged = [];
      for (const bot of data.bots || []) {
        if (bot.total_blocks > 0) {
          const detailResponse = await fetch(`${BACKEND_URL}/api/analytics/bot/${bot.bot_id}`);
          if (detailResponse.ok) {
            const details = await detailResponse.json();
            const blocked = (details.recent_requests || [])
              .filter(req => req.input_blocked || req.output_blocked)
              .map(req => ({
                ...req,
                bot_name: bot.bot_name,
                bot_id: bot.bot_id
              }));
            flagged.push(...blocked);
          }
        }
      }
      setFlaggedRequests(flagged.sort((a, b) => 
        new Date(b.timestamp) - new Date(a.timestamp)
      ));
    } catch (error) {
      console.error('Failed to fetch:', error);
    }
  };

  const fetchBotDetails = async (botId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/analytics/bot/${botId}`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setSelectedBot(data);
    } catch (error) {
      console.error('Failed to fetch:', error);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchOverview(), fetchBots()]);
      setLoading(false);
    };
    loadData();
    
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const botsWithIssues = bots.filter(bot => {
    const blockRate = bot.total_requests > 0 
      ? (bot.total_blocks / bot.total_requests) * 100 
      : 0;
    return blockRate > 5 || bot.total_blocks > 10;
  });

  const filteredFlagged = flaggedRequests.filter(req => 
    req.bot_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    req.bot_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (req.prompt && req.prompt.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading) {
    return (
      <div style={styles.loading}>
        <div style={styles.loadingDot}></div>
        <p style={styles.loadingText}>Loading analytics...</p>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div style={styles.loading}>
        <p style={styles.errorText}>⚠ {error}</p>
        <button onClick={() => window.location.reload()} style={styles.retryBtn}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
        
        * { 
          margin: 0; 
          padding: 0; 
          box-sizing: border-box; 
        }
        
        body { 
          font-family: 'IBM Plex Sans', -apple-system, sans-serif;
          background: #fafafa;
          color: #1a1a1a;
          line-height: 1.6;
        }

        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 40px 24px;
        }

        .header {
          margin-bottom: 48px;
        }

        .title {
          font-size: 28px;
          font-weight: 600;
          color: #1a1a1a;
          margin-bottom: 8px;
          letter-spacing: -0.02em;
        }

        .subtitle {
          font-size: 14px;
          color: #666;
          font-weight: 400;
        }

        .stats-row {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 40px;
        }

        .stat-card {
          background: white;
          border: 1px solid #e5e5e5;
          border-radius: 8px;
          padding: 20px;
          transition: border-color 0.2s;
        }

        .stat-card:hover {
          border-color: #d4d4d4;
        }

        .stat-label {
          font-size: 12px;
          color: #666;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 8px;
          font-weight: 500;
        }

        .stat-value {
          font-size: 32px;
          font-weight: 600;
          color: #1a1a1a;
          font-family: 'IBM Plex Mono', monospace;
        }

        .stat-trend {
          font-size: 13px;
          color: #666;
          margin-top: 4px;
        }

        .tabs {
          display: flex;
          gap: 8px;
          margin-bottom: 32px;
          border-bottom: 1px solid #e5e5e5;
          padding-bottom: 0;
        }

        .tab {
          background: none;
          border: none;
          padding: 12px 20px;
          font-size: 14px;
          font-weight: 500;
          color: #666;
          cursor: pointer;
          position: relative;
          transition: color 0.2s;
          font-family: 'IBM Plex Sans', sans-serif;
        }

        .tab:hover {
          color: #1a1a1a;
        }

        .tab.active {
          color: #1a1a1a;
        }

        .tab.active::after {
          content: '';
          position: absolute;
          bottom: -1px;
          left: 0;
          right: 0;
          height: 2px;
          background: #1a1a1a;
        }

        .search-box {
          margin-bottom: 24px;
        }

        .search-input {
          width: 100%;
          padding: 12px 16px;
          border: 1px solid #e5e5e5;
          border-radius: 8px;
          font-size: 14px;
          font-family: 'IBM Plex Sans', sans-serif;
          transition: border-color 0.2s;
        }

        .search-input:focus {
          outline: none;
          border-color: #1a1a1a;
        }

        .flagged-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .flagged-item {
          background: white;
          border: 1px solid #e5e5e5;
          border-left: 3px solid #dc2626;
          border-radius: 8px;
          padding: 20px;
          transition: border-color 0.2s;
        }

        .flagged-item:hover {
          border-left-color: #b91c1c;
        }

        .flagged-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }

        .bot-info {
          flex: 1;
        }

        .bot-name {
          font-weight: 600;
          font-size: 14px;
          color: #1a1a1a;
          margin-bottom: 4px;
        }

        .timestamp {
          font-size: 12px;
          color: #666;
          font-family: 'IBM Plex Mono', monospace;
        }

        .badges {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }

        .badge {
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .badge-danger {
          background: #fee2e2;
          color: #991b1b;
        }

        .badge-warning {
          background: #fef3c7;
          color: #92400e;
        }

        .badge-info {
          background: #dbeafe;
          color: #1e40af;
        }

        .badge-purple {
          background: #f3e8ff;
          color: #6b21a8;
        }

        .prompt-box {
          background: #f9fafb;
          border: 1px solid #e5e5e5;
          border-radius: 6px;
          padding: 12px;
          margin-top: 12px;
        }

        .prompt-label {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: #666;
          margin-bottom: 8px;
          font-weight: 500;
        }

        .prompt-text {
          font-size: 13px;
          color: #1a1a1a;
          line-height: 1.6;
          font-family: 'IBM Plex Mono', monospace;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .flagged-details {
          display: flex;
          flex-direction: column;
          gap: 4px;
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid #f3f4f6;
          font-size: 13px;
        }

        .detail-row {
          display: flex;
          gap: 8px;
        }

        .detail-label {
          color: #666;
          min-width: 100px;
        }

        .bots-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 16px;
        }

        .bot-card {
          background: white;
          border: 1px solid #e5e5e5;
          border-radius: 8px;
          padding: 20px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .bot-card:hover {
          border-color: #1a1a1a;
          transform: translateY(-2px);
        }

        .bot-card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 16px;
        }

        .bot-card-name {
          font-size: 16px;
          font-weight: 600;
          color: #1a1a1a;
          margin-bottom: 4px;
        }

        .bot-card-id {
          font-size: 11px;
          color: #666;
          font-family: 'IBM Plex Mono', monospace;
        }

        .bot-card-stats {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 12px;
        }

        .bot-stat-row {
          display: flex;
          justify-content: space-between;
          font-size: 13px;
        }

        .bot-stat-label {
          color: #666;
        }

        .bot-stat-value {
          font-weight: 600;
          font-family: 'IBM Plex Mono', monospace;
        }

        .bot-card-meta {
          display: flex;
          gap: 8px;
          padding-top: 12px;
          border-top: 1px solid #f3f4f6;
        }

        .empty-state {
          text-align: center;
          padding: 60px 20px;
        }

        .empty-icon {
          font-size: 48px;
          margin-bottom: 16px;
          opacity: 0.3;
        }

        .empty-text {
          font-size: 14px;
          color: #666;
        }

        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 20px;
        }

        .modal {
          background: white;
          border-radius: 12px;
          max-width: 800px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 24px;
          border-bottom: 1px solid #e5e5e5;
          position: sticky;
          top: 0;
          background: white;
          z-index: 10;
          border-radius: 12px 12px 0 0;
        }

        .modal-title {
          font-size: 20px;
          font-weight: 600;
          color: #1a1a1a;
        }

        .close-btn {
          padding: 8px 16px;
          background: #f3f4f6;
          border: none;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.2s;
          font-family: 'IBM Plex Sans', sans-serif;
        }

        .close-btn:hover {
          background: #e5e7eb;
        }

        .modal-body {
          padding: 24px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 16px;
          margin-bottom: 32px;
        }

        .detail-card {
          background: #f9fafb;
          border: 1px solid #e5e5e5;
          border-radius: 8px;
          padding: 16px;
        }

        .detail-card-label {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: #666;
          margin-bottom: 8px;
          font-weight: 500;
        }

        .detail-card-value {
          font-size: 24px;
          font-weight: 600;
          color: #1a1a1a;
          font-family: 'IBM Plex Mono', monospace;
        }

        .section-title {
          font-size: 14px;
          font-weight: 600;
          color: #1a1a1a;
          margin-bottom: 16px;
          padding-top: 8px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .scanner-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 32px;
          padding-top: 16px;
          border-top: 1px solid #e5e5e5;
        }

        .pii-item {
          background: white;
          border: 1px solid #e5e5e5;
          border-left: 3px solid #9333ea;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 12px;
        }

        .pii-box {
          background: #faf5ff;
          border: 1px solid #e9d5ff;
          border-radius: 6px;
          padding: 12px;
          margin-top: 12px;
        }

        .pii-value {
          font-size: 14px;
          font-weight: 600;
          color: #6b21a8;
          margin-bottom: 6px;
          font-family: 'IBM Plex Mono', monospace;
        }

        .pii-context {
          font-size: 12px;
          color: #6b21a8;
          line-height: 1.5;
          font-family: 'IBM Plex Mono', monospace;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      <div className="container">
        <div className="header">
          <h1 className="title">Security Analytics</h1>
          <p className="subtitle">Monitor flagged content and bot security metrics</p>
        </div>

        {overview && (
          <div className="stats-row">
            <div className="stat-card">
              <div className="stat-label">Total Scans</div>
              <div className="stat-value">{(overview.total_scans || 0).toLocaleString()}</div>
            </div>
            
            <div className="stat-card">
              <div className="stat-label">Flagged</div>
              <div className="stat-value">{(overview.total_blocks || 0).toLocaleString()}</div>
              {(overview.total_scans || 0) > 0 && (
                <div className="stat-trend">
                  {(((overview.total_blocks || 0) / (overview.total_scans || 1)) * 100).toFixed(1)}% blocked
                </div>
              )}
            </div>
            
            <div className="stat-card">
              <div className="stat-label">Active Bots</div>
              <div className="stat-value">{(bots?.length || 0).toLocaleString()}</div>
            </div>
            
            <div className="stat-card">
              <div className="stat-label">Bots with Issues</div>
              <div className="stat-value">{(botsWithIssues?.length || 0).toLocaleString()}</div>
            </div>
          </div>
        )}

        <div className="tabs">
          <button 
            className={`tab ${activeView === 'flagged' ? 'active' : ''}`}
            onClick={() => setActiveView('flagged')}
          >
            Flagged Content ({filteredFlagged?.length || 0})
          </button>
          <button 
            className={`tab ${activeView === 'bots' ? 'active' : ''}`}
            onClick={() => setActiveView('bots')}
          >
            All Bots ({bots?.length || 0})
          </button>
          <button 
            className={`tab ${activeView === 'issues' ? 'active' : ''}`}
            onClick={() => setActiveView('issues')}
          >
            Bots with Issues ({botsWithIssues?.length || 0})
          </button>
        </div>

        {activeView === 'flagged' && (
          <>
            <div className="search-box">
              <input
                type="text"
                className="search-input"
                placeholder="Search by bot name, ID, or prompt..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {filteredFlagged && filteredFlagged.length > 0 ? (
              <div className="flagged-list">
                {filteredFlagged.map((req, index) => (
                  <div key={index} className="flagged-item">
                    <div className="flagged-header">
                      <div className="bot-info">
                        <div className="bot-name">{req.bot_name}</div>
                        <div className="timestamp">
                          {new Date(req.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <div className="badges">
                        {req.input_blocked && (
                          <span className="badge badge-danger">Input</span>
                        )}
                        {req.output_blocked && (
                          <span className="badge badge-danger">Output</span>
                        )}
                        {req.pii_detected && (
                          <span className="badge badge-purple">PII: {req.pii_count}</span>
                        )}
                        <span className="badge badge-warning">
                          {req.risk_level}
                        </span>
                      </div>
                    </div>

                    {req.prompt && (
                      <div className="prompt-box">
                        <div className="prompt-label">User Prompt</div>
                        <div className="prompt-text">
                          {req.prompt.length > 400 
                            ? `${req.prompt.substring(0, 400)}...` 
                            : req.prompt}
                        </div>
                      </div>
                    )}

                    <div className="flagged-details">
                      {req.blocked_by && req.blocked_by.length > 0 && (
                        <div className="detail-row">
                          <span className="detail-label">Detected by:</span>
                          <span>{req.blocked_by.map(s => s.replace('_', ' ')).join(', ')}</span>
                        </div>
                      )}
                      <div className="detail-row">
                        <span className="detail-label">Bot ID:</span>
                        <span>{req.bot_id}</span>
                      </div>
                      <div className="detail-row">
                        <span className="detail-label">Model:</span>
                        <span>{req.model}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">✓</div>
                <div className="empty-text">
                  {searchTerm ? 'No matching flagged requests' : 'No flagged requests'}
                </div>
              </div>
            )}
          </>
        )}

        {activeView === 'bots' && (
          <>
            <div className="search-box">
              <input
                type="text"
                className="search-input"
                placeholder="Search bots by name or ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {(() => {
              const filteredBots = bots.filter(bot => 
                bot?.bot_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                bot?.bot_id?.toLowerCase().includes(searchTerm.toLowerCase())
              );

              return filteredBots && filteredBots.length > 0 ? (
                <div className="bots-grid">
                  {filteredBots.map((bot) => {
                    const blockRate = (bot?.total_requests || 0) > 0 
                      ? ((bot?.total_blocks || 0) / (bot?.total_requests || 1)) * 100 
                      : 0;
                    
                    return (
                      <div 
                        key={bot?.bot_id || Math.random()} 
                        className="bot-card"
                        onClick={() => fetchBotDetails(bot?.bot_id)}
                      >
                        <div className="bot-card-header">
                          <div>
                            <div className="bot-card-name">{bot?.bot_name || 'Unknown Bot'}</div>
                            <div className="bot-card-id">{bot?.bot_id || 'N/A'}</div>
                          </div>
                        </div>

                        <div className="bot-card-stats">
                          <div className="bot-stat-row">
                            <span className="bot-stat-label">Total Requests</span>
                            <span className="bot-stat-value">{(bot?.total_requests || 0).toLocaleString()}</span>
                          </div>
                          <div className="bot-stat-row">
                            <span className="bot-stat-label">Flagged</span>
                            <span className="bot-stat-value" style={{color: (bot?.total_blocks || 0) > 0 ? '#dc2626' : '#666'}}>
                              {(bot?.total_blocks || 0).toLocaleString()}
                            </span>
                          </div>
                          <div className="bot-stat-row">
                            <span className="bot-stat-label">Block Rate</span>
                            <span className="bot-stat-value" style={{
                              color: blockRate > 10 ? '#dc2626' : blockRate > 5 ? '#f59e0b' : '#666'
                            }}>
                              {blockRate.toFixed(1)}%
                            </span>
                          </div>
                          {(bot?.pii_detected_count || 0) > 0 && (
                            <div className="bot-stat-row">
                              <span className="bot-stat-label">PII Detected</span>
                              <span className="bot-stat-value" style={{color: '#9333ea'}}>
                                {bot?.pii_detected_count || 0}
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="bot-card-meta">
                          {(bot?.total_blocks || 0) === 0 && (bot?.total_requests || 0) > 0 && (
                            <span className="badge badge-info">✓ Clean</span>
                          )}
                          {(bot?.total_requests || 0) === 0 && (
                            <span className="badge" style={{background: '#f3f4f6', color: '#666'}}>No activity</span>
                          )}
                          {(bot?.toxicity_count || 0) > 0 && (
                            <span className="badge badge-danger">
                              Toxicity: {bot?.toxicity_count || 0}
                            </span>
                          )}
                          {(bot?.prompt_injection_count || 0) > 0 && (
                            <span className="badge badge-warning">
                              Injection: {bot?.prompt_injection_count || 0}
                            </span>
                          )}
                          {(bot?.pii_detected_count || 0) > 0 && (
                            <span className="badge badge-purple">
                              PII: {bot?.pii_detected_count || 0}
                            </span>
                          )}
                        </div>

                        <div style={{
                          fontSize: '11px',
                          color: '#999',
                          marginTop: '12px',
                          paddingTop: '12px',
                          borderTop: '1px solid #f3f4f6',
                          fontFamily: "'IBM Plex Mono', monospace"
                        }}>
                          Last seen: {bot?.last_seen ? new Date(bot.last_seen).toLocaleString() : 'Never'}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="empty-state">
                  <div className="empty-icon">🔍</div>
                  <div className="empty-text">
                    {searchTerm ? 'No bots match your search' : 'No active bots'}
                  </div>
                </div>
              );
            })()}
          </>
        )}

        {activeView === 'issues' && (
          <>
            {botsWithIssues && botsWithIssues.length > 0 ? (
              <div className="bots-grid">
                {botsWithIssues.map((bot) => {
                  const blockRate = (bot?.total_requests || 0) > 0 
                    ? ((bot?.total_blocks || 0) / (bot?.total_requests || 1)) * 100 
                    : 0;
                  
                  return (
                    <div 
                      key={bot?.bot_id || Math.random()} 
                      className="bot-card"
                      onClick={() => fetchBotDetails(bot?.bot_id)}
                    >
                      <div className="bot-card-header">
                        <div>
                          <div className="bot-card-name">{bot?.bot_name || 'Unknown Bot'}</div>
                          <div className="bot-card-id">{bot?.bot_id || 'N/A'}</div>
                        </div>
                      </div>

                      <div className="bot-card-stats">
                        <div className="bot-stat-row">
                          <span className="bot-stat-label">Total Requests</span>
                          <span className="bot-stat-value">{(bot?.total_requests || 0).toLocaleString()}</span>
                        </div>
                        <div className="bot-stat-row">
                          <span className="bot-stat-label">Flagged</span>
                          <span className="bot-stat-value" style={{color: '#dc2626'}}>
                            {(bot?.total_blocks || 0).toLocaleString()}
                          </span>
                        </div>
                        <div className="bot-stat-row">
                          <span className="bot-stat-label">Block Rate</span>
                          <span className="bot-stat-value">
                            {blockRate.toFixed(1)}%
                          </span>
                        </div>
                        {(bot?.pii_detected_count || 0) > 0 && (
                          <div className="bot-stat-row">
                            <span className="bot-stat-label">PII Detected</span>
                            <span className="bot-stat-value" style={{color: '#9333ea'}}>
                              {bot?.pii_detected_count || 0}
                            </span>
                          </div>
                        )}
                      </div>

                      <div className="bot-card-meta">
                        {(bot?.toxicity_count || 0) > 0 && (
                          <span className="badge badge-danger">
                            Toxicity: {bot?.toxicity_count || 0}
                          </span>
                        )}
                        {(bot?.prompt_injection_count || 0) > 0 && (
                          <span className="badge badge-warning">
                            Injection: {bot?.prompt_injection_count || 0}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">✓</div>
                <div className="empty-text">No bots with security issues</div>
              </div>
            )}
          </>
        )}

        {selectedBot && (
          <div className="modal-overlay" onClick={() => setSelectedBot(null)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2 className="modal-title">{selectedBot?.bot?.bot_name || 'Bot Details'}</h2>
                <button className="close-btn" onClick={() => setSelectedBot(null)}>
                  Close
                </button>
              </div>

              <div className="modal-body">
                {/* Activity Timeline Info */}
                <div style={{
                  background: '#f9fafb',
                  border: '1px solid #e5e5e5',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '24px',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                  gap: '12px',
                  fontSize: '12px'
                }}>
                  <div>
                    <div style={{color: '#666', marginBottom: '4px'}}>First Seen</div>
                    <div style={{fontFamily: "'IBM Plex Mono', monospace", color: '#1a1a1a'}}>
                      {selectedBot?.bot?.first_seen ? new Date(selectedBot.bot.first_seen).toLocaleString() : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div style={{color: '#666', marginBottom: '4px'}}>Last Seen</div>
                    <div style={{fontFamily: "'IBM Plex Mono', monospace", color: '#1a1a1a'}}>
                      {selectedBot?.bot?.last_seen ? new Date(selectedBot.bot.last_seen).toLocaleString() : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div style={{color: '#666', marginBottom: '4px'}}>Bot ID</div>
                    <div style={{fontFamily: "'IBM Plex Mono', monospace", color: '#1a1a1a', fontSize: '11px'}}>
                      {selectedBot?.bot?.bot_id || 'N/A'}
                    </div>
                  </div>
                </div>

                <div className="detail-grid">
                  <div className="detail-card">
                    <div className="detail-card-label">Total Requests</div>
                    <div className="detail-card-value">
                      {(selectedBot?.bot?.total_requests || 0).toLocaleString()}
                    </div>
                  </div>
                  
                  <div className="detail-card">
                    <div className="detail-card-label">Flagged</div>
                    <div className="detail-card-value">
                      {(selectedBot?.bot?.total_blocks || 0).toLocaleString()}
                    </div>
                  </div>
                  
                  <div className="detail-card">
                    <div className="detail-card-label">Input Blocks</div>
                    <div className="detail-card-value">{selectedBot?.bot?.input_blocks || 0}</div>
                  </div>
                  
                  <div className="detail-card">
                    <div className="detail-card-label">Output Blocks</div>
                    <div className="detail-card-value">{selectedBot?.bot?.output_blocks || 0}</div>
                  </div>
                </div>

                {/* PII SECTION - Only shown if PII detected */}
                {selectedBot?.bot?.pii_detected_count > 0 && (
                  <>
                    <div className="section-title">🔒 PII Detection</div>
                    <div className="detail-grid" style={{marginBottom: '24px'}}>
                      <div className="detail-card" style={{background: '#faf5ff', borderColor: '#e9d5ff'}}>
                        <div className="detail-card-label" style={{color: '#7c3aed'}}>PII Detections</div>
                        <div className="detail-card-value" style={{color: '#6b21a8'}}>
                          {selectedBot?.bot?.pii_detected_count || 0}
                        </div>
                      </div>
                    </div>

                    <div className="section-title" style={{marginTop: 0}}>PII Types Detected</div>
                    <div className="scanner-list" style={{marginTop: 0, paddingTop: 0, borderTop: 'none'}}>
                      {Object.entries(selectedBot?.bot?.pii_types || {})
                        .sort((a, b) => b[1] - a[1])
                        .map(([type, count]) => (
                          <span key={type} className="badge badge-purple">
                            {type.replace('_', ' ')}: {count}
                          </span>
                        ))}
                    </div>

                    <div className="section-title" style={{marginTop: '32px'}}>Recent PII Detections</div>
                    <div className="flagged-list">
                      {selectedBot?.pii_detections?.slice(-10).reverse().map((pii, index) => (
                        <div key={index} className="pii-item">
                          <div className="flagged-header">
                            <div className="bot-info">
                              <div className="timestamp">
                                {new Date(pii.timestamp).toLocaleString()}
                              </div>
                            </div>
                            <div className="badges">
                              <span className="badge badge-purple">{pii.entity_type.replace('_', ' ')}</span>
                            </div>
                          </div>

                          <div className="pii-box">
                            <div className="pii-value">{pii.entity_value}</div>
                            <div className="pii-context">{pii.context}</div>
                          </div>
                        </div>
                      )) || []}
                      {(!selectedBot?.pii_detections || selectedBot.pii_detections.length === 0) && (
                        <div className="empty-state" style={{padding: '40px 20px'}}>
                          <div className="empty-icon">🔒</div>
                          <div className="empty-text">No PII detections</div>
                        </div>
                      )}
                    </div>
                  </>
                )}

                <div className="section-title" style={{marginTop: '32px'}}>Detection Breakdown</div>
                <div className="scanner-list" style={{marginTop: 0, paddingTop: 0, borderTop: 'none'}}>
                  {Object.entries(selectedBot?.bot?.blocks_by_scanner || {})
                    .sort((a, b) => b[1] - a[1])
                    .map(([scanner, count]) => (
                      <span key={scanner} className="badge badge-info">
                        {scanner.replace('_', ' ')}: {count}
                      </span>
                    ))}
                  {(!selectedBot?.bot?.blocks_by_scanner || Object.keys(selectedBot.bot.blocks_by_scanner).length === 0) && (
                    <span className="badge badge-info">No detections</span>
                  )}
                </div>

                <div className="section-title" style={{marginTop: '32px'}}>Recent Flagged Requests</div>
                <div className="flagged-list">
                  {selectedBot?.recent_requests
                    ?.filter(req => req.input_blocked || req.output_blocked)
                    .slice(-10)
                    .reverse()
                    .map((req, index) => (
                      <div key={index} className="flagged-item" style={{borderLeft: 'none', padding: '16px'}}>
                        <div className="flagged-header">
                          <div className="timestamp">
                            {new Date(req.timestamp).toLocaleString()}
                          </div>
                          <div className="badges">
                            {req.input_blocked && (
                              <span className="badge badge-danger">Input</span>
                            )}
                            {req.output_blocked && (
                              <span className="badge badge-danger">Output</span>
                            )}
                            {req.pii_detected && (
                              <span className="badge badge-purple">PII: {req.pii_count}</span>
                            )}
                          </div>
                        </div>

                        {req.prompt && (
                          <div className="prompt-box" style={{marginTop: '12px'}}>
                            <div className="prompt-label">User Prompt</div>
                            <div className="prompt-text">
                              {req.prompt.length > 300 
                                ? `${req.prompt.substring(0, 300)}...` 
                                : req.prompt}
                            </div>
                          </div>
                        )}

                        <div className="flagged-details" style={{marginTop: '8px', paddingTop: '8px'}}>
                          {req.blocked_by && req.blocked_by.length > 0 && (
                            <div className="detail-row">
                              <span className="detail-label">Detected:</span>
                              <span>{req.blocked_by.map(s => s.replace('_', ' ')).join(', ')}</span>
                            </div>
                          )}
                          <div className="detail-row">
                            <span className="detail-label">Model:</span>
                            <span>{req.model || 'N/A'}</span>
                          </div>
                        </div>
                      </div>
                    )) || []}
                  {(!selectedBot?.recent_requests?.some(req => req.input_blocked || req.output_blocked)) && (
                    <div className="empty-state" style={{padding: '40px 20px'}}>
                      <div className="empty-icon">✓</div>
                      <div className="empty-text">No flagged requests</div>
                    </div>
                  )}
                </div>

                <div className="section-title" style={{marginTop: '32px'}}>All Recent Activity</div>
                <div className="flagged-list">
                  {selectedBot?.recent_requests
                    ?.slice(-20)
                    .reverse()
                    .map((req, index) => (
                      <div key={index} className="flagged-item" style={{
                        borderLeft: req.input_blocked || req.output_blocked ? '3px solid #dc2626' : '3px solid #10b981',
                        padding: '16px'
                      }}>
                        <div className="flagged-header">
                          <div className="timestamp">
                            {new Date(req.timestamp).toLocaleString()}
                          </div>
                          <div className="badges">
                            {!req.input_blocked && !req.output_blocked && (
                              <span className="badge badge-info">✓ Passed</span>
                            )}
                            {req.input_blocked && (
                              <span className="badge badge-danger">Blocked</span>
                            )}
                            {req.pii_detected && (
                              <span className="badge badge-purple">PII: {req.pii_count}</span>
                            )}
                            <span className="badge" style={{background: '#f3f4f6', color: '#666'}}>
                              {req.risk_level || 'LOW'}
                            </span>
                          </div>
                        </div>

                        {req.prompt && (
                          <div className="prompt-box" style={{marginTop: '12px'}}>
                            <div className="prompt-label">User Prompt</div>
                            <div className="prompt-text">
                              {req.prompt.length > 200 
                                ? `${req.prompt.substring(0, 200)}...` 
                                : req.prompt}
                            </div>
                          </div>
                        )}

                        <div className="flagged-details" style={{marginTop: '8px', paddingTop: '8px'}}>
                          <div className="detail-row">
                            <span className="detail-label">Prompt Length:</span>
                            <span>{req.prompt_length || 0} chars</span>
                          </div>
                          <div className="detail-row">
                            <span className="detail-label">Response Length:</span>
                            <span>{req.response_length || 0} chars</span>
                          </div>
                          <div className="detail-row">
                            <span className="detail-label">Response Time:</span>
                            <span>{(req.response_time || 0).toFixed(2)}s</span>
                          </div>
                          {req.blocked_by && req.blocked_by.length > 0 && (
                            <div className="detail-row">
                              <span className="detail-label">Blocked by:</span>
                              <span>{req.blocked_by.map(s => s.replace('_', ' ')).join(', ')}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )) || []}
                  {(!selectedBot?.recent_requests || selectedBot.recent_requests.length === 0) && (
                    <div className="empty-state" style={{padding: '40px 20px'}}>
                      <div className="empty-icon">📋</div>
                      <div className="empty-text">No recent activity</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

const styles = {
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    background: '#fafafa'
  },
  loadingDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    background: '#1a1a1a',
    animation: 'pulse 1.5s ease-in-out infinite',
    marginBottom: '16px'
  },
  loadingText: {
    fontSize: '14px',
    color: '#666'
  },
  errorText: {
    fontSize: '16px',
    color: '#dc2626',
    marginBottom: '16px'
  },
  retryBtn: {
    padding: '10px 20px',
    background: '#1a1a1a',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    fontFamily: "'IBM Plex Sans', sans-serif"
  }
};

export default AnalyticsDashboard;