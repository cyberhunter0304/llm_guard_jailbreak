// Modern SaaS Dashboard CSS
// Orange & Cream theme inspired by inextlabs.com

const dashboardStyles = `
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  background: linear-gradient(135deg, #fffbf5 0%, #fff4e6 100%);
  color: #78716c;
}

.dashboard-container {
  min-height: 100vh;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* Header - Orange gradient with warm tones */
.dashboard-header {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: white;
  padding: 2rem;
  border-radius: 1rem;
  margin-bottom: 2rem;
  box-shadow: 0 10px 40px rgba(249, 115, 22, 0.2);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.dashboard-header::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -10%;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
  border-radius: 50%;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(20px); }
}

.header-content {
  position: relative;
  z-index: 1;
}

.dashboard-title {
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.dashboard-subtitle {
  font-size: 0.9375rem;
  opacity: 0.95;
  font-weight: 400;
  line-height: 1.6;
}

.header-stats {
  display: flex;
  gap: 2rem;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255,255,255,0.2);
  flex-wrap: wrap;
}

.header-stat {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.header-stat-value {
  font-size: 1.875rem;
  font-weight: 700;
  letter-spacing: -0.025em;
}

.header-stat-label {
  font-size: 0.875rem;
  opacity: 0.9;
  font-weight: 500;
}

/* View Toggle - Orange accent */
.view-toggle {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.toggle-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: -0.025em;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #ffffff;
  color: #a8a29e;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  border: 1px solid #fde68a;
}

.toggle-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(249,115,22,0.15);
}

.toggle-btn.active {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(249,115,22,0.3);
}

/* Stats Grid - Warm cream cards */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: #ffffff;
  padding: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #fed7aa;
  box-shadow: 0 1px 3px rgba(249,115,22,0.08);
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  transition: all 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: #fdba74;
  box-shadow: 0 8px 24px rgba(249,115,22,0.15);
}

.stat-icon {
  font-size: 2rem;
  width: 3.5rem;
  height: 3.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(249,115,22,0.1) 0%, rgba(234,88,12,0.1) 100%);
  border-radius: 0.75rem;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: #292524;
  line-height: 1;
}

.stat-label {
  font-size: 0.875rem;
  color: #a8a29e;
  font-weight: 500;
  margin-top: 0.5rem;
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
  box-shadow: 0 2px 8px rgba(249,115,22,0.08);
  border: 1px solid #fed7aa;
  position: relative;
}

.chart-title {
  font-size: 18px;
  font-weight: 700;
  color: #292524;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Controls Section - Cream background */
.controls-section {
  background: #ffffff;
  padding: 1.5rem;
  border-radius: 0.75rem;
  margin-bottom: 1.5rem;
  border: 1px solid #fed7aa;
  box-shadow: 0 1px 3px rgba(249,115,22,0.08);
}

.controls-row {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  flex: 1;
  min-width: 220px;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 0.875rem;
  top: 50%;
  transform: translateY(-50%);
  color: #a8a29e;
  font-size: 1.125rem;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  border: 1px solid #fde68a;
  border-radius: 0.5rem;
  font-size: 0.9375rem;
  transition: all 0.2s ease;
  background: #fffbf5;
  color: #292524;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.search-input::placeholder {
  color: #a8a29e;
}

.search-input:focus {
  outline: none;
  border-color: #f97316;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(249,115,22,0.1);
}

.search-mode-toggle {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  padding: 0.5rem 0.75rem;
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: -0.025em;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(249,115,22,0.25);
}

.search-mode-toggle:hover {
  transform: translateY(-50%) translateY(-1px);
  box-shadow: 0 4px 12px rgba(249,115,22,0.35);
}

.filter-group {
  display: flex;
  gap: 0.5rem;
}

.filter-btn {
  padding: 0.625rem 1.125rem;
  border: 1px solid #fde68a;
  background: #ffffff;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: -0.025em;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #78716c;
}

.filter-btn:hover {
  border-color: #f97316;
  color: #f97316;
  background: rgba(249,115,22,0.05);
}

.filter-btn.active {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(249,115,22,0.25);
}

.select-wrapper {
  position: relative;
}

.sort-select {
  padding: 0.625rem 2.25rem 0.625rem 1rem;
  border: 1px solid #fde68a;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  background: #ffffff;
  color: #292524;
  cursor: pointer;
  appearance: none;
  transition: all 0.2s ease;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.sort-select:hover {
  border-color: #fdba74;
  background: #fffbf5;
}

.sort-select:focus {
  outline: none;
  border-color: #f97316;
  box-shadow: 0 0 0 3px rgba(249,115,22,0.1);
}

.select-arrow {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #a8a29e;
  font-size: 1rem;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  position: relative;
}

.icon-btn {
  padding: 0.625rem 1rem;
  border: 1px solid #fde68a;
  background: #ffffff;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: -0.025em;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #78716c;
}

.icon-btn:hover {
  border-color: #f97316;
  color: #f97316;
  background: rgba(249,115,22,0.05);
}

.icon-btn.danger:hover {
  border-color: #dc2626;
  color: #dc2626;
  background: #fef2f2;
}

.icon-btn.success {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 6px rgba(249,115,22,0.25);
}

.icon-btn.success:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(249,115,22,0.35);
}

/* Export Menu */
.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.5rem;
  background: #ffffff;
  border: 1px solid #fed7aa;
  border-radius: 0.75rem;
  box-shadow: 0 10px 40px rgba(249,115,22,0.15);
  min-width: 280px;
  z-index: 1000;
  overflow: hidden;
}

.export-menu-header {
  padding: 0.875rem 1rem;
  background: #fffbf5;
  border-bottom: 1px solid #fed7aa;
  font-weight: 700;
  color: #292524;
  font-size: 0.875rem;
  letter-spacing: -0.025em;
}

.export-option {
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: #78716c;
  border-bottom: 1px solid #fef3c7;
}

.export-option:hover {
  background: rgba(249,115,22,0.05);
  color: #f97316;
}

.export-option:last-child {
  border-bottom: none;
}

.export-option-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.export-option-text {
  flex: 1;
  font-weight: 500;
}

.export-option-count {
  font-size: 0.75rem;
  color: #a8a29e;
  background: #fef3c7;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
}

/* Sessions Container */
.sessions-container {
  background: #ffffff;
  border-radius: 0.75rem;
  padding: 1.5rem;
  border: 1px solid #fed7aa;
  box-shadow: 0 1px 3px rgba(249,115,22,0.08);
}

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #292524;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  letter-spacing: -0.025em;
}

/* Sessions Table - Orange accents */
.sessions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9375rem;
}

.sessions-table th {
  text-align: left;
  padding: 1rem 1rem;
  background: #fffbf5;
  color: #78716c;
  font-weight: 600;
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid #fed7aa;
}

.sessions-table td {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid #fef3c7;
  color: #78716c;
  font-weight: 400;
}

.sessions-table tbody tr {
  transition: all 0.2s ease;
}

.sessions-table tbody tr:hover {
  background: rgba(249,115,22,0.04);
}

.sessions-table tbody tr:hover td {
  color: #292524;
}

.bot-id {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  background: #fffbf5;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  color: #78716c;
  font-weight: 600;
  border: 1px solid #fde68a;
}

.prompt-match-badge {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: white;
  border-radius: 0.75rem;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.time-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.time-relative {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #292524;
}

.time-absolute {
  font-size: 0.8125rem;
  color: #a8a29e;
}

/* Threat Badges */
.threat-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.threat-badge {
  padding: 0.375rem 0.75rem;
  border-radius: 0.5rem;
  color: white;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  background-color: #a8a29e;
  white-space: nowrap;
}

.threat-badge.jailbreak {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.threat-badge.pii {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

.threat-badge.injection {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
}

/* Details Container & Buttons */
.details-container {
  background: #ffffff;
  border-radius: 0.75rem;
  padding: 1.5rem;
  border: 1px solid #fed7aa;
  box-shadow: 0 1px 3px rgba(249,115,22,0.08);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #fef3c7;
  color: #78716c;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  letter-spacing: -0.025em;
  font-size: 0.9375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.back-btn:hover {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: white;
  transform: translateX(-2px);
  box-shadow: 0 4px 12px rgba(249,115,22,0.25);
}

.btn-delete-session {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  letter-spacing: -0.025em;
  font-size: 0.9375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.btn-delete-session:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(220,38,38,0.3);
}

.btn-delete-session:active {
  transform: translateY(0);
}

/* Tabs Navigation */
.details-tabs {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #fed7aa;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.tab-btn {
  padding: 0.875rem 1.5rem;
  border: none;
  background: transparent;
  color: #a8a29e;
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: -0.025em;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.2s ease;
  margin-bottom: -2px;
  white-space: nowrap;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.tab-btn:hover {
  color: #f97316;
}

.tab-btn.active {
  color: #f97316;
  border-bottom-color: #f97316;
}

/* Bot Information Grid */
.bot-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1.5rem;
  background: #fffbf5;
  border-radius: 0.75rem;
  border: 1px solid #fed7aa;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.info-label {
  font-size: 0.75rem;
  color: #a8a29e;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-value {
  font-size: 1.0625rem;
  color: #292524;
  font-weight: 600;
  letter-spacing: -0.025em;
}

/* Events List */
.events-list {
  margin-top: 1.5rem;
}

.event-card {
  background: #ffffff;
  border-left: 4px solid #fed7aa;
  padding: 1.25rem;
  border-radius: 0.75rem;
  margin-bottom: 1rem;
  transition: all 0.2s ease;
  border: 1px solid #fed7aa;
  box-shadow: 0 1px 2px rgba(249,115,22,0.06);
}

.event-card:hover {
  box-shadow: 0 4px 12px rgba(249,115,22,0.12);
  transform: translateY(-2px);
}

.event-card.safe {
  border-left-color: #16a34a;
  border-color: rgba(22,163,74,0.2);
  background: rgba(22,163,74,0.02);
}

.event-card.blocked {
  border-left-color: #dc2626;
  border-color: rgba(220,38,38,0.2);
  background: rgba(220,38,38,0.02);
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.event-timestamp {
  font-size: 0.8125rem;
  color: #a8a29e;
  font-weight: 500;
}

.event-status {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: white;
  white-space: nowrap;
}

.event-status.blocked {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

.event-status.safe {
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
}

.event-content {
  margin-top: 1rem;
}

.event-section {
  margin-bottom: 1rem;
}

.event-section:last-child {
  margin-bottom: 0;
}

.event-section-title {
  font-size: 0.75rem;
  font-weight: 700;
  color: #a8a29e;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.event-text {
  background: #fffbf5;
  padding: 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #78716c;
  border: 1px solid #fde68a;
  line-height: 1.6;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
}

/* PII Detection Table */
.pii-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1.5rem;
  font-size: 0.875rem;
}

.pii-table th {
  text-align: left;
  padding: 1rem;
  background: linear-gradient(135deg, rgba(249,115,22,0.1) 0%, rgba(234,88,12,0.1) 100%);
  color: #9a3412;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid #fdba74;
}

.pii-table td {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid #fed7aa;
  color: #78716c;
}

.pii-table tbody tr {
  transition: all 0.2s ease;
}

.pii-table tbody tr:hover {
  background: rgba(249,115,22,0.05);
}

.pii-type {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  background: linear-gradient(135deg, rgba(249,115,22,0.15) 0%, rgba(234,88,12,0.15) 100%);
  color: #9a3412;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.pii-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  background: #fed7aa;
  padding: 0.375rem 0.5rem;
  border-radius: 0.25rem;
  color: #9a3412;
  font-weight: 600;
  font-size: 0.8125rem;
}

/* Loading State */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 1rem;
  font-size: 1rem;
  color: #a8a29e;
}

.loading-spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 3px solid #fed7aa;
  border-top-color: #f97316;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 4rem 1.25rem;
  color: #a8a29e;
}

.empty-state-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.6;
}

.empty-state-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #78716c;
  letter-spacing: -0.025em;
}

/* Risk Levels */
.event-risk {
  font-size: 0.75rem;
  color: #a8a29e;
  margin-left: auto;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.event-risk .risk-safe {
  color: #16a34a;
  font-weight: 700;
}

.event-risk .risk-critical {
  color: #b91c1c;
  font-weight: 700;
}

.event-risk .risk-warning {
  color: #d97706;
  font-weight: 700;
}

/* Detections Grid */
.detections-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.detection-badge {
  padding: 0.75rem;
  background: #ffffff;
  border: 1px solid #fed7aa;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  text-align: center;
  transition: all 0.2s ease;
}

.detection-badge:hover {
  border-color: #fdba74;
  box-shadow: 0 2px 8px rgba(249,115,22,0.12);
}

.detection-badge.threat {
  background: rgba(220,38,38,0.08);
  border-color: #fecaca;
  border-left: 3px solid #b91c1c;
}

.detection-name {
  font-weight: 700;
  color: #292524;
  text-transform: capitalize;
  margin-bottom: 0.25rem;
  font-size: 0.8125rem;
}

.detection-status {
  color: #b91c1c;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.detection-count {
  font-size: 0.7rem;
  color: #a8a29e;
  margin-top: 0.25rem;
}

/* Block Reason & LLM Response */
.block-reason {
  background: rgba(220,38,38,0.08);
  border-left: 3px solid #b91c1c;
  padding: 0.75rem;
  border-radius: 0.375rem;
  color: #7f1d1d;
  font-size: 0.875rem;
  line-height: 1.6;
}

.llm-response {
  background: rgba(249,115,22,0.08);
  border-left: 3px solid #f97316;
  padding: 0.75rem;
  border-radius: 0.375rem;
  color: #7c2d12;
  font-size: 0.875rem;
  line-height: 1.6;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.metric-box {
  background: #ffffff;
  border: 1px solid #fed7aa;
  border-radius: 0.5rem;
  padding: 0.75rem;
  text-align: center;
  transition: all 0.2s ease;
}

.metric-box:hover {
  background: #fffbf5;
  border-color: #fdba74;
  box-shadow: 0 2px 8px rgba(249,115,22,0.12);
}

.metric-label {
  font-size: 0.7rem;
  color: #a8a29e;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.metric-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: #292524;
  letter-spacing: -0.025em;
}

/* ====================================
   THREADS DISPLAY STYLES
   ==================================== */

/* Results Summary */
.results-summary {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: #fffbf5;
  border-radius: 0.5rem;
  border: 1px solid #fed7aa;
  font-size: 0.875rem;
  color: #78716c;
  font-weight: 500;
}

/* Threads Container */
.threads-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Thread Card */
.thread-card {
  background: #ffffff;
  border: 1px solid #fed7aa;
  border-left: 3px solid #fed7aa;
  border-radius: 0.5rem;
  overflow: hidden;
  transition: all 0.2s ease;
}

.thread-card:hover {
  box-shadow: 0 4px 12px rgba(249,115,22,0.12);
  border-color: #fdba74;
}

/* Thread Header */
.thread-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  cursor: pointer;
  transition: background 0.2s ease;
}

.thread-header:hover {
  background: rgba(249,115,22,0.03);
}

.thread-header.has-threats {
  border-left-color: #f59e0b;
}

.thread-header.clean {
  border-left-color: #10b981;
}

/* Thread Expand Icon */
.thread-expand-icon {
  font-size: 0.875rem;
  color: #a8a29e;
  flex-shrink: 0;
  min-width: 1.5rem;
  transition: color 0.2s ease;
}

.thread-header:hover .thread-expand-icon {
  color: #f97316;
}

/* Thread Info */
.thread-info {
  flex: 1;
  min-width: 0;
}

.thread-id-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.375rem;
}

.thread-id-label {
  font-size: 0.75rem;
  color: #a8a29e;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.thread-id {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.8125rem;
  color: #292524;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.thread-meta {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  flex-wrap: wrap;
  font-size: 0.8125rem;
  color: #78716c;
}

.thread-meta span {
  white-space: nowrap;
}

/* Thread Threats */
.thread-threats {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.threat-summary {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  align-items: flex-end;
}

.threat-count {
  font-size: 0.875rem;
  font-weight: 700;
  color: #dc2626;
}

.threat-badges-compact {
  display: flex;
  gap: 0.375rem;
  flex-wrap: wrap;
}

.badge-pii,
.badge-secrets,
.badge-jailbreak,
.badge-toxicity,
.badge-blocked {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.badge-pii {
  background: rgba(245,158,11,0.15);
  color: #b45309;
  border: 1px solid rgba(245,158,11,0.3);
}

.badge-secrets {
  background: rgba(139,92,246,0.15);
  color: #6d28d9;
  border: 1px solid rgba(139,92,246,0.3);
}

.badge-jailbreak {
  background: rgba(239,68,68,0.15);
  color: #b91c1c;
  border: 1px solid rgba(239,68,68,0.3);
}

.badge-toxicity {
  background: rgba(220,38,38,0.15);
  color: #991b1b;
  border: 1px solid rgba(220,38,38,0.3);
}

.badge-blocked {
  background: rgba(220,38,38,0.2);
  color: #7f1d1d;
  border: 1px solid rgba(220,38,38,0.4);
}

.clean-badge {
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 700;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
}

.clean-badge-small {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  font-weight: 700;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
}

/* Thread Delete Button */
.thread-delete-btn {
  padding: 0.375rem 0.5rem;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1rem;
  color: #a8a29e;
  flex-shrink: 0;
}

.thread-delete-btn:hover {
  background: rgba(220,38,38,0.1);
  color: #dc2626;
}

/* Conversations List */
.conversations-list {
  padding: 0.75rem;
  background: #fffbf5;
  border-top: 1px solid #fed7aa;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.empty-conversations {
  padding: 1.5rem;
  text-align: center;
  color: #a8a29e;
  background: #fffbf5;
  border-top: 1px solid #fed7aa;
  font-size: 0.875rem;
}

/* Conversation Card */
.conversation-card {
  background: #ffffff;
  border: 1px solid #fde68a;
  border-radius: 0.5rem;
  overflow: hidden;
  transition: all 0.2s ease;
}

.conversation-card:hover {
  box-shadow: 0 2px 8px rgba(249,115,22,0.08);
  border-color: #fdba74;
}

/* Conversation Header */
.conversation-header {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem;
  cursor: pointer;
  transition: background 0.2s ease;
}

.conversation-header:hover {
  background: rgba(249,115,22,0.03);
}

.conversation-expand-icon {
  font-size: 0.75rem;
  color: #a8a29e;
  flex-shrink: 0;
  min-width: 1.25rem;
  transition: color 0.2s ease;
}

.conversation-header:hover .conversation-expand-icon {
  color: #f97316;
}

/* Conversation Info */
.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-id {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin-bottom: 0.25rem;
}

.conversation-label {
  font-size: 0.7rem;
  color: #a8a29e;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.conversation-id-text {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.75rem;
  color: #292524;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  font-size: 0.75rem;
  color: #78716c;
}

.conversation-meta span {
  white-space: nowrap;
}

.conversation-threats {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
  flex-wrap: wrap;
}

/* Responsive for Threads */
@media (max-width: 768px) {
  .thread-header {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .thread-info {
    width: 100%;
  }

  .thread-meta {
    gap: 0.5rem;
    font-size: 0.75rem;
  }

  .thread-threats {
    width: 100%;
    justify-content: space-between;
  }

  .conversation-header {
    flex-wrap: wrap;
  }

  .conversation-info {
    width: 100%;
  }

  .conversation-meta {
    font-size: 0.7rem;
    gap: 0.5rem;
  }
}

@media (max-width: 480px) {
  .thread-header {
    padding: 0.75rem;
  }

  .thread-id {
    font-size: 0.75rem;
  }

  .thread-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  .threat-badges-compact {
    flex-wrap: wrap;
  }

  .conversation-header {
    padding: 0.625rem;
  }
}

/* Original Thread List Components (for ThreadsList component) */
.thread-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Individual Thread Item - Compact Row */
.thread-item {
  background: #ffffff;
  border: 1px solid #fed7aa;
  border-radius: 0.5rem;
  transition: all 0.2s ease;
  cursor: pointer;
  overflow: hidden;
}

.thread-item:hover {
  transform: translateX(4px);
  border-color: #fdba74;
  box-shadow: 0 4px 12px rgba(249,115,22,0.12);
}

/* Thread Item Header - Main clickable area */
.thread-item-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
}

/* Thread Arrow Icon */
.thread-arrow {
  font-size: 0.875rem;
  color: #a8a29e;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.thread-item:hover .thread-arrow {
  color: #f97316;
  transform: translateX(2px);
}

/* Thread ID */
.thread-id {
  flex: 1;
  min-width: 0;
}

.thread-id-label {
  font-size: 0.75rem;
  color: #a8a29e;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.thread-id-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.8125rem;
  color: #292524;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Thread Metadata */
.thread-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.thread-meta-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: #78716c;
  white-space: nowrap;
}

.thread-meta-item strong {
  color: #292524;
  font-weight: 600;
}

/* Thread Status Badge */
.thread-status {
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
  flex-shrink: 0;
}

.thread-status.clean {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
}

.thread-status.threats {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
}

.thread-status.warning {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
}

/* Thread Actions */
.thread-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.thread-action-btn {
  padding: 0.375rem 0.5rem;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1rem;
  color: #a8a29e;
}

.thread-action-btn:hover {
  background: rgba(249,115,22,0.1);
  color: #f97316;
}

.thread-action-btn.delete:hover {
  background: rgba(220,38,38,0.1);
  color: #dc2626;
}

/* Threat Type Visual Treatments */
.thread-item.threat-pii {
  border-left: 3px solid #f59e0b;
  background: linear-gradient(to right, rgba(245,158,11,0.03) 0%, #ffffff 100%);
}

.thread-item.threat-secrets {
  border-left: 3px solid #8b5cf6;
  background: linear-gradient(to right, rgba(139,92,246,0.03) 0%, #ffffff 100%);
}

.thread-item.threat-jailbreak {
  border-left: 3px solid #ef4444;
  background: linear-gradient(to right, rgba(239,68,68,0.03) 0%, #ffffff 100%);
}

.thread-item.threat-toxicity {
  border-left: 3px solid #dc2626;
  background: linear-gradient(to right, rgba(220,38,38,0.03) 0%, #ffffff 100%);
}

.thread-item.threat-multiple {
  border-left: 3px solid #9333ea;
  background: linear-gradient(to right, rgba(147,51,234,0.03) 0%, #ffffff 100%);
}

.thread-item.clean {
  border-left: 3px solid #10b981;
  background: linear-gradient(to right, rgba(16,185,129,0.03) 0%, #ffffff 100%);
}

/* Thread Detail View - Collapsible Items Inside Thread */
.thread-detail-container {
  margin-top: 1.5rem;
}

.thread-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #fed7aa;
}

.thread-detail-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #292524;
  letter-spacing: -0.025em;
}

.thread-detail-count {
  font-size: 0.875rem;
  color: #a8a29e;
  font-weight: 500;
}

/* Thread Detail Items List */
.thread-detail-items {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Individual Collapsible Item */
.thread-detail-item {
  background: #ffffff;
  border: 1px solid #fed7aa;
  border-radius: 0.5rem;
  overflow: hidden;
  transition: all 0.2s ease;
}

.thread-detail-item.expanded {
  box-shadow: 0 4px 12px rgba(249,115,22,0.12);
}

/* Item Header - Collapsible trigger */
.thread-detail-item-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  background: #fffbf5;
  transition: all 0.2s ease;
}

.thread-detail-item-header:hover {
  background: rgba(249,115,22,0.05);
}

.thread-detail-item.expanded .thread-detail-item-header {
  background: #ffffff;
  border-bottom: 1px solid #fed7aa;
}

/* Item Expand Icon */
.thread-detail-item-icon {
  font-size: 0.875rem;
  color: #a8a29e;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.thread-detail-item.expanded .thread-detail-item-icon {
  transform: rotate(90deg);
  color: #f97316;
}

/* Item Summary */
.thread-detail-item-summary {
  flex: 1;
  min-width: 0;
}

.thread-detail-item-type {
  font-size: 0.75rem;
  color: #a8a29e;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.thread-detail-item-preview {
  font-size: 0.875rem;
  color: #292524;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Item Timestamp */
.thread-detail-item-time {
  font-size: 0.75rem;
  color: #a8a29e;
  flex-shrink: 0;
}

/* Item Content - Expanded View */
.thread-detail-item-content {
  padding: 1rem;
  display: none;
}

.thread-detail-item.expanded .thread-detail-item-content {
  display: block;
}

.thread-detail-item-section {
  margin-bottom: 1rem;
}

.thread-detail-item-section:last-child {
  margin-bottom: 0;
}

.thread-detail-item-section-title {
  font-size: 0.75rem;
  font-weight: 700;
  color: #a8a29e;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.thread-detail-item-section-content {
  background: #fffbf5;
  padding: 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #78716c;
  border: 1px solid #fde68a;
  line-height: 1.6;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Threat Badges in Detail Items */
.thread-detail-item-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.thread-detail-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.thread-detail-badge.pii {
  background: rgba(245,158,11,0.15);
  color: #b45309;
  border: 1px solid rgba(245,158,11,0.3);
}

.thread-detail-badge.secrets {
  background: rgba(139,92,246,0.15);
  color: #6d28d9;
  border: 1px solid rgba(139,92,246,0.3);
}

.thread-detail-badge.jailbreak {
  background: rgba(239,68,68,0.15);
  color: #b91c1c;
  border: 1px solid rgba(239,68,68,0.3);
}

.thread-detail-badge.toxicity {
  background: rgba(220,38,38,0.15);
  color: #991b1b;
  border: 1px solid rgba(220,38,38,0.3);
}

.thread-detail-badge.blocked {
  background: rgba(220,38,38,0.2);
  color: #7f1d1d;
  border: 1px solid rgba(220,38,38,0.4);
}

/* Empty State for Thread Details */
.thread-detail-empty {
  text-align: center;
  padding: 3rem 1.5rem;
  color: #a8a29e;
}

.thread-detail-empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.thread-detail-empty-text {
  font-size: 0.9375rem;
  font-weight: 500;
}

/* Responsive Design for Threads */
@media (max-width: 768px) {
  .thread-item-header {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .thread-meta {
    width: 100%;
    gap: 0.5rem;
  }

  .thread-meta-item {
    font-size: 0.75rem;
  }

  .thread-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .thread-detail-item-header {
    flex-wrap: wrap;
  }

  .thread-detail-item-summary {
    width: 100%;
  }

  .thread-detail-item-time {
    margin-left: 1.75rem;
  }
}

@media (max-width: 480px) {
  .thread-item-header {
    padding: 0.75rem;
  }

  .thread-id-value {
    font-size: 0.75rem;
  }

  .thread-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.375rem;
  }

  .thread-status {
    font-size: 0.7rem;
    padding: 0.25rem 0.5rem;
  }

  .thread-detail-item-header {
    padding: 0.625rem 0.75rem;
  }

  .thread-detail-item-content {
    padding: 0.75rem;
  }
}

/* Responsive Design */
@media (max-width: 1024px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 1rem;
  }

  .dashboard-header {
    flex-direction: column;
    text-align: center;
    padding: 1.5rem;
  }

  .dashboard-title {
    font-size: 1.5rem;
  }

  .dashboard-subtitle {
    font-size: 0.875rem;
  }

  .controls-row {
    flex-direction: column;
    gap: 0.75rem;
  }

  .search-box {
    width: 100%;
  }

  .filter-group,
  .action-buttons {
    width: 100%;
    justify-content: space-between;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }

  .stat-card {
    flex-direction: column;
    text-align: center;
  }

  .stat-icon {
    width: 3rem;
    height: 3rem;
    font-size: 1.5rem;
  }

  .stat-value {
    font-size: 2rem;
  }

  .stat-label {
    font-size: 0.8rem;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }

  .sessions-table th,
  .sessions-table td {
    padding: 0.75rem 0.5rem;
    font-size: 0.8125rem;
  }

  .detections-grid,
  .metrics-grid {
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  }

  .section-title {
    font-size: 1.25rem;
  }
}

@media (max-width: 480px) {
  .dashboard-container {
    padding: 0.75rem;
  }

  .dashboard-header {
    padding: 1rem;
  }

  .dashboard-title {
    font-size: 1.375rem;
  }

  .dashboard-subtitle {
    font-size: 0.8rem;
  }

  .controls-section {
    padding: 1rem;
  }

  .controls-row {
    flex-direction: column;
    gap: 0.75rem;
  }

  .search-input {
    min-width: auto;
    width: 100%;
  }

  .filter-group {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .stats-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .stat-card {
    padding: 1rem;
  }

  .stat-value {
    font-size: 1.75rem;
  }

  .stat-label {
    font-size: 0.75rem;
  }

  .sessions-table th,
  .sessions-table td {
    padding: 0.5rem 0.25rem;
    font-size: 0.75rem;
  }

  .bot-info-grid {
    grid-template-columns: 1fr;
  }

  .details-tabs {
    gap: 0.5rem;
    overflow-x: auto;
  }

  .tab-btn {
    padding: 0.75rem 1rem;
    font-size: 0.8125rem;
  }
}
`;

export default dashboardStyles;