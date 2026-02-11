import React, { memo } from 'react';

/**
 * StatCard Component - Displays a single statistic metric
 * Memoized to prevent unnecessary re-renders
 */
const StatCard = memo(({ icon, label, value, color }) => (
  <div className="stat-card" style={{ borderLeftColor: color }}>
    <div className="stat-icon" style={{ color }}>{icon}</div>
    <div className="stat-content">
      <div className="stat-value">{value.toLocaleString()}</div>
      <div className="stat-label">{label}</div>
    </div>
  </div>
));

StatCard.displayName = 'StatCard';

/**
 * StatsGrid Component - Displays multiple stat cards
 * Memoized to prevent re-renders when props don't change
 */
const StatsGrid = memo(({ stats }) => {
  const statCards = [
    { icon: '💬', label: 'Total Sessions', value: stats.totalSessions, color: '#3b82f6' },
    { icon: '📝', label: 'Total Prompts', value: stats.totalPrompts, color: '#10b981' },
    { icon: '🚫', label: 'Blocked Prompts', value: stats.totalBlocked, color: '#ef4444' },
    { icon: '🔒', label: 'PII Detections', value: stats.totalPII, color: '#f59e0b' },
    { icon: '🔑', label: 'Secrets Detected', value: stats.totalSecrets, color: '#8b5cf6' },
    { icon: '⚠️', label: 'Jailbreak Attempts', value: stats.totalJailbreaks, color: '#dc2626' },
    { icon: '☣️', label: 'Toxicity Detected', value: stats.totalToxicity, color: '#991b1b' }
  ];

  return (
    <div className="stats-grid">
      {statCards.map((card, idx) => (
        <StatCard key={idx} {...card} />
      ))}
    </div>
  );
});

StatsGrid.displayName = 'StatsGrid';

export { StatCard, StatsGrid };
