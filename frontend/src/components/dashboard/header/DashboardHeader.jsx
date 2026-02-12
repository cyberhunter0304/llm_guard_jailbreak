import React, { memo } from 'react';
import logo from '../../loco.png';

/**
 * DashboardHeader Component - Clean minimal design
 * Logo outside orange box on the left, same height as title container
 * Memoized for performance optimization
 */
const DashboardHeader = memo(({ stats, isIndexingPrompts }) => {
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'stretch',
      gap: '1.5rem',
      marginBottom: '2rem'
    }}>
      {/* Logo - Same height as title container */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        maxHeight: '120px'
      }}>
        <img 
          src={logo} 
          alt="iNextLabs" 
          style={{ 
            height: 'auto',
            maxHeight: '100px',
            width: 'auto',
            display: 'block',
            objectFit: 'contain'
          }} 
        />
      </div>

      {/* Main Header Section - Orange box with title only */}
      <div className="dashboard-header" style={{ flex: 1 }}>
        <div className="header-content">
          <div className="dashboard-title">
            <span>inFlow Shield</span>
          </div>
          <div className="dashboard-subtitle">
            Real-time monitoring of AI security guardrails and threat detection
          </div>
        </div>
      </div>
    </div>
  );
});

DashboardHeader.displayName = 'DashboardHeader';

export default DashboardHeader;