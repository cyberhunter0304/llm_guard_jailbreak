import React, { memo, useCallback } from 'react';

/**
 * SearchBox Component - Search functionality with mode toggle
 */
const SearchBox = memo(({ searchTerm, searchMode, onSearchChange, onModeChange }) => {
  return (
    <div className="search-box">
      <div className="search-icon">🔍</div>
      <input
        type="text"
        className="search-input"
        placeholder={searchMode === 'botId' ? 'Search by Bot ID...' : 'Search by Prompt (min 3 characters)...'}
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
      />
      <button 
        className="search-mode-toggle" 
        onClick={onModeChange}
        title={`Switch to search by ${searchMode === 'botId' ? 'Prompt' : 'Bot ID'}`}
      >
        {searchMode === 'botId' ? '🤖 ID' : '💬 Prompt'}
      </button>
    </div>
  );
});

SearchBox.displayName = 'SearchBox';

/**
 * FilterGroup Component - Quick filter buttons
 */
const FilterGroup = memo(({ filterType, onFilterChange }) => {
  const filters = [
    { value: 'all', label: 'All' },
    { value: 'threats', label: '⚠️ Threats' },
    { value: 'pii', label: '🔒 PII' },
    { value: 'secrets', label: '🔑 Secrets' },
    { value: 'jailbreak', label: '🚨 Jailbreak' },
    { value: 'toxicity', label: '☣️ Toxicity' },
    { value: 'clean', label: '✅ Clean' }
  ];

  return (
    <div className="filter-group">
      {filters.map(filter => (
        <button
          key={filter.value}
          className={`filter-btn ${filterType === filter.value ? 'active' : ''}`}
          onClick={() => onFilterChange(filter.value)}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
});

FilterGroup.displayName = 'FilterGroup';

/**
 * SortDropdown Component - Sorting options
 */
const SortDropdown = memo(({ sortBy, onSortChange }) => {
  return (
    <div className="select-wrapper">
      <select 
        className="sort-select" 
        value={sortBy} 
        onChange={(e) => onSortChange(e.target.value)}
      >
        <option value="date-desc">Newest First</option>
        <option value="date-asc">Oldest First</option>
        <option value="threats-desc">Most Threats</option>
        <option value="prompts-desc">Most Prompts</option>
      </select>
      <span className="select-arrow">▼</span>
    </div>
  );
});

SortDropdown.displayName = 'SortDropdown';

/**
 * ActionButtons Component - Export, Refresh, Clear buttons
 */
const ActionButtons = memo(({ 
  sessionsCount, 
  onExportClick, 
  onRefreshClick, 
  onClearClick,
  showExportMenu 
}) => {
  return (
    <div className="action-buttons">
      <div style={{ position: 'relative' }}>
        <button 
          className="icon-btn" 
          onClick={onExportClick}
          title="Export data in various formats"
        >
          📥 Export {showExportMenu ? '▲' : '▼'}
        </button>
      </div>
      <button 
        className="icon-btn" 
        onClick={onRefreshClick}
        title="Refresh sessions data"
      >
        🔄 Refresh
      </button>
      {sessionsCount > 0 && (
        <button 
          className="icon-btn danger" 
          onClick={onClearClick}
          title="Delete all sessions (irreversible)"
        >
          🗑️ Clear All
        </button>
      )}
    </div>
  );
});

ActionButtons.displayName = 'ActionButtons';

export { SearchBox, FilterGroup, SortDropdown, ActionButtons };
