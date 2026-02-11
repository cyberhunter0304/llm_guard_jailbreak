import React, { memo } from 'react';
import logo from '../../loco.png';

/**
 * DashboardHeader Component - Main header with title and key stats
 * Memoized for performance optimization
 */
const DashboardHeader = memo(({ stats, isIndexingPrompts }) => {
  return (
    <div className="dashboard-header">
      <div className="header-content">
        <div className="dashboard-title">
          <div className="app-logo">
            <img src={logo} alt="iNextLabs" />
          </div>
          <span>inFlow Shield</span>
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
          {isIndexingPrompts && (
            <div className="header-stat">
              <div className="header-stat-value">⏳</div>
              <div className="header-stat-label">Indexing Prompts...</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

DashboardHeader.displayName = 'DashboardHeader';

export default DashboardHeader;
