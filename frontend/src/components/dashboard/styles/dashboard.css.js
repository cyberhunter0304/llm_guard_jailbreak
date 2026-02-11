// All existing styles from the original AnalyticsDashboard
// This would contain the full CSS from the original file
// For brevity, creating a reference to import from original styling

const dashboardStyles = `
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f8fafc;
}

.dashboard-container {
  min-height: 100vh;
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.dashboard-header {
  background: linear-gradient(135deg, #fbfbfb 0%, #F15843 100%);
  color: white;
  padding: 32px;
  border-radius: 20px;
  margin-bottom: 28px;
  box-shadow: 0 8px 24px rgba(255, 107, 53, 0.25);
  position: relative;
  overflow: hidden;
}

.dashboard-header::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
  border-radius: 50%;
  transform: translate(30%, -30%);
}

.header-content {
  position: relative;
  z-index: 1;
}

.dashboard-title {
  font-size: 32px;
  font-weight: 800;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: black;
}

.dashboard-subtitle {
  font-size: 16px;
  opacity: 0.95;
  color: black;
}

.header-stats {
  display: flex;
  gap: 32px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.2);
}

.header-stat {
  display: flex;
  flex-direction: column;
}

.header-stat-value {
  font-size: 28px;
  font-weight: 700;
  color: black;
}

.header-stat-label {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 4px;
  color: black;
}

.view-toggle {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.toggle-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
  color: #6b7280;
  box-shadow: 0 2px 4px rgba(0,0,0,0.06);
}

.toggle-btn.active {
  background: linear-gradient(135deg, #F15843 0%, #fc7777 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 28px;
}

.stat-card {
  background: white;
  padding: 24px;
  border-radius: 16px;
  border-left: 4px solid;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  display: flex;
  gap: 16px;
  align-items: center;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0,0,0,0.1);
}

.stat-icon {
  font-size: 36px;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 107, 53, 0.1);
  border-radius: 14px;
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

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
  gap: 24px;
  margin-bottom: 28px;
}

.chart-container {
  background: white;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  position: relative;
}

.chart-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.controls-section {
  background: white;
  padding: 20px;
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.controls-row {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  flex: 1;
  min-width: 250px;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #9ca3af;
  font-size: 18px;
}

.search-input {
  width: 100%;
  padding: 12px 130px 12px 44px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  font-size: 15px;
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #F15843;
  box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1);
}

.search-mode-toggle {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  padding: 6px 12px;
  background: linear-gradient(135deg, #F15843 0%, #fc7777 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 6px rgba(241, 88, 67, 0.25);
}

.filter-group {
  display: flex;
  gap: 8px;
}

.filter-btn {
  padding: 10px 18px;
  border: 2px solid #e5e7eb;
  background: white;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  color: #6b7280;
}

.filter-btn:hover {
  border-color: #F15843;
  color: #F15843;
}

.filter-btn.active {
  background: linear-gradient(135deg, #F15843 0%, #f5897b 100%);
  color: white;
  border-color: transparent;
}

.select-wrapper {
  position: relative;
}

.sort-select {
  padding: 10px 36px 10px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  background: white;
  color: #374151;
  cursor: pointer;
  appearance: none;
  transition: all 0.2s;
}

.select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #6b7280;
}

.action-buttons {
  display: flex;
  gap: 8px;
  position: relative;
}

.icon-btn {
  padding: 10px 16px;
  border: 2px solid #e5e7eb;
  background: white;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #374151;
}

.icon-btn:hover {
  border-color: #FF6B35;
  color: #FF6B35;
}

.icon-btn.danger:hover {
  border-color: #ef4444;
  color: #ef4444;
  background: #fef2f2;
}

.icon-btn.success {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
}

.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  min-width: 280px;
  z-index: 1000;
  overflow: hidden;
}

.export-menu-header {
  padding: 14px 16px;
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
  font-weight: 700;
  color: #1f2937;
  font-size: 14px;
}

.export-option {
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
}

.export-option:hover {
  background: #fffbeb;
  color: #F15843;
}

.export-option-icon {
  font-size: 16px;
}

.export-option-text {
  flex: 1;
}

.export-option-count {
  font-size: 12px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 10px;
}

.sessions-container {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
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
  border-bottom: 2px solid #e5e7eb;
}

.sessions-table td {
  padding: 16px 14px;
  border-bottom: 1px solid #f3f4f6;
  color: #374151;
}

.sessions-table tbody tr:hover {
  background: #fffbeb;
}

.bot-id {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  background: #f3f4f6;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: #374151;
  font-weight: 600;
}

.prompt-match-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 4px 10px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.time-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.time-relative {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.time-absolute {
  font-size: 12px;
  color: #9ca3af;
}

.threat-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.threat-badge {
  padding: 5px 10px;
  border-radius: 12px;
  color: white;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.details-container {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #FF6B35;
  color: white;
  transform: translateX(-4px);
}

.btn-delete-session {
  padding: 10px 20px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-delete-session:hover {
  background: #dc2626;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
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
  transition: all 0.2s;
}

.event-card.safe {
  border-left-color: #10b981;
}

.event-card.blocked {
  border-left-color: #ef4444;
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
  padding: 6px 14px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
  color: white;
}

.event-status.blocked {
  background: #ef4444;
}

.event-status.safe {
  background: #10b981;
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
  line-height: 1.5;
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
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  background: #fef3c7;
  padding: 4px 8px;
  border-radius: 4px;
  color: #92400e;
  font-weight: 600;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  font-size: 18px;
  color: #6b7280;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f4f6;
  border-top-color: #FF6B35;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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

/* Event details enhanced styles */
.event-risk {
  font-size: 12px;
  color: #6b7280;
  margin-left: auto;
}

.event-risk .risk-safe {
  color: #10b981;
  font-weight: 700;
}

.event-risk .risk-critical {
  color: #dc2626;
  font-weight: 700;
}

.event-risk .risk-warning {
  color: #f59e0b;
  font-weight: 700;
}

/* Detections grid */
.detections-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-top: 8px;
}

.detection-badge {
  padding: 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 12px;
  text-align: center;
  transition: all 0.2s;
}

.detection-badge.threat {
  background: #fef2f2;
  border-color: #fecaca;
  border-left: 3px solid #dc2626;
}

.detection-name {
  font-weight: 600;
  color: #1f2937;
  text-transform: capitalize;
  margin-bottom: 4px;
}

.detection-status {
  color: #dc2626;
  font-weight: 600;
  margin: 4px 0;
}

.detection-count {
  font-size: 11px;
  color: #6b7280;
  margin-top: 4px;
}

/* Block reason */
.block-reason {
  background: #fef2f2;
  border-left: 3px solid #dc2626;
  padding: 12px;
  border-radius: 6px;
  color: #7f1d1d;
  font-size: 14px;
  line-height: 1.5;
}

/* LLM response */
.llm-response {
  background: #f0f9ff;
  border-left: 3px solid #0ea5e9;
  padding: 12px;
  border-radius: 6px;
  color: #0c4a6e;
  font-size: 14px;
  line-height: 1.6;
}

/* Metrics grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 12px;
  margin-top: 8px;
}

.metric-box {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  transition: all 0.2s;
}

.metric-box:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.metric-label {
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  font-weight: 600;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: #1f2937;
}

@media (max-width: 1024px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 16px;
  }

  .dashboard-title {
    font-size: 24px;
  }

  .controls-row {
    flex-direction: column;
  }

  .search-box {
    width: 100%;
  }

  .filter-group,
  .action-buttons {
    width: 100%;
    flex-wrap: wrap;
  }

  .detections-grid,
  .metrics-grid {
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  }
}
`;

export default dashboardStyles;
