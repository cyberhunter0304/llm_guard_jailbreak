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
      {labels[type]}: {count}
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
        <span className="bot-id">{session.bot_id.substring(0, 24)}...</span>
        {promptMatch && (
          <span className="prompt-match-badge">
            💬 {promptMatch.matchCount} match{promptMatch.matchCount !== 1 ? 'es' : ''}
          </span>
        )}
      </td>
      <td onClick={() => !selectionMode && onSessionClick(session.bot_id)}>
        <div className="time-info">
          <div className="time-relative">{getRelativeTime(session.created_at)}</div>
          <div className="time-absolute">{formatDate(session.created_at)}</div>
        </div>
      </td>
      <td onClick={() => !selectionMode && onSessionClick(session.bot_id)}>
        <strong>{session.total_prompts}</strong>
        {session.blocked_prompts > 0 && (
          <span style={{ color: '#ef4444', marginLeft: 8, fontSize: 13 }}>({session.blocked_prompts} blocked)</span>
        )}
      </td>
      <td onClick={() => !selectionMode && onSessionClick(session.bot_id)}>
        <div className="threat-badges">
          <ThreatBadge type="pii" count={session.pii_detections} />
          <ThreatBadge type="secrets" count={session.secrets_detections || 0} />
          <ThreatBadge type="jailbreak" count={session.jailbreak_attempts} />
          <ThreatBadge type="toxicity" count={session.toxicity_detections} />
        </div>
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

export { ThreatBadge, SessionRow, SessionsTable };
