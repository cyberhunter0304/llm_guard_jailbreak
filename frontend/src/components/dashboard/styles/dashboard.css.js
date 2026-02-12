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