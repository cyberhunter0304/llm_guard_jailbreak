// ============================================
// DASHBOARD TYPE DEFINITIONS
// ============================================

export interface SecurityStats {
  totalSessions: number;
  totalPrompts: number;
  totalBlocked: number;
  totalPII: number;
  totalJailbreaks: number;
  totalToxicity: number;
  totalSecrets: number;
}

export interface Session {
  bot_id: string;
  created_at: string;
  last_updated?: string;
  total_prompts: number;
  blocked_prompts: number;
  pii_detections: number;
  jailbreak_attempts: number;
  toxicity_detections: number;
  secrets_detections?: number;
}

export interface SecurityMetrics {
  total_time: number;
  scan_time: number;
  llm_time?: number;
  scanner_details?: Record<string, number>;
}

export interface Detection {
  detected: boolean;
  risk_score?: number;
  confidence?: number;
  entity_types?: string[];
  entity_count?: number;
  secrets_risk_score?: number;
}

export interface DetectionResult {
  prompt_injection?: Detection;
  pii?: Detection & {
    entities?: PIIEntity[];
    secrets_detected?: boolean;
  };
  toxicity?: Detection;
}

export interface PIIEntity {
  type: string;
  value: string;
  confidence?: number;
}

export interface SecurityEvent {
  timestamp: string;
  prompt: string;
  anonymized_prompt?: string;
  llm_response?: string;
  block_reason?: string;
  blocked: boolean;
  detections?: DetectionResult;
  metrics?: SecurityMetrics;
}

export interface BotDetails extends Session {
  security_events?: SecurityEvent[];
}

export interface AllSessionDetails {
  [key: string]: BotDetails;
}

export interface PromptSearchResult {
  bot_id: string;
  matchCount: number;
  matches: Array<{
    prompt: string;
    timestamp: string;
  }>;
}

export interface ChartDataPoint {
  name?: string;
  date?: string;
  value?: number;
  count?: number;
  color?: string;
  filterType?: string;
  sessions?: number;
  threats?: number;
  prompts?: number;
  id?: string;
  fullId?: string;
}

export interface PIIData {
  eventIndex: number;
  timestamp: string;
  type: string;
  value: string;
  confidence: number;
  prompt: string;
}

export interface FilterState {
  searchTerm: string;
  searchMode: 'botId' | 'prompt';
  filterType: 'all' | 'threats' | 'clean' | 'pii' | 'jailbreak' | 'toxicity' | 'secrets';
  sortBy: 'date-desc' | 'date-asc' | 'threats-desc' | 'prompts-desc';
  currentPage: number;
}

export interface ViewState {
  view: 'overview' | 'analytics' | 'details';
  detailsTab: 'events' | 'pii';
  selectedBot: string | null;
}

export interface ExportData {
  sessions: Session[];
  details?: BotDetails[];
  timestamp: string;
}
