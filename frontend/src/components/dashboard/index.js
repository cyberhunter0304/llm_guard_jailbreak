/**
 * Dashboard Module - Barrel export for convenient imports
 * 
 * Usage:
 *   import { StatCard, StatsGrid } from './dashboard/stats';
 *   import { SearchBox, FilterGroup } from './dashboard/filters';
 */

// Types
export * from './types/index.js';

// Utils
export * from './utils/helpers.js';

// Hooks
export {
  useSessionData,
  useSessionFiltering,
  useAllSessionDetails,
  usePromptSearch,
  usePagination
} from './hooks/index.js';

// Header
export { default as DashboardHeader } from './header/DashboardHeader.jsx';

// Stats
export { StatCard, StatsGrid } from './stats/StatCard.jsx';

// Filters
export { 
  SearchBox, 
  FilterGroup, 
  SortDropdown, 
  ActionButtons 
} from './filters/FilterControls.jsx';

export { default as ExportMenu } from './filters/ExportMenu.jsx';

// Charts
export {
  CustomTooltip,
  ThreatDistributionChart,
  TimelineChart,
  ThreatTypeChart,
  TopThreateningChart,
  ChartContainer
} from './charts/Charts.jsx';

// Sessions
export {
  ThreatBadge,
  SessionRow,
  SessionsTable,
  ThreadItem,
  ThreadsList,
  CollapsibleItem,
  ThreadDetailView
} from './sessions/SessionsTable.jsx';

// Styles
export { default as dashboardStyles } from './styles/dashboard.css.js';