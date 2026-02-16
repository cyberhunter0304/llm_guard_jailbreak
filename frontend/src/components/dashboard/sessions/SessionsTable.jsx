import React, { memo, useCallback } from 'react';
import { getRelativeTime, formatDate } from '../utils/helpers.js';

/**
 * ThreatBadge Component - Visual badge for threat counts
 */
const ThreatBadge = memo(({ type, count }) => {
  const colors = {
    pii: '#f59e0b',
    secrets: '#8b5cf6',
    jailbreak: '#ef4444',
    toxicity: '#dc2626'
  };
  
  const labels = {
    pii: 'PII',
    secrets: 'SEC',
    jailbreak: 'JB',
    toxicity: 'TOX'
  };
  
  if (count === 0) return null;
  
  return (
    <span className="threat-badge" style={{ backgroundColor: colors[type] }}>
      <span style={{ opacity: 0.9 }}>{labels[type]}</span>
      <span style={{ 
        marginLeft: '0.25rem',
        fontWeight: '700',
        fontSize: '0.8125rem'
      }}>
        {count}
      </span>
    </span>
  );
});

ThreatBadge.displayName = 'ThreatBadge';

/**
 * SessionRow Component - Single session table row
 */
const SessionRow = memo(({ 
  session, 
  promptSearchResults, 
  onSelectSession, 
  onSessionClick,
  isSelected,
  selectionMode 
}) => {
  const promptMatch = promptSearchResults.find(r => r.bot_id === session.bot_id);
  const totalThreats = (session.pii_detections || 0) + (session.secrets_detections || 0) + 
                      (session.jailbreak_attempts || 0) + (session.toxicity_detections || 0);
  
  return (
    <tr>
      {selectionMode && (
        <td className="checkbox-cell" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            className="session-checkbox"
            checked={isSelected}
            onChange={() => onSelectSession(session.bot_id)}
          />
        </td>
      )}
      <td onClick={() => !selectionMode && onSessionClick(session.bot_id)}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <span className="bot-id">{session.bot_id.substring(0, 24)}...</span>
          {promptMatch && (
            <span className="prompt-match-badge">
              💬 {promptMatch.matchCount} match{promptMatch.matchCount !== 1 ? 'es' : ''}
            </span>
          )}
        </div>
      </td>
      <td onClick={() => !selectionMode && onSessionClick(session.bot_id)}>
        <div className="time-info">
          <div className="time-relative">{getRelativeTime(session.created_at)}</div>
          <div className="time-absolute">{formatDate(session.created_at)}</div>
        </div>
      </td>
      <td onClick={() => !selectionMode && onSessionClick(session.bot_id)}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', alignItems: 'center' }}>
          <strong style={{ fontSize: '1.0625rem' }}>{session.total_prompts}</strong>
          {session.blocked_prompts > 0 && (
            <span style={{ color: '#ef4444', fontSize: '0.75rem', fontWeight: '600' }}>
              ({session.blocked_prompts} blocked)
            </span>
          )}
        </div>
      </td>
      <td onClick={() => !selectionMode && onSessionClick(session.bot_id)}>
        {totalThreats > 0 ? (
          <div className="threat-badges">
            <ThreatBadge type="pii" count={session.pii_detections} />
            <ThreatBadge type="secrets" count={session.secrets_detections || 0} />
            <ThreatBadge type="jailbreak" count={session.jailbreak_attempts} />
            <ThreatBadge type="toxicity" count={session.toxicity_detections} />
          </div>
        ) : (
          <span style={{
            padding: '0.25rem 0.625rem',
            borderRadius: '0.375rem',
            fontSize: '0.75rem',
            fontWeight: '700',
            color: '#15803d',
            backgroundColor: 'rgba(16,185,129,0.12)',
            border: '1px solid rgba(16,185,129,0.25)',
            display: 'inline-block'
          }}>
            ✓ Clean
          </span>
        )}
      </td>
    </tr>
  );
});

SessionRow.displayName = 'SessionRow';

/**
 * SessionsTable Component - Table displaying all sessions
 */
const SessionsTable = memo(({ 
  sessions, 
  promptSearchResults, 
  selectionMode,
  selectedSessions,
  onSelectSession,
  onSessionClick 
}) => {
  if (sessions.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📭</div>
        <div className="empty-state-title">No sessions found</div>
        <div>Start a chat to see security analytics here</div>
      </div>
    );
  }

  return (
    <table className="sessions-table">
      <thead>
        <tr>
          {selectionMode && <th className="checkbox-cell">☑️</th>}
          <th>Bot ID</th>
          <th>Created</th>
          <th>Prompts</th>
          <th>Threats Detected</th>
        </tr>
      </thead>
      <tbody>
        {sessions.map((session) => (
          <SessionRow 
            key={session.bot_id}
            session={session}
            promptSearchResults={promptSearchResults}
            onSelectSession={onSelectSession}
            onSessionClick={onSessionClick}
            isSelected={selectedSessions.has(session.bot_id)}
            selectionMode={selectionMode}
          />
        ))}
      </tbody>
    </table>
  );
});

SessionsTable.displayName = 'SessionsTable';

/**
 * ThreadItem Component - Individual thread in the list
 */
const ThreadItem = memo(({ thread, onClick, onDelete }) => {
  // Determine threat class based on detections
  const getThreatClass = () => {
    const threats = [];
    if (thread.pii_detections > 0) threats.push('pii');
    if (thread.secrets_detections > 0) threats.push('secrets');
    if (thread.jailbreak_attempts > 0) threats.push('jailbreak');
    if (thread.toxicity_detections > 0) threats.push('toxicity');
    
    if (threats.length === 0) return 'clean';
    if (threats.length > 1) return 'threat-multiple';
    return `threat-${threats[0]}`;
  };

  // Determine status
  const getStatus = () => {
    const hasThreats = thread.pii_detections > 0 || 
                      thread.secrets_detections > 0 || 
                      thread.jailbreak_attempts > 0 || 
                      thread.toxicity_detections > 0;
    
    if (!hasThreats) return { label: '✓ Clean', className: 'clean' };
    
    const threatCount = (thread.pii_detections || 0) + 
                       (thread.secrets_detections || 0) + 
                       (thread.jailbreak_attempts || 0) + 
                       (thread.toxicity_detections || 0);
    
    if (threatCount > 5) return { label: '⚠️ High Risk', className: 'threats' };
    return { label: '⚠️ Threats', className: 'warning' };
  };

  const status = getStatus();
  const threatClass = getThreatClass();
  const totalThreats = (thread.pii_detections || 0) + (thread.secrets_detections || 0) + 
                      (thread.jailbreak_attempts || 0) + (thread.toxicity_detections || 0);

  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this thread?')) {
      onDelete(thread.thread_id);
    }
  };

  return (
    <div 
      className={`thread-item ${threatClass}`}
      onClick={() => onClick(thread.thread_id)}
    >
      <div className="thread-item-header">
        <span className="thread-arrow">▶</span>
        
        <div className="thread-id">
          <div className="thread-id-label">Thread:</div>
          <div className="thread-id-value">{thread.thread_id}</div>
        </div>

        <div className="thread-meta">
          <div className="thread-meta-item">
            👤 User: <strong>{thread.user_id}</strong>
          </div>
          <div className="thread-meta-item">
            💬 <strong>{thread.conversation_count}</strong> conversation{thread.conversation_count !== 1 ? 's' : ''}
          </div>
          <div className="thread-meta-item">
            📝 <strong>{thread.total_prompts}</strong> prompt{thread.total_prompts !== 1 ? 's' : ''}
          </div>
          <div className="thread-meta-item">
            🕐 {getRelativeTime(thread.created_at)}
          </div>
        </div>

        <div className={`thread-status ${status.className}`}>
          {status.label}
        </div>

        <div className="thread-actions">
          <button 
            className="thread-action-btn delete" 
            onClick={handleDelete}
            title="Delete thread"
          >
            🗑️
          </button>
        </div>
      </div>
      
      {/* Enhanced threat badges display */}
      {totalThreats > 0 && (
        <div style={{
          marginTop: '0.75rem',
          paddingTop: '0.75rem',
          borderTop: '1px solid rgba(249,115,22,0.15)',
          display: 'flex',
          gap: '0.5rem',
          flexWrap: 'wrap'
        }}>
          {thread.pii_detections > 0 && (
            <span style={{
              padding: '0.3125rem 0.625rem',
              borderRadius: '0.375rem',
              fontSize: '0.75rem',
              fontWeight: '700',
              color: '#b45309',
              backgroundColor: 'rgba(245,158,11,0.15)',
              border: '1px solid rgba(245,158,11,0.3)'
            }}>
              PII {thread.pii_detections}
            </span>
          )}
          {(thread.secrets_detections || 0) > 0 && (
            <span style={{
              padding: '0.3125rem 0.625rem',
              borderRadius: '0.375rem',
              fontSize: '0.75rem',
              fontWeight: '700',
              color: '#6d28d9',
              backgroundColor: 'rgba(139,92,246,0.15)',
              border: '1px solid rgba(139,92,246,0.3)'
            }}>
              SEC {thread.secrets_detections}
            </span>
          )}
          {thread.jailbreak_attempts > 0 && (
            <span style={{
              padding: '0.3125rem 0.625rem',
              borderRadius: '0.375rem',
              fontSize: '0.75rem',
              fontWeight: '700',
              color: '#b91c1c',
              backgroundColor: 'rgba(239,68,68,0.15)',
              border: '1px solid rgba(239,68,68,0.3)'
            }}>
              JB {thread.jailbreak_attempts}
            </span>
          )}
          {thread.toxicity_detections > 0 && (
            <span style={{
              padding: '0.3125rem 0.625rem',
              borderRadius: '0.375rem',
              fontSize: '0.75rem',
              fontWeight: '700',
              color: '#991b1b',
              backgroundColor: 'rgba(220,38,38,0.15)',
              border: '1px solid rgba(220,38,38,0.3)'
            }}>
              TOX {thread.toxicity_detections}
            </span>
          )}
        </div>
      )}
    </div>
  );
});

ThreadItem.displayName = 'ThreadItem';

/**
 * ThreadsList Component - Main threads list view
 */
const ThreadsList = memo(({ threads, onThreadClick, onThreadDelete }) => {
  if (threads.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🔭</div>
        <div className="empty-state-title">No threads found</div>
        <div>Threads will appear here as users interact with the system</div>
      </div>
    );
  }

  return (
    <div className="thread-list">
      {threads.map((thread) => (
        <ThreadItem
          key={thread.thread_id}
          thread={thread}
          onClick={onThreadClick}
          onDelete={onThreadDelete}
        />
      ))}
    </div>
  );
});

ThreadsList.displayName = 'ThreadsList';

/**
 * CollapsibleItem Component - For items inside thread detail view
 */
const CollapsibleItem = memo(({ item, index }) => {
  const [isExpanded, setIsExpanded] = React.useState(false);

  return (
    <div className={`thread-detail-item ${isExpanded ? 'expanded' : ''}`}>
      <div 
        className="thread-detail-item-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="thread-detail-item-icon">▶</span>
        
        <div className="thread-detail-item-summary">
          <div className="thread-detail-item-type">
            {item.type || 'Prompt'} #{index + 1}
          </div>
          <div className="thread-detail-item-preview">
            {item.preview || item.prompt?.substring(0, 100) || 'No preview available'}
          </div>
          
          {item.threats && item.threats.length > 0 && (
            <div className="thread-detail-item-badges">
              {item.threats.map((threat, idx) => (
                <span key={idx} className={`thread-detail-badge ${threat.toLowerCase()}`}>
                  {threat}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="thread-detail-item-time">
          {getRelativeTime(item.timestamp)}
        </div>
      </div>

      <div className="thread-detail-item-content">
        {item.prompt && (
          <div className="thread-detail-item-section">
            <div className="thread-detail-item-section-title">Prompt</div>
            <div className="thread-detail-item-section-content">
              {item.prompt}
            </div>
          </div>
        )}

        {item.response && (
          <div className="thread-detail-item-section">
            <div className="thread-detail-item-section-title">Response</div>
            <div className="thread-detail-item-section-content">
              {item.response}
            </div>
          </div>
        )}

        {item.blocked_reason && (
          <div className="thread-detail-item-section">
            <div className="thread-detail-item-section-title">Block Reason</div>
            <div className="thread-detail-item-section-content">
              {item.blocked_reason}
            </div>
          </div>
        )}

        {item.detections && (
          <div className="thread-detail-item-section">
            <div className="thread-detail-item-section-title">Detection Details</div>
            <div className="thread-detail-item-section-content">
              {JSON.stringify(item.detections, null, 2)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

CollapsibleItem.displayName = 'CollapsibleItem';

/**
 * ThreadDetailView Component - Shows items inside a thread
 */
const ThreadDetailView = memo(({ thread, items }) => {
  if (!items || items.length === 0) {
    return (
      <div className="thread-detail-empty">
        <div className="thread-detail-empty-icon">📭</div>
        <div className="thread-detail-empty-text">
          No items found in this thread
        </div>
      </div>
    );
  }

  return (
    <div className="thread-detail-container">
      <div className="thread-detail-header">
        <div className="thread-detail-title">
          Thread Items
        </div>
        <div className="thread-detail-count">
          {items.length} item{items.length !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="thread-detail-items">
        {items.map((item, index) => (
          <CollapsibleItem
            key={item.id || index}
            item={item}
            index={index}
          />
        ))}
      </div>
    </div>
  );
});

ThreadDetailView.displayName = 'ThreadDetailView';

export { 
  ThreatBadge, 
  SessionRow, 
  SessionsTable,
  ThreadItem,
  ThreadsList,
  CollapsibleItem,
  ThreadDetailView
};