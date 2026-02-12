import React, { useState, useEffect, useCallback, useMemo } from 'react';
import DashboardHeader from './dashboard/header/DashboardHeader.jsx';
import { StatsGrid } from './dashboard/stats/StatCard.jsx';
import { SearchBox, FilterGroup, SortDropdown, ActionButtons } from './dashboard/filters/FilterControls.jsx';
import ExportMenu from './dashboard/filters/ExportMenu.jsx';
import { SessionsTable } from './dashboard/sessions/SessionsTable.jsx';
import PaginationControls from './dashboard/pagination/PaginationControls.jsx';
import {
  ThreatDistributionChart,
  TimelineChart,
  ThreatTypeChart,
  TopThreateningChart,
  ChartContainer
} from './dashboard/charts/Charts.jsx';
import {
  useSessionData,
  useSessionFiltering,
  useAllSessionDetails,
  usePromptSearch,
  usePagination
} from './dashboard/hooks/index.js';
import {
  formatDate,
  getRelativeTime,
  extractPIIData,
  calculateThreatCount,
  isCleanSession
} from './dashboard/utils/helpers.js';
import dashboardStyles from './dashboard/styles/dashboard.css';

/**
 * AnalyticsDashboard - Main refactored component
 * Manages state and orchestrates child components
 */
const AnalyticsDashboard = () => {
  // Allow override via environment or local storage
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || localStorage.getItem('backendUrl') || `http://${window.location.hostname}:8000`;

  // Data management hooks
  const {
    sessions,
    botDetails,
    loading,
    stats,
    fetchAllSessions,
    fetchBotDetails,
    deleteBotSession,
    clearAllSessions
  } = useSessionData(BACKEND_URL);

  // UI State
  const [view, setView] = useState('overview');
  const [detailsTab, setDetailsTab] = useState('events');
  const [selectedBot, setSelectedBot] = useState(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedSessions, setSelectedSessions] = useState(new Set());

  // Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMode, setSearchMode] = useState('botId');
  const [filterType, setFilterType] = useState('all');
  const [sortBy, setSortBy] = useState('date-desc');

  // Session details and search
  const { allSessionDetails, loadingPromptData } = useAllSessionDetails(sessions, BACKEND_URL);
  const promptSearchResults = usePromptSearch(searchTerm, searchMode, allSessionDetails);
  
  // Filtering
  const filteredSessions = useSessionFiltering(
    sessions,
    searchTerm,
    searchMode,
    filterType,
    sortBy,
    promptSearchResults
  );

  // Pagination
  const {
    currentPage,
    currentItems,
    totalPages,
    indexOfFirstItem,
    indexOfLastItem,
    paginate,
    resetPage
  } = usePagination(filteredSessions, 20);

  // Initialize on mount
  useEffect(() => {
    fetchAllSessions();
  }, []);

  // Reset pagination on filter/search changes
  useEffect(() => {
    resetPage();
  }, [searchTerm, filterType, sortBy]);

  // Memoized chart data generators
  const getThreatDistributionData = useMemo(() => {
    return () => {
      const cleanSessions = sessions.filter(isCleanSession).length;
      return [
        { name: 'PII Detected', value: stats.totalPII, color: '#f59e0b', filterType: 'pii' },
        { name: 'Secrets Detected', value: stats.totalSecrets, color: '#8b5cf6', filterType: 'secrets' },
        { name: 'Jailbreak Attempts', value: stats.totalJailbreaks, color: '#ef4444', filterType: 'jailbreak' },
        { name: 'Toxicity', value: stats.totalToxicity, color: '#dc2626', filterType: 'toxicity' },
        { name: 'Clean Sessions', value: cleanSessions, color: '#10b981', filterType: 'clean' }
      ].filter(item => item.value > 0);
    };
  }, [stats, sessions]);

  const getTimelineData = useMemo(() => {
    return () => {
      const grouped = sessions.reduce((acc, session) => {
        const dateObj = new Date(session.created_at);
        const date = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        if (!acc[date]) {
          acc[date] = { date, sessions: 0, threats: 0, prompts: 0 };
        }
        acc[date].sessions += 1;
        acc[date].prompts += session.total_prompts || 0;
        acc[date].threats += calculateThreatCount(session);
        return acc;
      }, {});

      return Object.values(grouped)
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .slice(-14);
    };
  }, [sessions]);

  const getThreatTypeData = useMemo(() => {
    return () => [
      { name: 'PII', count: stats.totalPII, color: '#f59e0b', filterType: 'pii' },
      { name: 'Secrets', count: stats.totalSecrets, color: '#8b5cf6', filterType: 'secrets' },
      { name: 'Jailbreak', count: stats.totalJailbreaks, color: '#ef4444', filterType: 'jailbreak' },
      { name: 'Toxicity', count: stats.totalToxicity, color: '#dc2626', filterType: 'toxicity' }
    ].filter(item => item.count > 0);
  }, [stats]);

  const getTopThreateningSessions = useMemo(() => {
    return () =>
      [...sessions]
        .map(s => ({
          id: s.bot_id.substring(0, 12) + '...',
          fullId: s.bot_id,
          threats: calculateThreatCount(s)
        }))
        .filter(s => s.threats > 0)
        .sort((a, b) => b.threats - a.threats)
        .slice(0, 10);
  }, [sessions]);

  // Event handlers with useCallback
  const handleViewChange = useCallback((newView) => {
    setView(newView);
  }, []);

  const handleSessionClick = useCallback((botId) => {
    setSelectedBot(botId);
    fetchBotDetails(botId).then(() => {
      setView('details');
      setDetailsTab('events');
    });
  }, [fetchBotDetails]);

  const handleFilterChange = useCallback((newFilter) => {
    setFilterType(newFilter);
    setSearchTerm('');
  }, []);

  const handleSearchModeChange = useCallback(() => {
    setSearchMode(prev => prev === 'botId' ? 'prompt' : 'botId');
    setSearchTerm('');
  }, []);

  const handlePieChartClick = useCallback((data) => {
    if (data?.filterType) {
      setFilterType(data.filterType);
      setView('overview');
      setSearchTerm('');
    }
  }, []);

  const handleBarChartClick = useCallback((data) => {
    if (data?.fullId) {
      handleSessionClick(data.fullId);
    }
  }, [handleSessionClick]);

  const handleDeleteSession = useCallback(async (botId) => {
    if (window.confirm(`Are you sure you want to delete session ${botId.substring(0, 24)}...?`)) {
      await deleteBotSession(botId);
      if (selectedBot === botId) {
        setView('overview');
        setSelectedBot(null);
      }
    }
  }, [selectedBot, deleteBotSession]);

  const handleClearAllSessions = useCallback(async () => {
    if (window.confirm('⚠️ Are you sure you want to delete ALL sessions? This action cannot be undone.')) {
      await clearAllSessions();
      setView('overview');
      setSelectedBot(null);
    }
  }, [clearAllSessions]);

  const toggleSessionSelection = useCallback((botId) => {
    const newSelected = new Set(selectedSessions);
    if (newSelected.has(botId)) {
      newSelected.delete(botId);
    } else {
      newSelected.add(botId);
    }
    setSelectedSessions(newSelected);
  }, [selectedSessions]);

  const selectAllSessions = useCallback(() => {
    setSelectedSessions(new Set(filteredSessions.map(s => s.bot_id)));
  }, [filteredSessions]);

  const deselectAllSessions = useCallback(() => {
    setSelectedSessions(new Set());
  }, []);

  return (
    <>
      <style>{dashboardStyles}</style>
      
      <div className="dashboard-container">
        <DashboardHeader 
          stats={stats} 
          isIndexingPrompts={loadingPromptData}
        />

        {/* View Toggle */}
        <div className="view-toggle">
          <button 
            className={`toggle-btn ${view === 'overview' ? 'active' : ''}`}
            onClick={() => handleViewChange('overview')}
          >
            📋 Sessions
          </button>
          <button 
            className={`toggle-btn ${view === 'analytics' ? 'active' : ''}`}
            onClick={() => handleViewChange('analytics')}
          >
            📊 Analytics
          </button>
          {selectedBot && (
            <button 
              className={`toggle-btn ${view === 'details' ? 'active' : ''}`}
              onClick={() => handleViewChange('details')}
            >
              🔍 Session Details
            </button>
          )}
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="loading">
            <div className="loading-spinner"></div>
            Loading analytics data...
          </div>
        ) : loadingPromptData ? (
          <div className="loading">
            <div className="loading-spinner"></div>
            Loading prompt data for instant search...
          </div>
        ) : (
          <>
            {/* Overview View */}
            {view === 'overview' && (
              <>
                <StatsGrid stats={stats} />

                <div className="controls-section">
                  <div className="controls-row">
                    <SearchBox 
                      searchTerm={searchTerm}
                      searchMode={searchMode}
                      onSearchChange={setSearchTerm}
                      onModeChange={handleSearchModeChange}
                    />

                    <FilterGroup 
                      filterType={filterType}
                      onFilterChange={handleFilterChange}
                    />

                    <SortDropdown 
                      sortBy={sortBy}
                      onSortChange={setSortBy}
                    />

                    <div style={{ position: 'relative' }}>
                      <ActionButtons 
                        sessionsCount={sessions.length}
                        onExportClick={() => setShowExportMenu(!showExportMenu)}
                        onRefreshClick={fetchAllSessions}
                        onClearClick={handleClearAllSessions}
                        showExportMenu={showExportMenu}
                      />
                      {showExportMenu && (
                        <ExportMenu 
                          sessions={sessions}
                          filteredSessions={filteredSessions}
                          selectedBot={selectedBot}
                          botDetails={botDetails}
                          backendUrl={BACKEND_URL}
                          onExportComplete={() => setShowExportMenu(false)}
                        />
                      )}
                    </div>
                  </div>
                </div>

                {/* Sessions Container */}
                <div className="sessions-container">
                  <div className="section-title">🤖 Bot Sessions ({filteredSessions.length})</div>
                  <SessionsTable 
                    sessions={currentItems}
                    promptSearchResults={promptSearchResults}
                    selectionMode={selectionMode}
                    selectedSessions={selectedSessions}
                    onSelectSession={toggleSessionSelection}
                    onSessionClick={handleSessionClick}
                  />
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <PaginationControls
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={paginate}
                    itemsPerPage={20}
                    totalItems={filteredSessions.length}
                  />
                )}
              </>
            )}

            {/* Analytics View */}
            {view === 'analytics' && (
              <>
                <StatsGrid stats={stats} />

                <div className="charts-grid">
                  <ChartContainer title="📊 Threat Distribution">
                    <ThreatDistributionChart 
                      data={getThreatDistributionData()} 
                      onDataClick={handlePieChartClick}
                    />
                  </ChartContainer>

                  <ChartContainer title="📈 Activity Timeline (Last 14 Days)">
                    <TimelineChart data={getTimelineData()} />
                  </ChartContainer>

                  <ChartContainer title="⚠️ Threat Types Breakdown">
                    <ThreatTypeChart 
                      data={getThreatTypeData()} 
                      onDataClick={handlePieChartClick}
                    />
                  </ChartContainer>

                  <ChartContainer title="🔥 Top Threatening Sessions">
                    <TopThreateningChart 
                      data={getTopThreateningSessions()} 
                      onDataClick={handleBarChartClick}
                    />
                  </ChartContainer>
                </div>
              </>
            )}

            {/* Details View */}
           {view === 'details' && botDetails && (
              <div className="details-container">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
                  <button className="back-btn" onClick={() => setView('overview')}>
                    ← Back to Overview
                  </button>
                  <button className="btn-delete-session" onClick={() => handleDeleteSession(selectedBot)}>
                    🗑️ Delete Session
                  </button>
                </div>

                <div className="section-title">🔍 Session Details: {selectedBot?.substring(0, 30)}...</div>
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
                    <div className="info-label">Total Prompts</div>
                    <div className="info-value">{botDetails.total_prompts}</div>
                  </div>
                </div>

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

                {detailsTab === 'events' ? (
  <div className="events-list">
    {botDetails.security_events?.map((event, idx) => {
      // Determine event card background color based on threat type
      let bgColor = '#d4edda'; // Default green for safe
      let borderColor = '#28a745'; // Green border
      
      // Check if PII is detected (Yellow - highest priority)
      if (event.detections?.pii?.detected || 
          event.detections?.['pii-presidio']?.detected ||
          event.detections?.['pii-scanner']?.detected) {
        bgColor = '#fff3cd'; // Yellow background
        borderColor = '#ffc107'; // Yellow border
      }
      // Check if blocked - jailbreak, prompt_injection, toxicity (Red)
      else if (event.blocked) {
        bgColor = '#f8d7da'; // Red background
        borderColor = '#dc3545'; // Red border
      }
      
      return (
        <div 
          key={idx} 
          className="event-card"
          style={{ 
            backgroundColor: bgColor, 
            borderLeft: `4px solid ${borderColor}`
          }}
        >
          <div className="event-header">
            <div className="event-timestamp">🕐 {formatDate(event.timestamp)}</div>
            <div className={`event-status ${event.blocked ? 'blocked' : 'safe'}`}>
              {event.blocked ? '🚫 BLOCKED' : '✅ SAFE'}
            </div>
            <div className="event-risk">
              Risk: <span className={`risk-${event.risk_level.toLowerCase()}`}>{event.risk_level}</span>
            </div>
          </div>
          
          <div className="event-content">
            <div className="event-section">
              <div className="event-section-title">📝 Prompt</div>
              <div className="event-text">{event.prompt}</div>
            </div>

            {/* Only show detected threats */}
            {event.detections && Object.entries(event.detections).filter(([, result]) => result.detected).length > 0 && (
              <div className="event-section">
                <div className="event-section-title">🔍 Detected Threats</div>
                <div className="detections-grid">
                  {Object.entries(event.detections).map(([scannerName, result]) => 
                    result.detected && (
                      <div key={scannerName} className="detection-badge threat">
                        <div className="detection-name">{scannerName}</div>
                        <div className="detection-status">⚠️ DETECTED</div>
                        {result.entities_found && <div className="detection-count">{result.entities_found} entities</div>}
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            {/* Block Reason (if blocked) */}
            {event.blocked && event.block_reason && (
              <div className="event-section">
                <div className="event-section-title">🛡️ Block Reason</div>
                <div className="block-reason">{event.block_reason}</div>
              </div>
            )}

            {/* LLM Response (if not blocked) */}
            {!event.blocked && event.llm_response && (
              <div className="event-section">
                <div className="event-section-title">💬 LLM Response</div>
                <div className="llm-response">{event.llm_response}</div>
              </div>
            )}

            {/* Metrics */}
            <div className="event-section">
              <div className="event-section-title">⏱️ Performance</div>
              <div className="metrics-grid">
                <div className="metric-box">
                  <div className="metric-label">Scan Time</div>
                  <div className="metric-value">{event.metrics?.scan_time?.toFixed(3) || event.scan_duration?.toFixed(3)}s</div>
                </div>
                {!event.blocked && event.metrics?.llm_time && (
                  <div className="metric-box">
                    <div className="metric-label">LLM Time</div>
                    <div className="metric-value">{event.metrics.llm_time.toFixed(3)}s</div>
                  </div>
                )}
                {event.metrics?.total_time && (
                  <div className="metric-box">
                    <div className="metric-label">Total Time</div>
                    <div className="metric-value">{event.metrics.total_time.toFixed(3)}s</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      );
    })}
  </div>
) : (
                  <div className="pii-details">
                    <div className="section-title">🔒 PII Entities ({extractPIIData(botDetails).length})</div>
                    {extractPIIData(botDetails).length === 0 ? (
                      <div className="empty-state">No PII detected</div>
                    ) : (
                      <table className="pii-table">
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Value</th>
                            <th>Timestamp</th>
                          </tr>
                        </thead>
                        <tbody>
                          {extractPIIData(botDetails).map((pii, idx) => (
                            <tr key={idx}>
                              <td><span className="pii-type">{pii.type}</span></td>
                              <td><span className="pii-value">{pii.value}</span></td>
                              <td>{formatDate(pii.timestamp)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
};

export default AnalyticsDashboard;
