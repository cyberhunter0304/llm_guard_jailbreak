import React, { memo, useCallback } from 'react';
import { downloadFile, convertToCSV } from '../utils/helpers.js';

/**
 * ExportMenu Component - Export options dropdown menu
 */
const ExportMenu = memo(({ 
  sessions, 
  filteredSessions,
  selectedBot,
  botDetails,
  backendUrl,
  onExportComplete 
}) => {
  const downloadCSV = useCallback((data, filename) => {
    const csv = convertToCSV(data);
    downloadFile(csv, filename, 'csv');
    if (onExportComplete) onExportComplete();
  }, [onExportComplete]);

  const downloadJSON = useCallback((data, filename) => {
    const json = JSON.stringify(data, null, 2);
    downloadFile(json, filename, 'json');
    if (onExportComplete) onExportComplete();
  }, [onExportComplete]);

  const handleExportSummary = useCallback(() => {
    const csvData = sessions.map(session => ({
      'Bot ID': session.bot_id,
      'Created': new Date(session.created_at).toLocaleString(),
      'Total Prompts': session.total_prompts,
      'Blocked': session.blocked_prompts,
      'PII': session.pii_detections,
      'Secrets': session.secrets_detections || 0,
      'Jailbreaks': session.jailbreak_attempts,
      'Toxicity': session.toxicity_detections
    }));
    downloadCSV(csvData, `security-summary-${new Date().toISOString().split('T')[0]}.csv`);
  }, [sessions, downloadCSV]);

  const handleExportFullData = useCallback(async () => {
    try {
      const fullData = await Promise.all(
        sessions.map(async (session) => {
          try {
            const response = await fetch(`${backendUrl}/api/security/${session.bot_id}`);
            return await response.json();
          } catch (error) {
            console.error(`Failed to fetch ${session.bot_id}:`, error);
            return session;
          }
        })
      );
      downloadJSON(fullData, `security-full-data-${new Date().toISOString().split('T')[0]}.json`);
    } catch (error) {
      console.error('Export failed:', error);
    }
  }, [sessions, backendUrl, downloadJSON]);

  const handleExportAllThreats = useCallback(() => {
    const threatSessions = sessions.filter(s => 
      s.pii_detections > 0 || s.jailbreak_attempts > 0 || 
      s.toxicity_detections > 0 || (s.secrets_detections || 0) > 0 || 
      s.blocked_prompts > 0
    );
    const csvData = threatSessions.map(session => ({
      'Bot ID': session.bot_id,
      'Created': new Date(session.created_at).toLocaleString(),
      'Total Prompts': session.total_prompts,
      'Blocked': session.blocked_prompts,
      'PII': session.pii_detections,
      'Secrets': session.secrets_detections || 0,
      'Jailbreaks': session.jailbreak_attempts,
      'Toxicity': session.toxicity_detections,
      'Total Threats': (session.pii_detections + (session.secrets_detections || 0) + session.jailbreak_attempts + session.toxicity_detections + session.blocked_prompts)
    }));
    downloadCSV(csvData, `all-threats-${new Date().toISOString().split('T')[0]}.csv`);
  }, [sessions, downloadCSV]);

  return (
    <div className="export-menu">
      <div className="export-menu-header">📊 Export Options</div>
      
      <div className="export-option" onClick={handleExportSummary}>
        <span className="export-option-icon">📄</span>
        <span className="export-option-text">Summary (CSV)</span>
        <span className="export-option-count">{sessions.length} sessions</span>
      </div>

      <div className="export-option" onClick={handleExportFullData}>
        <span className="export-option-icon">📦</span>
        <span className="export-option-text">Full Data + Prompts (JSON)</span>
        <span className="export-option-count">All details</span>
      </div>

      <div className="export-option" onClick={handleExportAllThreats}>
        <span className="export-option-icon">⚠️</span>
        <span className="export-option-text">All Threats (CSV)</span>
        <span className="export-option-count">
          {sessions.filter(s => 
            s.pii_detections > 0 || (s.secrets_detections || 0) > 0 || 
            s.jailbreak_attempts > 0 || s.toxicity_detections > 0 || 
            s.blocked_prompts > 0
          ).length} sessions
        </span>
      </div>

      {selectedBot && botDetails && (
        <div className="export-option" onClick={() => downloadJSON(botDetails, `bot-${selectedBot.substring(0, 12)}-${new Date().toISOString().split('T')[0]}.json`)}>
          <span className="export-option-icon">🤖</span>
          <span className="export-option-text">Current Bot (JSON)</span>
          <span className="export-option-count">1 session</span>
        </div>
      )}
    </div>
  );
});

ExportMenu.displayName = 'ExportMenu';

export default ExportMenu;
