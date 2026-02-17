import React, { useState, useEffect, useCallback, useMemo } from 'react';
import DashboardHeader from './dashboard/header/DashboardHeader.jsx';
import { StatsGrid } from './dashboard/stats/StatCard.jsx';
import { SearchBox, FilterGroup, SortDropdown, ActionButtons } from './dashboard/filters/FilterControls.jsx';
import ExportMenu from './dashboard/filters/ExportMenu.jsx';
import PaginationControls from './dashboard/pagination/PaginationControls.jsx';
import {
  ThreatDistributionChart,
  TimelineChart,
  ThreatTypeChart,
  TopThreateningChart,
  ChartContainer
} from './dashboard/charts/Charts.jsx';
import {
  formatDate,
  getRelativeTime,
  calculateThreatCount
} from './dashboard/utils/helpers.js';
import dashboardStyles from './dashboard/styles/dashboard.css.js';

/**
 * AnalyticsDashboard - Thread-Based Architecture
 * 
 * Data Structure:
 * - threads[] - Array of thread documents (one per user)
 *   - thread_id - Unique identifier for user
 *   - conversations[] - Array of conversations for this user
 *     - conversation_id - Session identifier
 *     - security_events[] - Array of message validations
 */
const AnalyticsDashboard = () => {
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 
                     localStorage.getItem('backendUrl') || 
                     `http://${window.location.hostname}:8000`;

  // Data State
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // UI State
  const [view, setView] = useState('overview'); // 'overview' | 'analytics' | 'details'
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [selectedThread, setSelectedThread] = useState(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  
  // Filter State
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMode, setSearchMode] = useState('threadId'); // 'threadId' | 'userId' | 'prompt'
  const [filterType, setFilterType] = useState('all'); // 'all' | 'threats' | 'clean' | 'pii' | etc.
  const [sortBy, setSortBy] = useState('date-desc');
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  // Helper: Recalculate thread stats from conversations
  const recalculateThreadStats = (thread) => {
    if (!thread.conversations || thread.conversations.length === 0) {
      return thread;
    }

    const stats = thread.conversations.reduce((acc, conv) => ({
      total_prompts: acc.total_prompts + (conv.total_prompts || 0),
      blocked_prompts: acc.blocked_prompts + (conv.blocked_prompts || 0),
      pii_detections: acc.pii_detections + (conv.pii_detections || 0),
      jailbreak_attempts: acc.jailbreak_attempts + (conv.jailbreak_attempts || 0),
      toxicity_detections: acc.toxicity_detections + (conv.toxicity_detections || 0),
      secrets_detections: acc.secrets_detections + (conv.secrets_detections || 0),
      total_messages: acc.total_messages + (conv.total_messages || 0)
    }), {
      total_prompts: 0,
      blocked_prompts: 0,
      pii_detections: 0,
      jailbreak_attempts: 0,
      toxicity_detections: 0,
      secrets_detections: 0,
      total_messages: 0
    });

    return { ...thread, ...stats };
  };

  // Normalize threads data with recalculated stats
  const normalizedThreads = useMemo(() => 
    threads.map(recalculateThreadStats), 
    [threads]
  );

  // Calculate aggregate statistics
  const stats = useMemo(() => {
    const aggregated = normalizedThreads.reduce((acc, thread) => ({
      totalThreads: acc.totalThreads + 1,
      totalConversations: acc.totalConversations + (thread.conversation_count || 0),
      totalPrompts: acc.totalPrompts + (thread.total_prompts || 0),
      totalBlocked: acc.totalBlocked + (thread.blocked_prompts || 0),
      totalPII: acc.totalPII + (thread.pii_detections || 0),
      totalJailbreaks: acc.totalJailbreaks + (thread.jailbreak_attempts || 0),
      totalToxicity: acc.totalToxicity + (thread.toxicity_detections || 0),
      totalSecrets: acc.totalSecrets + (thread.secrets_detections || 0)
    }), {
      totalThreads: 0,
      totalConversations: 0,
      totalPrompts: 0,
      totalBlocked: 0,
      totalPII: 0,
      totalJailbreaks: 0,
      totalToxicity: 0,
      totalSecrets: 0
    });
    return aggregated;
  }, [normalizedThreads]);

  // Transform MongoDB message structure to security_events structure
  const transformConversationData = (conversation) => {
    if (!conversation.messages || conversation.messages.length === 0) {
      console.log(`Conversation ${conversation.conversation_id} has no messages`);
      return { ...conversation, security_events: [] };
    }

    // Convert messages array to security_events array
    // Only include user messages that have validation data
    const security_events = conversation.messages
      .filter(msg => {
        const isUserMessage = msg.role === 'user';
        const hasValidation = msg.validation != null;
        return isUserMessage && hasValidation;
      })
      .map(msg => ({
        timestamp: msg.timestamp || msg.validation?.timestamp,
        prompt: msg.text || msg.validation?.prompt,
        prompt_length: msg.validation?.prompt_length || (msg.text?.length || 0),
        llm_response: msg.validation?.llm_response,
        detections: msg.validation?.detections || {},
        risk_level: msg.validation?.risk_level || 'SAFE',
        is_safe: msg.validation?.is_safe !== false,
        blocked: msg.validation?.blocked || false,
        block_reason: msg.validation?.message,
        metrics: msg.validation?.metrics || {},
        anonymized_prompt: msg.validation?.detections?.pii?.anonymized_prompt
      }));

    console.log(`Conversation ${conversation.conversation_id}: ${conversation.messages.length} messages → ${security_events.length} security events`);

    return {
      ...conversation,
      security_events
    };
  };

  // Fetch all threads from backend
  const fetchAllThreads = useCallback(async () => {
    try {
      setLoading(true);
      // Use /api/security endpoint which reads from security_logs collection
      const response = await fetch(`${BACKEND_URL}/api/security`);
      const data = await response.json();
      
      // Transform the data structure to match UI expectations
      const transformedThreads = (data.sessions || []).map(thread => {
        if (!thread.conversations) {
          return thread;
        }
        
        // Transform each conversation's messages to security_events
        const transformedConversations = thread.conversations.map(transformConversationData);
        
        return {
          ...thread,
          conversations: transformedConversations
        };
      });
      
      setThreads(transformedThreads);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch threads:', error);
      setLoading(false);
    }
  }, [BACKEND_URL]);

  // Delete a thread
  const deleteThread = useCallback(async (threadId) => {
    try {
      // Find the bot_id for this thread to use in delete endpoint
      const thread = threads.find(t => t.thread_id === threadId || t.bot_id === threadId);
      const botIdToDelete = thread?.bot_id || threadId;
      
      await fetch(`${BACKEND_URL}/api/security/${botIdToDelete}`, {
        method: 'DELETE'
      });
      await fetchAllThreads();
      return true;
    } catch (error) {
      console.error('Failed to delete thread:', error);
      return false;
    }
  }, [BACKEND_URL, threads, fetchAllThreads]);

  // Clear all threads
  const clearAllThreads = useCallback(async () => {
    try {
      await Promise.all(threads.map(thread => 
        fetch(`${BACKEND_URL}/api/security-logs/${thread.thread_id || thread.bot_id}`, { method: 'DELETE' })
      ));
      await fetchAllThreads();
      return true;
    } catch (error) {
      console.error('Failed to clear all threads:', error);
      return false;
    }
  }, [BACKEND_URL, threads, fetchAllThreads]);

  // Filter and sort threads
  const filteredThreads = useMemo(() => {
    let filtered = [...normalizedThreads];

    // Search filtering
    if (searchTerm) {
      const lowerSearch = searchTerm.toLowerCase();
      
      if (searchMode === 'threadId') {
        filtered = filtered.filter(thread =>
          (thread.thread_id || '').toLowerCase().includes(lowerSearch)
        );
      } else if (searchMode === 'userId') {
        filtered = filtered.filter(thread =>
          (thread.user_id || thread.user_id || '').toLowerCase().includes(lowerSearch)
        );
      } else if (searchMode === 'prompt') {
        // Search in all conversations and messages
        filtered = filtered.filter(thread =>
          thread.conversations?.some(conv =>
            conv.messages?.some(msg =>
              (msg.text || '').toLowerCase().includes(lowerSearch) ||
              (msg.validation?.prompt || '').toLowerCase().includes(lowerSearch)
            )
          )
        );
      }
    }

    // Threat filtering
    if (filterType === 'threats') {
      filtered = filtered.filter(thread =>
        thread.pii_detections > 0 ||
        thread.jailbreak_attempts > 0 ||
        thread.toxicity_detections > 0 ||
        thread.secrets_detections > 0 ||
        thread.blocked_prompts > 0
      );
    } else if (filterType === 'clean') {
      filtered = filtered.filter(thread =>
        thread.pii_detections === 0 &&
        thread.jailbreak_attempts === 0 &&
        thread.toxicity_detections === 0 &&
        thread.secrets_detections === 0 &&
        thread.blocked_prompts === 0
      );
    } else if (filterType === 'pii') {
      filtered = filtered.filter(thread => thread.pii_detections > 0);
    } else if (filterType === 'jailbreak') {
      filtered = filtered.filter(thread => thread.jailbreak_attempts > 0);
    } else if (filterType === 'toxicity') {
      filtered = filtered.filter(thread => thread.toxicity_detections > 0);
    } else if (filterType === 'secrets') {
      filtered = filtered.filter(thread => thread.secrets_detections > 0);
    }

    // Sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'date-desc':
          return new Date(b.last_updated || b.created_at) - new Date(a.last_updated || a.created_at);
        case 'date-asc':
          return new Date(a.last_updated || a.created_at) - new Date(b.last_updated || b.created_at);
        case 'threats-desc': {
          const threatsA = (a.pii_detections || 0) + (a.jailbreak_attempts || 0) + 
                          (a.toxicity_detections || 0) + (a.secrets_detections || 0);
          const threatsB = (b.pii_detections || 0) + (b.jailbreak_attempts || 0) + 
                          (b.toxicity_detections || 0) + (b.secrets_detections || 0);
          return threatsB - threatsA;
        }
        case 'prompts-desc':
          return (b.total_prompts || 0) - (a.total_prompts || 0);
        case 'conversations-desc':
          return (b.total_conversations || 0) - (a.total_conversations || 0);
        default:
          return 0;
      }
    });

    return filtered;
  }, [normalizedThreads, searchTerm, searchMode, filterType, sortBy]);

  // Paginated threads
  const paginatedThreads = useMemo(() => {
    const indexOfLastItem = currentPage * itemsPerPage;
    const indexOfFirstItem = indexOfLastItem - itemsPerPage;
    return filteredThreads.slice(indexOfFirstItem, indexOfLastItem);
  }, [filteredThreads, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filteredThreads.length / itemsPerPage);

  // Toggle thread expansion
  // Thread navigation handlers
  const handleThreadClick = useCallback((threadId) => {
    const thread = threads.find(t => t.thread_id === threadId);
    setSelectedThreadId(threadId);
    setSelectedThread(thread);
    setView('details');
  }, [threads]);

  const handleBackToOverview = useCallback(() => {
    setView('overview');
    setSelectedThreadId(null);
    setSelectedThread(null);
  }, []);

  // Initialize on mount
  useEffect(() => {
    fetchAllThreads();
  }, [fetchAllThreads]);

  // Reset pagination on filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filterType, sortBy]);

  // Chart data generators
  const getThreatDistributionData = useMemo(() => [
    { name: 'PII Detected', value: stats.totalPII, color: '#f59e0b', filterType: 'pii' },
    { name: 'Secrets Detected', value: stats.totalSecrets, color: '#8b5cf6', filterType: 'secrets' },
    { name: 'Jailbreak Attempts', value: stats.totalJailbreaks, color: '#ef4444', filterType: 'jailbreak' },
    { name: 'Toxicity', value: stats.totalToxicity, color: '#dc2626', filterType: 'toxicity' },
    { 
      name: 'Clean Threads', 
      value: threads.filter(t => 
        t.pii_detections === 0 && t.jailbreak_attempts === 0 && 
        t.toxicity_detections === 0 && t.secrets_detections === 0
      ).length, 
      color: '#10b981', 
      filterType: 'clean' 
    }
  ].filter(item => item.value > 0), [stats, threads]);

  const getTimelineData = useMemo(() => {
    const grouped = {};
    
    threads.forEach(thread => {
      thread.conversations?.forEach(conv => {
        const dateObj = new Date(conv.started_at);
        const date = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        if (!grouped[date]) {
          grouped[date] = { date, conversations: 0, threats: 0, prompts: 0 };
        }
        
        grouped[date].conversations += 1;
        grouped[date].prompts += conv.total_prompts || 0;
        grouped[date].threats += (conv.pii_detections || 0) + (conv.jailbreak_attempts || 0) + 
                                (conv.toxicity_detections || 0) + (conv.blocked_prompts || 0);
      });
    });

    return Object.values(grouped)
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .slice(-14);
  }, [threads]);

  const getThreatTypeData = useMemo(() => [
    { name: 'PII', count: stats.totalPII, color: '#f59e0b', filterType: 'pii' },
    { name: 'Secrets', count: stats.totalSecrets, color: '#8b5cf6', filterType: 'secrets' },
    { name: 'Jailbreak', count: stats.totalJailbreaks, color: '#ef4444', filterType: 'jailbreak' },
    { name: 'Toxicity', count: stats.totalToxicity, color: '#dc2626', filterType: 'toxicity' }
  ].filter(item => item.count > 0), [stats]);

  const getTopThreateningThreads = useMemo(() => 
    [...threads]
      .map(t => ({
        id: (t.thread_id || 'unknown').substring(0, 20) + '...',
        fullId: t.thread_id || 'unknown',
        threats: (t.pii_detections || 0) + (t.jailbreak_attempts || 0) + 
                (t.toxicity_detections || 0) + (t.secrets_detections || 0)
      }))
      .filter(t => t.threats > 0)
      .sort((a, b) => b.threats - a.threats)
      .slice(0, 10),
  [threads]);

  // Event handlers
  const handleChartClick = useCallback((data) => {
    if (data?.filterType) {
      setFilterType(data.filterType);
      setView('overview');
      setSearchTerm('');
    }
  }, []);

  const handleDeleteThread = useCallback(async (threadId, e) => {
    e.stopPropagation();
    if (window.confirm(`Delete thread ${(threadId || 'unknown').substring(0, 24)}...?`)) {
      await deleteThread(threadId);
    }
  }, [deleteThread]);

  const handleClearAll = useCallback(async () => {
    if (window.confirm('⚠️ Delete ALL threads? This cannot be undone.')) {
      await clearAllThreads();
    }
  }, [clearAllThreads]);

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ fontSize: '48px', marginBottom: '20px' }}>⏳</div>
        <div style={{ fontSize: '18px', color: '#6b7280' }}>Loading security logs...</div>
      </div>
    );
  }

  return (
    <>
      <style>{dashboardStyles}</style>
      <div className="dashboard-container">
        <DashboardHeader stats={stats} />

        {/* View Toggle */}
        <div className="view-toggle">
          <button 
            className={`view-btn ${view === 'overview' ? 'active' : ''}`}
            onClick={() => setView('overview')}
          >
            📊 Threads Overview
          </button>
          <button 
            className={`view-btn ${view === 'analytics' ? 'active' : ''}`}
            onClick={() => setView('analytics')}
          >
            📈 Analytics
          </button>
        </div>

        {/* Stats Grid */}
        <StatsGrid stats={{
          totalSessions: stats.totalThreads,
          totalPrompts: stats.totalPrompts,
          totalBlocked: stats.totalBlocked,
          totalPII: stats.totalPII,
          totalSecrets: stats.totalSecrets,
          totalJailbreaks: stats.totalJailbreaks,
          totalToxicity: stats.totalToxicity
        }} />

        {view === 'details' ? (
          /* Thread Detail View */
          <ThreadDetailView 
            thread={selectedThread}
            onBack={handleBackToOverview}
            onDelete={handleDeleteThread}
          />
        ) : view === 'overview' ? (
          <>
            {/* Filters and Controls */}
            <div className="controls-section">
              <SearchBox 
                searchTerm={searchTerm}
                searchMode={searchMode}
                onSearchChange={setSearchTerm}
                onModeChange={() => {
                  setSearchMode(prev => {
                    if (prev === 'threadId') return 'userId';
                    if (prev === 'userId') return 'prompt';
                    return 'threadId';
                  });
                  setSearchTerm('');
                }}
              />

              <FilterGroup 
                filterType={filterType}
                onFilterChange={(filter) => {
                  setFilterType(filter);
                  setSearchTerm('');
                }}
              />

              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <SortDropdown 
                  sortBy={sortBy}
                  onSortChange={setSortBy}
                />

                <ActionButtons 
                  sessionsCount={threads.length}
                  onExportClick={() => setShowExportMenu(!showExportMenu)}
                  onRefreshClick={fetchAllThreads}
                  onClearClick={handleClearAll}
                  showExportMenu={showExportMenu}
                />
              </div>
            </div>

            {showExportMenu && (
              <ExportMenu 
                sessions={threads}
                filteredSessions={filteredThreads}
                backendUrl={BACKEND_URL}
                onExportComplete={() => setShowExportMenu(false)}
              />
            )}

            {/* Results Summary */}
            <div className="results-summary">
              Showing {filteredThreads.length} thread{filteredThreads.length !== 1 ? 's' : ''} 
              {searchTerm && ` matching "${searchTerm}"`}
              {filterType !== 'all' && ` with filter: ${filterType}`}
            </div>

            {/* Threads Table */}
            <ThreadsTable 
              threads={paginatedThreads}
              onThreadClick={handleThreadClick}
              onDeleteThread={handleDeleteThread}
            />

            {/* Pagination */}
            {totalPages > 1 && (
              <PaginationControls 
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
                itemsPerPage={itemsPerPage}
                totalItems={filteredThreads.length}
              />
            )}
          </>
        ) : (
          /* Analytics View */
          <div className="charts-grid">
            <ChartContainer title="🎯 Threat Distribution">
              <ThreatDistributionChart 
                data={getThreatDistributionData} 
                onDataClick={handleChartClick}
              />
            </ChartContainer>

            <ChartContainer title="📅 Activity Timeline">
              <TimelineChart data={getTimelineData} />
            </ChartContainer>

            <ChartContainer title="⚠️ Threat Types Breakdown">
              <ThreatTypeChart 
                data={getThreatTypeData} 
                onDataClick={handleChartClick}
              />
            </ChartContainer>

            <ChartContainer title="🔥 Top Threatening Threads">
              <TopThreateningChart 
                data={getTopThreateningThreads} 
                onDataClick={(data) => {
                  if (data?.fullId) {
                    // Navigate to this thread's detail view
                    handleThreadClick(data.fullId);
                  }
                }}
              />
            </ChartContainer>
          </div>
        )}
      </div>
    </>
  );
};

/**
 * ThreadsTable Component - Simple clickable thread list
 */
const ThreadsTable = ({ 
  threads, 
  onThreadClick, 
  onDeleteThread 
}) => {
  if (threads.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🔭</div>
        <div className="empty-state-title">No threads found</div>
        <div>Start conversations to see security analytics here</div>
      </div>
    );
  }

  return (
    <div className="threads-container">
      {threads.map(thread => (
        <ThreadRow 
          key={thread.thread_id}
          thread={thread}
          onClick={() => onThreadClick(thread.thread_id)}
          onDelete={(e) => onDeleteThread(thread.thread_id, e)}
        />
      ))}
    </div>
  );
};

/**
 * ThreadRow Component - Simple clickable thread row
 */
const ThreadRow = ({ 
  thread, 
  onClick,
  onDelete 
}) => {
  const totalThreats = (thread.pii_detections || 0) + (thread.jailbreak_attempts || 0) + 
                      (thread.toxicity_detections || 0) + (thread.secrets_detections || 0);
  
  const hasThreats = totalThreats > 0;

  return (
    <div className="thread-card">
      {/* Thread Header */}
      <div 
        className={`thread-header ${hasThreats ? 'has-threats' : 'clean'}`}
        onClick={onClick}
      >
        <div className="thread-expand-icon">
          ▶
        </div>
        
        <div className="thread-info">
          <div className="thread-id-row">
            <span className="thread-id-label">Thread:</span>
            <span className="thread-id">{thread.thread_id}</span>
          </div>
          <div className="thread-meta">
            <span>👤 User: {thread.user_id || 'N/A'}</span>
            <span>💬 {thread.total_conversations || 0} conversation{thread.total_conversations !== 1 ? 's' : ''}</span>
            <span>📝 {thread.total_prompts || 0} prompts</span>
            <span>🕐 {getRelativeTime(thread.last_updated || thread.created_at)}</span>
          </div>
        </div>

        <div className="thread-threats">
          {hasThreats ? (
            <div className="threat-summary">
              <span className="threat-count">⚠️ {totalThreats} threats</span>
              <div className="threat-badges-compact">
                {thread.pii_detections > 0 && <span className="badge-pii">{thread.pii_detections} PII</span>}
                {thread.secrets_detections > 0 && <span className="badge-secrets">{thread.secrets_detections} SEC</span>}
                {thread.jailbreak_attempts > 0 && <span className="badge-jailbreak">{thread.jailbreak_attempts} JB</span>}
                {thread.toxicity_detections > 0 && <span className="badge-toxicity">{thread.toxicity_detections} TOX</span>}
              </div>
            </div>
          ) : (
            <span className="clean-badge">✅ Clean</span>
          )}
        </div>

        <button 
          className="thread-delete-btn"
          onClick={onDelete}
          title="Delete thread"
        >
          🗑️
        </button>
      </div>
    </div>
  );
};

/**
 * ThreadDetailView Component - Shows thread details with collapsible conversations
 */
const ThreadDetailView = ({ thread, onBack, onDelete }) => {
  const [expandedConversations, setExpandedConversations] = useState(new Set());

  const toggleConversation = useCallback((conversationId) => {
    setExpandedConversations(prev => {
      const newSet = new Set(prev);
      if (newSet.has(conversationId)) {
        newSet.delete(conversationId);
      } else {
        newSet.add(conversationId);
      }
      return newSet;
    });
  }, []);

  const totalThreats = (thread.pii_detections || 0) + (thread.jailbreak_attempts || 0) + 
                      (thread.toxicity_detections || 0) + (thread.secrets_detections || 0);

  return (
    <div className="details-container">
      {/* Back Button */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
        <button className="back-btn" onClick={onBack}>
          ← Back to Threads
        </button>
        <button 
          className="btn-delete-session"
          onClick={(e) => {
            e.preventDefault();
            if (window.confirm('Are you sure you want to delete this thread?')) {
              onDelete(thread.thread_id, e);
              onBack();
            }
          }}
        >
          🗑️ Delete Thread
        </button>
      </div>

      {/* Thread Info Grid */}
      <div className="bot-info-grid">
        <div className="info-item">
          <div className="info-label">Thread ID</div>
          <div className="info-value">{thread.thread_id}</div>
        </div>
        <div className="info-item">
          <div className="info-label">User</div>
          <div className="info-value">{thread.user_id || 'N/A'}</div>
        </div>
        <div className="info-item">
          <div className="info-label">Conversations</div>
          <div className="info-value">{thread.total_conversations || 0}</div>
        </div>
        <div className="info-item">
          <div className="info-label">Total Prompts</div>
          <div className="info-value">{thread.total_prompts || 0}</div>
        </div>
        <div className="info-item">
          <div className="info-label">Threats</div>
          <div className="info-value" style={{ color: totalThreats > 0 ? '#dc2626' : '#10b981' }}>
            {totalThreats}
          </div>
        </div>
        <div className="info-item">
          <div className="info-label">Created</div>
          <div className="info-value">{formatDate(thread.created_at)}</div>
        </div>
      </div>

      {/* Conversations Section */}
      <div className="sessions-container" style={{ marginTop: '1.5rem' }}>
        <div className="section-title">
          💬 Conversations ({thread.conversations?.length || 0})
        </div>

        {thread.conversations && thread.conversations.length > 0 ? (
          <div className="conversations-list">
            {thread.conversations.map(conversation => (
              <ConversationRow 
                key={conversation.conversation_id}
                conversation={conversation}
                isExpanded={expandedConversations.has(conversation.conversation_id)}
                onToggle={() => toggleConversation(conversation.conversation_id)}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">💬</div>
            <div className="empty-state-title">No conversations found</div>
            <div>This thread doesn't have any conversations yet</div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * ConversationRow Component - Single conversation with security events
 */
const ConversationRow = ({ conversation, isExpanded, onToggle }) => {
  const convThreats = (conversation.pii_detections || 0) + (conversation.jailbreak_attempts || 0) + 
                     (conversation.toxicity_detections || 0) + (conversation.blocked_prompts || 0);
  
  return (
    <div className="conversation-card">
      {/* Conversation Header */}
      <div 
        className="conversation-header"
        onClick={onToggle}
      >
        <div className="conversation-expand-icon">
          {isExpanded ? '▼' : '▶'}
        </div>
        
        <div className="conversation-info">
          <div className="conversation-id">
            <span className="conversation-label">Conversation:</span>
            <span className="conversation-id-text">{conversation.conversation_id}</span>
          </div>
          <div className="conversation-meta">
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem' }}>
              📝 <strong>{conversation.total_prompts || 0}</strong> message{(conversation.total_prompts || 0) !== 1 ? 's' : ''}
            </span>
            <span style={{ fontSize: '0.8125rem', color: '#a8a29e' }}>
              🕐 {formatDate(conversation.started_at)}
              {conversation.ended_at && ` → ${formatDate(conversation.ended_at)}`}
            </span>
          </div>
        </div>

        <div className="conversation-threats">
          {convThreats > 0 ? (
            <div className="threat-badges-compact">
              {conversation.pii_detections > 0 && (
                <span className="badge-pii">
                  PII <strong style={{ marginLeft: '0.25rem' }}>{conversation.pii_detections}</strong>
                </span>
              )}
              {conversation.jailbreak_attempts > 0 && (
                <span className="badge-jailbreak">
                  JB <strong style={{ marginLeft: '0.25rem' }}>{conversation.jailbreak_attempts}</strong>
                </span>
              )}
              {conversation.toxicity_detections > 0 && (
                <span className="badge-toxicity">
                  TOX <strong style={{ marginLeft: '0.25rem' }}>{conversation.toxicity_detections}</strong>
                </span>
              )}
              {conversation.blocked_prompts > 0 && (
                <span className="badge-blocked">
                  BLK <strong style={{ marginLeft: '0.25rem' }}>{conversation.blocked_prompts}</strong>
                </span>
              )}
            </div>
          ) : (
            <span className="clean-badge-small">✅</span>
          )}
        </div>
      </div>

      {/* Expanded Security Events */}
      {isExpanded && (
        <div className="events-list">
          {conversation.security_events && conversation.security_events.length > 0 ? (
            conversation.security_events.map((event, idx) => (
              <SecurityEventCard key={idx} event={event} index={idx + 1} />
            ))
          ) : (
            <div className="empty-state" style={{ 
              padding: '2rem', 
              textAlign: 'center',
              backgroundColor: 'rgba(249,115,22,0.05)',
              borderRadius: '8px',
              margin: '1rem 0'
            }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📭</div>
              <div style={{ color: '#78716c', fontSize: '0.875rem' }}>
                No security events found in this conversation
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * SecurityEventCard Component - Individual security event (message validation)
 */
const SecurityEventCard = ({ event, index }) => {
  // Determine background color
  let bgColor = '#d4edda'; // Green for safe
  let borderColor = '#28a745';
  
  if (event.detections?.pii?.detected) {
    bgColor = '#fff3cd'; // Yellow for PII
    borderColor = '#ffc107';
  } else if (event.blocked) {
    bgColor = '#f8d7da'; // Red for blocked
    borderColor = '#dc3545';
  }

  const hasDetections = event.detections && 
    Object.entries(event.detections).some(([, result]) => result.detected);

  return (
    <div 
      className="event-card"
      style={{ 
        backgroundColor: bgColor,
        borderLeft: `4px solid ${borderColor}`
      }}
    >
      {/* Event Header */}
      <div className="event-header">
        <span className="event-number">#{index}</span>
        <span className="event-timestamp">🕐 {formatDate(event.timestamp)}</span>
        <span className={`event-status ${event.blocked ? 'blocked' : 'safe'}`}>
          {event.blocked ? '🚫 BLOCKED' : '✅ SAFE'}
        </span>
        {event.risk_level && (
          <span className={`risk-badge risk-${event.risk_level.toLowerCase()}`}>
            {event.risk_level}
          </span>
        )}
      </div>

      {/* Prompt */}
      <div className="event-section">
        <div className="event-section-title">📝 Prompt</div>
        <div className="event-text" style={{ 
          fontFamily: '"SF Mono", "Monaco", "Consolas", monospace',
          fontSize: '0.875rem',
          lineHeight: '1.6'
        }}>
          {event.prompt || 'N/A'}
        </div>
      </div>

      {/* Detected Threats */}
      {hasDetections && (
        <div className="event-section">
          <div className="event-section-title">🔍 Detected Threats</div>
          <div className="detections-grid">
            {Object.entries(event.detections).map(([scannerName, result]) => 
              result.detected && (
                <div key={scannerName} className="detection-badge threat">
                  <div className="detection-name" style={{ fontWeight: '700', marginBottom: '0.25rem' }}>
                    {scannerName}
                  </div>
                  <div className="detection-status" style={{ fontSize: '0.75rem' }}>
                    ⚠️ DETECTED
                  </div>
                  {result.entities_found > 0 && (
                    <div className="detection-count" style={{ 
                      fontSize: '0.75rem',
                      marginTop: '0.25rem',
                      fontWeight: '600'
                    }}>
                      {result.entities_found} entities
                    </div>
                  )}
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Block Reason */}
      {event.blocked && event.block_reason && (
        <div className="event-section">
          <div className="event-section-title">🛡️ Block Reason</div>
          <div className="block-reason" style={{
            fontFamily: '"SF Mono", "Monaco", "Consolas", monospace',
            fontSize: '0.875rem',
            lineHeight: '1.6',
            padding: '0.75rem',
            backgroundColor: 'rgba(220,38,38,0.1)',
            borderRadius: '0.375rem'
          }}>
            {event.block_reason}
          </div>
        </div>
      )}

      {/* LLM Response */}
      {!event.blocked && event.llm_response && (
        <div className="event-section">
          <div className="event-section-title">💬 Response</div>
          <div className="llm-response" style={{
            fontFamily: '"SF Mono", "Monaco", "Consolas", monospace',
            fontSize: '0.875rem',
            lineHeight: '1.6'
          }}>
            {event.llm_response}
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      {event.metrics && (
        <div className="event-section">
          <div className="event-section-title">⏱️ Performance</div>
          <div className="metrics-grid">
            {event.metrics.scan_time && (
              <div className="metric-box">
                <div className="metric-label">Scan Time</div>
                <div className="metric-value" style={{ fontWeight: '700' }}>
                  {event.metrics.scan_time.toFixed(3)}s
                </div>
              </div>
            )}
            {event.metrics.llm_time && (
              <div className="metric-box">
                <div className="metric-label">LLM Time</div>
                <div className="metric-value" style={{ fontWeight: '700' }}>
                  {event.metrics.llm_time.toFixed(3)}s
                </div>
              </div>
            )}
            {event.metrics.total_time && (
              <div className="metric-box">
                <div className="metric-label">Total Time</div>
                <div className="metric-value" style={{ fontWeight: '700' }}>
                  {event.metrics.total_time.toFixed(3)}s
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};  

export default AnalyticsDashboard;