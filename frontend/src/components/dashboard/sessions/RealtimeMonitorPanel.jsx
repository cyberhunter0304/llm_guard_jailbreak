/**
 * RealtimeMonitorPanel Component
 * Display real-time monitoring status and recent processing events
 */
import React, { memo } from 'react';
import useRealtimeMonitor from './useRealtimeMonitor';
import { formatDate, getRelativeTime } from '../utils/helpers';

const RealtimeMonitorPanel = memo(({ backendUrl }) => {
  const {
    isConnected,
    isMonitoring,
    stats,
    recentEvents,
    error,
    startMonitor,
    stopMonitor
  } = useRealtimeMonitor(backendUrl, true);

  const handleToggleMonitor = async () => {
    if (isMonitoring) {
      await stopMonitor();
    } else {
      await startMonitor();
    }
  };

  return (
    <div className="monitor-panel">
      {/* Monitor Control */}
      <div className="monitor-control">
        <div className="monitor-status">
          <div className="status-indicator-container">
            <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`} />
            <span className="status-text">
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </span>
          </div>
          
          {isMonitoring && (
            <div className="monitoring-badge">
              <span className="pulse-dot"></span>
              <span>Real-time Monitoring Active</span>
            </div>
          )}
        </div>

        <button 
          className={`monitor-toggle-btn ${isMonitoring ? 'stop' : 'start'}`}
          onClick={handleToggleMonitor}
        >
          {isMonitoring ? '⏹️ Stop Monitor' : '▶️ Start Monitor'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="monitor-error">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Stats */}
      <div className="monitor-stats">
        <div className="stat-item">
          <div className="stat-label">Processed</div>
          <div className="stat-value success">{stats.processedCount}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Errors</div>
          <div className="stat-value error">{stats.errorCount}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Success Rate</div>
          <div className="stat-value">
            {stats.processedCount > 0 
              ? `${Math.round((stats.processedCount / (stats.processedCount + stats.errorCount)) * 100)}%`
              : 'N/A'}
          </div>
        </div>
      </div>

      {/* Recent Events */}
      <div className="recent-events">
        <div className="events-header">
          <h3>📊 Recent Processing Events</h3>
          <span className="events-count">{recentEvents.length} events</span>
        </div>
        
        <div className="events-list">
          {recentEvents.length === 0 ? (
            <div className="empty-events">
              <div className="empty-icon">👀</div>
              <div>Waiting for conversations to process...</div>
            </div>
          ) : (
            recentEvents.map((event, idx) => (
              <EventCard key={idx} event={event} />
            ))
          )}
        </div>
      </div>

      <style jsx>{`
        .monitor-panel {
          background: linear-gradient(135deg, #fff5e6 0%, #fffbf5 100%);
          border: 2px solid #fed7aa;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 2rem;
        }

        .monitor-control {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          padding-bottom: 1rem;
          border-bottom: 2px solid rgba(249,115,22,0.15);
        }

        .monitor-status {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .status-indicator-container {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .status-indicator {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          transition: all 0.3s ease;
        }

        .status-indicator.connected {
          background: #10b981;
          box-shadow: 0 0 8px rgba(16,185,129,0.5);
        }

        .status-indicator.disconnected {
          background: #ef4444;
          box-shadow: 0 0 8px rgba(239,68,68,0.5);
        }

        .status-text {
          font-size: 0.875rem;
          font-weight: 600;
          color: #78716c;
        }

        .monitoring-badge {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          background: rgba(16,185,129,0.1);
          border: 1px solid rgba(16,185,129,0.3);
          padding: 0.375rem 0.75rem;
          border-radius: 6px;
          font-size: 0.8125rem;
          font-weight: 600;
          color: #059669;
        }

        .pulse-dot {
          width: 8px;
          height: 8px;
          background: #10b981;
          border-radius: 50%;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
        }

        .monitor-toggle-btn {
          padding: 0.625rem 1.25rem;
          border-radius: 8px;
          border: none;
          font-weight: 600;
          font-size: 0.9375rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .monitor-toggle-btn.start {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          box-shadow: 0 4px 12px rgba(16,185,129,0.3);
        }

        .monitor-toggle-btn.start:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(16,185,129,0.4);
        }

        .monitor-toggle-btn.stop {
          background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
          color: white;
          box-shadow: 0 4px 12px rgba(239,68,68,0.3);
        }

        .monitor-toggle-btn.stop:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(239,68,68,0.4);
        }

        .monitor-error {
          background: rgba(239,68,68,0.1);
          border: 1px solid rgba(239,68,68,0.3);
          padding: 0.75rem 1rem;
          border-radius: 8px;
          margin-bottom: 1rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: #dc2626;
          font-size: 0.875rem;
          font-weight: 500;
        }

        .monitor-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .stat-item {
          background: white;
          padding: 1rem;
          border-radius: 8px;
          border: 1px solid #fde68a;
          text-align: center;
        }

        .stat-label {
          font-size: 0.75rem;
          color: #78716c;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 0.5rem;
        }

        .stat-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: #292524;
        }

        .stat-value.success {
          color: #10b981;
        }

        .stat-value.error {
          color: #ef4444;
        }

        .recent-events {
          background: white;
          border-radius: 8px;
          padding: 1rem;
          border: 1px solid #fde68a;
        }

        .events-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
          padding-bottom: 0.75rem;
          border-bottom: 1px solid #fef3c7;
        }

        .events-header h3 {
          margin: 0;
          font-size: 1rem;
          color: #292524;
        }

        .events-count {
          font-size: 0.75rem;
          color: #78716c;
          font-weight: 600;
          background: #fef3c7;
          padding: 0.25rem 0.625rem;
          border-radius: 4px;
        }

        .events-list {
          max-height: 400px;
          overflow-y: auto;
        }

        .empty-events {
          text-align: center;
          padding: 2rem;
          color: #a8a29e;
        }

        .empty-icon {
          font-size: 3rem;
          margin-bottom: 0.5rem;
        }
      `}</style>
    </div>
  );
});

RealtimeMonitorPanel.displayName = 'RealtimeMonitorPanel';

/**
 * EventCard Component - Display individual processing event
 */
const EventCard = memo(({ event }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'in-progress': return '#f59e0b';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return '✅';
      case 'in-progress': return '⚙️';
      case 'error': return '❌';
      default: return '📝';
    }
  };

  return (
    <div className="event-card">
      <div className="event-header">
        <span className="event-icon">{getStatusIcon(event.status)}</span>
        <span className="event-type">{event.type}</span>
        <span className="event-time">{getRelativeTime(event.timestamp)}</span>
      </div>

      <div className="event-details">
        <div className="event-id">
          Conv: {event.conversation_id?.substring(0, 24)}...
        </div>
        
        {event.success && event.security_events_created > 0 && (
          <div className="event-stats">
            <span>📝 {event.security_events_created} events</span>
            {event.pii_detections > 0 && <span className="threat-badge pii">PII {event.pii_detections}</span>}
            {event.jailbreak_attempts > 0 && <span className="threat-badge jb">JB {event.jailbreak_attempts}</span>}
            {event.toxicity_detections > 0 && <span className="threat-badge tox">TOX {event.toxicity_detections}</span>}
          </div>
        )}

        {event.error && (
          <div className="event-error">
            {event.error}
          </div>
        )}
      </div>

      <style jsx>{`
        .event-card {
          background: #fffbf5;
          border: 1px solid #fde68a;
          border-radius: 6px;
          padding: 0.75rem;
          margin-bottom: 0.5rem;
          transition: all 0.2s ease;
        }

        .event-card:hover {
          border-color: #f97316;
          box-shadow: 0 2px 8px rgba(249,115,22,0.1);
        }

        .event-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.5rem;
        }

        .event-icon {
          font-size: 1rem;
        }

        .event-type {
          font-size: 0.75rem;
          font-weight: 700;
          text-transform: uppercase;
          color: ${getStatusColor(event.status)};
          letter-spacing: 0.5px;
        }

        .event-time {
          margin-left: auto;
          font-size: 0.6875rem;
          color: #a8a29e;
        }

        .event-details {
          font-size: 0.8125rem;
        }

        .event-id {
          color: #57534e;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.75rem;
          margin-bottom: 0.375rem;
        }

        .event-stats {
          display: flex;
          gap: 0.375rem;
          flex-wrap: wrap;
          align-items: center;
          font-size: 0.75rem;
        }

        .threat-badge {
          padding: 0.125rem 0.375rem;
          border-radius: 4px;
          font-weight: 600;
          font-size: 0.6875rem;
        }

        .threat-badge.pii {
          background: rgba(245,158,11,0.15);
          color: #b45309;
          border: 1px solid rgba(245,158,11,0.3);
        }

        .threat-badge.jb {
          background: rgba(239,68,68,0.15);
          color: #b91c1c;
          border: 1px solid rgba(239,68,68,0.3);
        }

        .threat-badge.tox {
          background: rgba(220,38,38,0.15);
          color: #991b1b;
          border: 1px solid rgba(220,38,38,0.3);
        }

        .event-error {
          color: #dc2626;
          font-size: 0.75rem;
          background: rgba(239,68,68,0.1);
          padding: 0.375rem;
          border-radius: 4px;
          margin-top: 0.375rem;
        }
      `}</style>
    </div>
  );
});

EventCard.displayName = 'EventCard';

export default RealtimeMonitorPanel;