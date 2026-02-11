import { Session, BotDetails, PIIData } from '../types/index.ts';

/**
 * Format ISO date string to locale string
 */
export const formatDate = (isoString: string | undefined): string => {
  if (!isoString) return 'N/A';
  return new Date(isoString).toLocaleString();
};

/**
 * Get relative time (e.g., "5m ago", "2h ago")
 */
export const getRelativeTime = (isoString: string | undefined): string => {
  if (!isoString) return '';
  
  const date = new Date(isoString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return formatDate(isoString);
};

/**
 * Extract PII data from bot details
 */
export const extractPIIData = (botDetails: BotDetails | null): PIIData[] => {
  if (!botDetails || !botDetails.security_events) return [];
  
  const piiData: PIIData[] = [];
  botDetails.security_events.forEach((event, eventIndex) => {
    if (event.detections?.pii?.detected && event.detections.pii.entities) {
      event.detections.pii.entities.forEach((entity) => {
        piiData.push({
          eventIndex: eventIndex + 1,
          timestamp: event.timestamp,
          type: entity.type || 'Unknown',
          value: entity.value || 'N/A',
          confidence: entity.confidence || 0,
          prompt: event.prompt
        });
      });
    }
  });
  
  return piiData;
};

/**
 * Download CSV or JSON data
 */
export const downloadFile = (data: string, filename: string, type: 'csv' | 'json' = 'csv'): void => {
  const mimeType = type === 'csv' ? 'text/csv;charset=utf-8;' : 'application/json';
  const blob = new Blob([data], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
};

/**
 * Convert array of objects to CSV string
 */
export const convertToCSV = (data: Record<string, any>[]): string => {
  if (data.length === 0) return '';
  
  const headers = Object.keys(data[0]).join(',');
  const rows = data
    .map(row => Object.values(row).map(val => `"${val}"`).join(','))
    .join('\n');
  
  return `${headers}\n${rows}`;
};

/**
 * Calculate threat count for a session
 */
export const calculateThreatCount = (session: Session): number => {
  return (
    (session.pii_detections || 0) +
    (session.secrets_detections || 0) +
    (session.jailbreak_attempts || 0) +
    (session.toxicity_detections || 0)
  );
};

/**
 * Check if session has any threats
 */
export const hasThreat = (session: Session): boolean => {
  return (
    session.pii_detections > 0 ||
    session.jailbreak_attempts > 0 ||
    session.toxicity_detections > 0 ||
    (session.secrets_detections || 0) > 0 ||
    session.blocked_prompts > 0
  );
};

/**
 * Check if session is clean
 */
export const isCleanSession = (session: Session): boolean => {
  return (
    session.pii_detections === 0 &&
    session.jailbreak_attempts === 0 &&
    session.toxicity_detections === 0 &&
    (session.secrets_detections || 0) === 0 &&
    session.blocked_prompts === 0
  );
};

/**
 * Get threat type color mapping
 */
export const getThreatColor = (threatType: string): string => {
  const colors: Record<string, string> = {
    pii: '#f59e0b',
    secrets: '#8b5cf6',
    jailbreak: '#ef4444',
    toxicity: '#dc2626',
    clean: '#10b981',
    blocked: '#ef4444'
  };
  return colors[threatType] || '#6b7280';
};

/**
 * Get threat label abbreviation
 */
export const getThreatLabel = (threatType: string): string => {
  const labels: Record<string, string> = {
    pii: 'PII',
    secrets: 'SEC',
    jailbreak: 'JB',
    toxicity: 'TOX'
  };
  return labels[threatType] || threatType.toUpperCase();
};

/**
 * Format bytes to human readable size
 */
export const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Generate color gradient for severity
 */
export const getSeverityColor = (percentage: number): string => {
  if (percentage >= 80) return '#10b981'; // Green
  if (percentage >= 60) return '#f59e0b'; // Orange
  if (percentage >= 40) return '#ef4444'; // Red
  return '#dc2626'; // Dark Red
};
